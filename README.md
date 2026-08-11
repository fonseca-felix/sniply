# Snip.ly

Encurtador de links com Flask + Firebase Firestore.

## Rodando

```bash
pip install -r requirements.txt
# substitua serviceAccountKey.json pelas credenciais reais do seu projeto Firebase
export BASE_URL="http://localhost:5000"
python app.py
```

Acesse http://localhost:5000

## Firestore

Coleção `urls`, documento com ID = `short_code`:

- `original_url` (string)
- `short_code` (string)
- `clicks_count` (number, inicia em 0)
- `created_at` (timestamp do servidor)

## API

- `POST /api/shorten` → `{ "original_url": "https://..." }`
- `GET /api/stats/<short_code>`
- `GET /<short_code>` → incrementa cliques e redireciona (302)
