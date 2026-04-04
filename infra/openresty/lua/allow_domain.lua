-- Whitelist hostnames for ACME (Let's Encrypt). New tenant subdomains are allowed
-- when they match PLATFORM_ROOT_DOMAIN (e.g. "shopper.example.com" → "*.shopper.example.com").
-- Optional exact allowlist via ALLOW_ACME_EXTRA_DOMAINS=comma,separated,hosts

local _M = {}

local function split_csv(s)
    local out = {}
    if not s or s == "" then
        return out
    end
    for part in string.gmatch(s, "([^,]+)") do
        part = string.match(part, "^%s*(.-)%s*$")
        if part and part ~= "" then
            out[#out + 1] = part
        end
    end
    return out
end

function _M.check(domain)
    if not domain or domain == "" then
        return false
    end

    local root = os.getenv("PLATFORM_ROOT_DOMAIN")
    if root and root ~= "" then
        local suffix = "." .. root
        if string.sub(domain, -#suffix) == suffix then
            return true
        end
        if domain == root then
            return true
        end
    end

    for _, host in ipairs(split_csv(os.getenv("ALLOW_ACME_EXTRA_DOMAINS"))) do
        if domain == host then
            return true
        end
    end

    return false
end

return _M
