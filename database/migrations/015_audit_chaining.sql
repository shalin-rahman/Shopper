-- database/migrations/015_audit_chaining.sql
-- Tamper-evident hash chaining for audit log.

ALTER TABLE tenant_data.audit_log ADD COLUMN IF NOT EXISTS previous_hash TEXT;
ALTER TABLE tenant_data.audit_log ADD COLUMN IF NOT EXISTS current_hash TEXT;

CREATE OR REPLACE FUNCTION tenant_data.chain_audit_hash()
RETURNS TRIGGER AS $$
DECLARE
    prev_hash TEXT;
    content_text TEXT;
BEGIN
    -- Get the most recent hash for this tenant
    SELECT current_hash INTO prev_hash
    FROM tenant_data.audit_log
    WHERE tenant_id = NEW.tenant_id
    ORDER BY changed_at DESC, id DESC
    LIMIT 1;
    
    NEW.previous_hash := COALESCE(prev_hash, 'GENESIS');
    
    -- Combine row content to hash
    content_text := NEW.tenant_id::text || '|' || 
                    NEW.table_name || '|' || 
                    NEW.record_id::text || '|' || 
                    NEW.action || '|' || 
                    COALESCE(NEW.old_values::text, '') || '|' || 
                    COALESCE(NEW.new_values::text, '') || '|' || 
                    NEW.previous_hash;
                    
    NEW.current_hash := encode(digest(content_text, 'sha256'), 'hex');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_chain
    BEFORE INSERT ON tenant_data.audit_log
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.chain_audit_hash();
