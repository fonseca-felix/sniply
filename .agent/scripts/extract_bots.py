import re

filepath = r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\backend\bots\definitions.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

bot_names = re.findall(r'\"id\":\s*\"([^\"]+)\"[^}]*?\"name\":\s*\"([^\"]+)\"', content)
for b_id, name in bot_names:
    print(f"{b_id} - {name}")
