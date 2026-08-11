import re
import os

filepath = r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\backend\bots\definitions.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

mapping = {
    "text-writer": "escritor.png",
    "story-writer": "escritor.png",
    "study-planner": "professor.png",
    "flashcard-maker": "ideias.png",
    "activity-generator": "criador de atividade.png",
    "exam-maker": "criador de atividade.png",
    "tea-educator": "TEA.png",
    "content-explainer": "explicador.png",
    "literacy-teacher": "alfebetizador.png",
    "math-tutor": "matematica.png",
    "history-tutor": "historia.png",
    "sociology-tutor": "sociologia.png",
    "philosophy-tutor": "filosofia.png",
    "geography-tutor": "geografia.png",
    "chemistry-tutor": "quimico.png",
    "biology-tutor": "cientista.png",
    "physics-tutor": "fisico.png",
    "languages-tutor": "linguas.png",
    "programming-tutor": "dev.png",
    "frontend-dev": "dev.png",
    "backend-dev": "dev.png",
    "database-dev": "sql.png",
    "nosql-dev": "nosql.png",
    "code-orchestrator": "orchestrator.png",
    "doc-writer": "leitura.png",
    "prompt-engineer": "prompt.png",
    "pygame-dev": "pygame.png",
    "webgame-dev": "games-html-css-js.png",
    "rpg-helper": "rpg.png",
    "rpg-master": "mestre-rpg.png",
    "basketball-coach": "basquete.png",
    "volleyball-coach": "volei.png",
    "beach-tennis-coach": "tecnico.png",
    "handball-coach": "tecnico.png",
    "futsal-coach": "fut.png",
    "corinthians-fan": "torcedor.png",
    "football-expert": "fut.png",
    "sports-coach": "tecnico.png",
    "tennis-expert": "tecnico.png",
    "f1-expert": "f1.png",
    "nutritionist": "nutricionista.png",
    "fitness-trainer": "personal.png",
    "companion": "ajuda.png",
    "contract-writer": "contrato.png",
    "message-writer": "escritor.png",
    "entrepreneur": "empreendedor.png",
    "chef": "cozinha.png",
    "fashion-expert": "ideias.png",
    "sneaker-expert": "tenis-calcado.png",
    "music-expert": "musica.png",
    "european-lit": "1.png",
    "brazilian-lit": "2.png",
    "asian-lit": "3.png",
    "movie-expert": "filme.png",
    "army-expert": "exercito.png",
    "police-expert": "policia.png",
    "air-force-expert": "aeronautica.png",
    "navy-expert": "marinha.png",
    "catholic-church": "catolico.png"
}

import re

for b_id, img in mapping.items():
    # Replace or insert 'image': 'img/...'
    # First, let's see if image already exists
    pattern_has_image = re.compile(rf'(\"id\":\s*\"{b_id}\"[^}}]*?)(?:\n\s*\"image\":\s*\"[^\"]+\",)([^}}]*?)}}', re.DOTALL)
    if pattern_has_image.search(content):
        # replace
        content = pattern_has_image.sub(rf'\1\n        "image": "img/{img}",\2}}', content)
    else:
        # insert after color
        pattern_insert = re.compile(rf'(\"id\":\s*\"{b_id}\"[^}}]*?\"color\":\s*\"[^\"]+\",)', re.DOTALL)
        content = pattern_insert.sub(rf'\1\n        "image": "img/{img}",', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated definitions.py")
