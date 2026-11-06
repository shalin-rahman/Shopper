-- Allow Mushak 6.7 (credit note) lines in the sales VAT register.
-- Credit notes write negative lines so the register nets returns off the original sale.
-- Safe to run more than once.

BEGIN;

ALTER TABLE tenant_data.vat_sales_register_lines
    DROP CONSTRAINT IF EXISTS vat_sales_register_lines_mushak_form_check;

ALTER TABLE tenant_data.vat_sales_register_lines
    ADD CONSTRAINT vat_sales_register_lines_mushak_form_check
    CHECK (mushak_form IN ('6.1', '6.2', '6.3', '6.6', '6.7'));

COMMIT;
