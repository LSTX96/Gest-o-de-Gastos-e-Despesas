import sys

path = r'C:\Users\Meu Note\Desktop\ATIVIDADES\rps_passivo\rps_passivo\pages\dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the logo_b64 line to handle Var objects properly
old = 'logo_b64 = item.get("logo_b64") or ""'
new = 'logo_b64 = item.get("logo_b64", "")'
if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed logo_b64 line')
else:
    print('Pattern not found, checking content...')
    # Check for alternative patterns
    for line in content.split('\n'):
        if 'logo_b64' in line:
            print(f'  Found: {line}')