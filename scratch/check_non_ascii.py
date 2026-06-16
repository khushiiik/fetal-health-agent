import re
import sys

# Reconfigure stdout to use utf-8
sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\KHUSHI\OneDrive\Desktop\brainerhub\Projects\fetal_health_agent\streamlit_ui\app.py", 'r', encoding='utf-8') as f:
    content = f.read()

non_ascii = re.findall(r'[^\x00-\x7F]', content)
print("Unique non-ascii characters in app.py:")
for char in sorted(set(non_ascii)):
    print(f"Char: {char} | Code: U+{ord(char):04X}")
