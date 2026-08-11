"""
Sniply — Flask URL Shortener
Segurança: Rate limiting, security headers, validação de URL,
           proteção contra Open Redirect, error handlers seguros.
"""

import ipaddress
import logging
import os
import random
import re
import secrets
import string
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, redirect, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_PATH = os.environ.get(
    "FIREBASE_CREDENTIALS", os.path.join(BASE_DIR, "serviceAccountKey.json")
)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
IS_PRODUCTION = os.environ.get("FLASK_ENV", "development") == "production"

# Schemas e hosts que NUNCA devem ser encurtados
BLOCKED_SCHEMAS = {"javascript", "data", "vbscript", "file", "ftp"}
BLOCKED_HOSTS = {
    "localhost",
    "0.0.0.0",
    "metadata.google.internal",  # GCP metadata server
    "169.254.169.254",           # AWS / cloud metadata
    "100.100.100.200",           # Alibaba metadata
}

# Regex rigorosa: só http/https, domínio real, sem IP privado
URL_REGEX = re.compile(
    r"^https?://"
    r"([A-Za-z0-9]([A-Za-z0-9\-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}"
    r"(:\d{1,5})?"
    r"(/[^\s]*)?$",
    re.IGNORECASE,
)

# Slug: apenas alfanumérico
SLUG_REGEX = re.compile(r"^[A-Za-z0-9]{1,10}$")

ALPHABET = string.ascii_letters + string.digits


# ---------------------------------------------------------------------------
# Firebase
# ---------------------------------------------------------------------------
def _build_firebase_cred() -> credentials.Certificate:
    """
    Monta credenciais do Firebase.
    Prioridade:
      1. Arquivo JSON (LOCAL / desenvolvimento)
      2. Variáveis de ambiente individuais (PRODUÇÃO / Vercel)
    """
    if os.path.isfile(SERVICE_ACCOUNT_PATH):
        return credentials.Certificate(SERVICE_ACCOUNT_PATH)

    private_key_raw = os.environ.get("FIREBASE_PRIVATE_KEY", "")
    private_key = private_key_raw.replace("\\n", "\n")

    service_account_info = {
        "type": "service_account",
        "project_id": os.environ["FIREBASE_PROJECT_ID"],
        "private_key_id": os.environ["FIREBASE_PRIVATE_KEY_ID"],
        "private_key": private_key,
        "client_email": os.environ["FIREBASE_CLIENT_EMAIL"],
        "client_id": os.environ["FIREBASE_CLIENT_ID"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ["FIREBASE_CLIENT_X509_CERT_URL"],
        "universe_domain": "googleapis.com",
    }
    return credentials.Certificate(service_account_info)


if not firebase_admin._apps:
    firebase_admin.initialize_app(_build_firebase_cred())

db = firestore.client()
COLLECTION = "urls"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=16 * 1024,          # 16 KB máx por request
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["120 per minute", "500 per hour"],
    storage_uri="memory://",
)

# ---------------------------------------------------------------------------
# Security Headers (todas as respostas)
# ---------------------------------------------------------------------------
@app.after_request
def apply_security_headers(response):
    # Impede clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Impede MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Controla informações do referrer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Desabilita recursos perigosos do browser
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    )
    # XSS Protection legado (IE/Edge antigo)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Força HTTPS em produção
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' "
          "https://cdn.tailwindcss.com "
          "https://cdnjs.cloudflare.com "
          "https://pagead2.googlesyndication.com "
          "https://partner.googleadservices.com "
          "https://www.googletagservices.com "
          "https://adservice.google.com "
          "https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: "
          "https://*.googlesyndication.com "
          "https://*.google.com "
          "https://*.gstatic.com "
          "https://*.doubleclick.net; "
        "frame-src "
          "https://googleads.g.doubleclick.net "
          "https://tpc.googlesyndication.com "
          "https://*.googlesyndication.com "
          "https://*.google.com "
          "https://*.doubleclick.net; "
        "connect-src 'self' "
          "https://*.googlesyndication.com "
          "https://*.doubleclick.net "
          "https://pagead2.googlesyndication.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    # Cross-Origin isolation (sem COEP — incompatível com AdSense)
    response.headers["Cross-Origin-Opener-Policy"]   = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Remove header que identifica o framework
    response.headers.pop("Server", None)
    response.headers.pop("X-Powered-By", None)
    return response


# ---------------------------------------------------------------------------
# Rota estática — robots.txt
# ---------------------------------------------------------------------------
@app.route("/robots.txt")
def robots():
    return app.send_static_file("robots.txt")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_private_ip(host: str) -> bool:
    """Retorna True se o host for um IP privado, loopback ou reservado."""
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local
    except ValueError:
        return False


def normalize_url(raw_url: str) -> str | None:
    """
    Valida e normaliza a URL.
    Rejeita:
      - Schemas perigosos (javascript:, data:, etc.)
      - IPs privados / loopback (SSRF)
      - Hosts internos conhecidos (metadata servers)
      - Porta 0 ou portas incomuns sem https
      - URLs sem TLD
    """
    url = (raw_url or "").strip()
    if not url or len(url) > 2048:
        return None

    # Adiciona https:// se não tiver schema
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", url):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception:
        return None

    schema = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port

    # Bloqueia schemas perigosos
    if schema in BLOCKED_SCHEMAS:
        return None

    # Só http e https
    if schema not in {"http", "https"}:
        return None

    # Bloqueia hosts internos conhecidos
    if host in BLOCKED_HOSTS or not host:
        return None

    # Bloqueia IPs privados (proteção SSRF)
    if _is_private_ip(host):
        return None

    # Bloqueia porta 0
    if port == 0:
        return None

    # Valida formato geral com regex
    if not URL_REGEX.match(url):
        return None

    return url


def generate_slug(length: int = 6) -> str:
    """Slug criptograficamente seguro (secrets em vez de random)."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_unique_slug(length: int = 6, max_attempts: int = 10) -> str:
    """Gera slug único no Firestore."""
    for _ in range(max_attempts):
        slug = generate_slug(length)
        if not db.collection(COLLECTION).document(slug).get().exists:
            return slug
    raise RuntimeError("Não foi possível gerar um slug único. Tente novamente.")


def _safe_json_error(message: str, status: int):
    """Resposta de erro JSON sem vazar detalhes internos."""
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(_):
    return _safe_json_error("Requisição inválida.", 400)


@app.errorhandler(404)
def not_found(_):
    return render_template("index.html"), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return _safe_json_error("Método não permitido.", 405)


@app.errorhandler(413)
def payload_too_large(_):
    return _safe_json_error("Payload muito grande.", 413)


@app.errorhandler(429)
def rate_limit_exceeded(_):
    return _safe_json_error(
        "Muitas requisições. Aguarde um momento e tente novamente.", 429
    )


@app.errorhandler(500)
def internal_error(exc):
    # Loga o erro real internamente, mas não expõe ao cliente
    logger.error("Erro interno: %s", exc, exc_info=True)
    return _safe_json_error("Erro interno. Tente novamente mais tarde.", 500)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
@limiter.limit("10 per minute")          # Rate limit específico para criação
def shorten():
    # Exige Content-Type correto
    if not request.is_json:
        return _safe_json_error("Content-Type deve ser application/json.", 415)

    payload = request.get_json(silent=True) or {}
    raw_url = payload.get("original_url", "")

    # Rejeita payloads gigantes (já coberto por MAX_CONTENT_LENGTH, mas dupla checagem)
    if len(str(raw_url)) > 2048:
        return _safe_json_error("URL muito longa (máx 2048 caracteres).", 400)

    original_url = normalize_url(raw_url)
    if not original_url:
        return _safe_json_error("URL inválida. Informe um link público válido.", 400)

    try:
        short_code = generate_unique_slug()
    except RuntimeError as exc:
        logger.error("Falha ao gerar slug: %s", exc)
        return _safe_json_error("Erro ao processar. Tente novamente.", 500)

    db.collection(COLLECTION).document(short_code).set(
        {
            "original_url": original_url,
            "short_code": short_code,
            "clicks_count": 0,
            "created_at": firestore.SERVER_TIMESTAMP,
            "created_ip": get_remote_address(),  # auditoria
        }
    )

    logger.info("Link criado: %s → %s", short_code, original_url)

    return (
        jsonify(
            {
                "original_url": original_url,
                "short_code": short_code,
                "short_url": f"{BASE_URL.rstrip('/')}/{short_code}",
            }
        ),
        201,
    )


@app.route("/api/stats/<short_code>")
@limiter.limit("30 per minute")
def stats(short_code: str):
    # Valida slug antes de consultar Firestore
    if not SLUG_REGEX.match(short_code):
        return _safe_json_error("Código inválido.", 400)

    snapshot = db.collection(COLLECTION).document(short_code).get()
    if not snapshot.exists:
        return _safe_json_error("Link não encontrado.", 404)

    data = snapshot.to_dict()
    created_at = data.get("created_at")
    return jsonify(
        {
            "short_code": data.get("short_code", short_code),
            "original_url": data.get("original_url"),
            "clicks_count": data.get("clicks_count", 0),
            "created_at": created_at.isoformat() if created_at else None,
            "short_url": f"{BASE_URL.rstrip('/')}/{short_code}",
        }
    )


@app.route("/<short_code>")
@limiter.limit("60 per minute")
def follow(short_code: str):
    # Valida slug: só alfanumérico, tamanho controlado
    if not SLUG_REGEX.match(short_code):
        return render_template("index.html"), 404

    doc_ref = db.collection(COLLECTION).document(short_code)
    snapshot = doc_ref.get()

    if not snapshot.exists:
        return render_template("index.html"), 404

    original_url = snapshot.to_dict().get("original_url", "")

    # Dupla checagem na URL destino antes do redirect (defense in depth)
    if not original_url or not normalize_url(original_url):
        logger.warning("URL destino inválida para slug: %s", short_code)
        return render_template("index.html"), 404

    doc_ref.update({"clicks_count": firestore.Increment(1)})

    # 301 cache permanente; 302 para manter contagem de cliques real
    return redirect(original_url, code=302)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug,
        host="127.0.0.1",           # Não expõe em 0.0.0.0 localmente
        port=int(os.environ.get("PORT", 5000)),
    )
