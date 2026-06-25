import os
import re

DIR = 'routers'
for file in os.listdir(DIR):
    if not file.endswith('.py'):
        continue
    path = os.path.join(DIR, file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    content = content.replace("ctx.tenant_id=", "tenant_id=")
    content = content.replace("ctx.subdomain=", "sub=")
    
    # Also in SQL strings, it might have replaced it. Wait, `ctx.tenant_id` in SQL string is fine or not?
    # Actually, the SQL strings usually say `SELECT id, tenant_id, ...`
    # Did it replace `tenant_id` in SQL strings?
    # `content = re.sub(r'(?<!\w)tenant_id(?!\w)', 'ctx.tenant_id', content)`
    # This means `SELECT tenant_id` became `SELECT ctx.tenant_id`. That's bad!
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
