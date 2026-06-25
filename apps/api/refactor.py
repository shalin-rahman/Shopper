import os
import re

DIR = 'routers'

boilerplates = [
    re.compile(r'^[ \t]*sub\s*=\s*subdomain_from_request\(request\)\n[ \t]*if\s+not\s+sub:\n[ \t]*raise\s+HTTPException\(status_code=400,\s*detail="Tenant subdomain required"\)\n+[ \t]*pool\s*=\s*_pool\(request\)\n[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*tenant_id\s*=\s*tenant\["id"\]\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant_id,\s*tenant\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE),
    re.compile(r'^[ \t]*sub\s*=\s*subdomain_from_request\(request\)\n[ \t]*pool\s*=\s*_pool\(request\)\n[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*tenant_id\s*=\s*tenant\["id"\]\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant_id,\s*tenant\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE),
    re.compile(r'^[ \t]*sub\s*=\s*subdomain_from_request\(request\)\n[ \t]*pool\s*=\s*request\.app\.state\.db_pool\n[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*tenant_id\s*=\s*tenant\["id"\]\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant_id,\s*tenant\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE),
    re.compile(r'^[ \t]*sub\s*=\s*subdomain_from_request\(request\)\n[ \t]*pool\s*=\s*_pool\(request\)\n[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant\["id"\],\s*tenant\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE),
    re.compile(r'^[ \t]*sub\s*=\s*subdomain_from_request\(request\)\n[ \t]*pool\s*=\s*_pool\(request\)\n[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*tenant_info\s*=\s*tenant\n[ \t]*tenant_id\s*=\s*tenant\["id"\]\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant_id,\s*tenant_info\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE),
    # For products.py list_products which has `tenant = await resolve_tenant_id(pool, sub)` then `async with tenant_transaction`
    re.compile(r'^[ \t]*tenant\s*=\s*await\s+resolve_tenant_id\(pool,\s*sub\)\n[ \t]*tenant_id\s*=\s*tenant\["id"\]\n[ \t]*async\s+with\s+tenant_transaction\(request,\s*tenant_id,\s*tenant\["dedicated_database_name"\]\)\s*as\s*conn:', re.MULTILINE)
]

for file in os.listdir(DIR):
    if not file.endswith('.py'):
        continue
        
    path = os.path.join(DIR, file)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    
    # Replace imports
    content = content.replace(
        "from core.tenant_context import resolve_tenant_id, subdomain_from_request, tenant_transaction",
        "from core.tenant_context import TenantCtxDep"
    )
    
    # Replace boilerplates
    def repl(m):
        # find leading spaces of the match
        lines = m.group(0).split('\n')
        indent = lines[-1][:len(lines[-1]) - len(lines[-1].lstrip())]
        return f"{indent}async with ctx.transaction() as conn:"
        
    for regex in boilerplates:
        content = regex.sub(repl, content)
        
    # Replace request: Request with ctx: TenantCtxDep in async defs that now have ctx.transaction()
    if 'ctx.transaction()' in content:
        content = content.replace("(request: Request,", "(ctx: TenantCtxDep,")
        content = content.replace("(request: Request)", "(ctx: TenantCtxDep)")
        
        # fix leftover usages of sub or tenant_id
        content = re.sub(r'(?<!\w)sub(?!\w)', 'ctx.subdomain', content)
        content = re.sub(r'(?<!\w)tenant_id(?!\w)', 'ctx.tenant_id', content)
        # except in signatures maybe? No, signatures use ctx.
        
        # remove _pool function
        content = re.sub(r'\n*def _pool\(request: Request\) -> asyncpg\.Pool:.*?return pool\n+', '\n\n', content, flags=re.DOTALL)
        
        # replace unused `subdomain_from_request` import if any
        # actually, just let it be.
        
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
