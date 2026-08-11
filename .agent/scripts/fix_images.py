import re

filepath = r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\backend\bots\definitions.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix literature bots
content = re.sub(r'(european-lit.*?)\"image\":\s*\"img/1\.png\"', r'\1"image": "img/leitura.png"', content, flags=re.DOTALL)
content = re.sub(r'(brazilian-lit.*?)\"image\":\s*\"img/2\.png\"', r'\1"image": "img/leitura.png"', content, flags=re.DOTALL)
content = re.sub(r'(asian-lit.*?)\"image\":\s*\"img/3\.png\"', r'\1"image": "img/leitura.png"', content, flags=re.DOTALL)

# Fix code-orchestrator
content = re.sub(r'(code-orchestrator.*?)\"image\":\s*\"img/orchestrator\.png\"', r'\1"image": "img/orchestrator (2).png"', content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
