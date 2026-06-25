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
    # Fix SQL select/insert lists
    content = content.replace("id, ctx.tenant_id,", "id, tenant_id,")
    content = content.replace(" ctx.tenant_id,", " tenant_id,")
    content = content.replace("ctx.tenant_id, ", "tenant_id, ")
    content = content.replace("ctx.tenant_id)", "tenant_id)")
    content = content.replace("(ctx.tenant_id", "(tenant_id")
    
    # Wait, what if it's passed as an argument? `conn.fetchrow(..., ctx.tenant_id, ...)`
    # That one SHOULD be ctx.tenant_id!
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
