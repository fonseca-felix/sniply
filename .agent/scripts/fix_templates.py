files = [
    r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\frontend\templates\chat.html',
    r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\frontend\templates\keys.html',
    r'c:\Users\SENAI DS 2025\Desktop\3º Semestre\bot_chat_exp\frontend\templates\index.html'
]

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace broken syntax
    content = content.replace("filename=css/style.css) + ?v=2 }}", "filename='css/style.css') }}?v=2")
    content = content.replace("filename=js/chat.js) + ?v=2 }}", "filename='js/chat.js') }}?v=2")
    content = content.replace("filename=js/keys.js) + ?v=2 }}", "filename='js/keys.js') }}?v=2")
    content = content.replace("filename=js/main.js) + ?v=2 }}", "filename='js/main.js') }}?v=2")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
print('Fixed syntax error')
