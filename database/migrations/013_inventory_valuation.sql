-- database/migrations/013_inventory_valuation.sql
-- Implements WAC and FIFO cost layers logic.

CREATE TABLE IF NOT EXISTS tenant_data.cost_layers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES platform.tenants (id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES tenant_data.products (id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL REFERENCES tenant_data.stock_transactions (id) ON DELETE CASCADE,
    quantity_original NUMERIC(18, 4) NOT NULL CHECK (quantity_original > 0),
    quantity_remaining NUMERIC(18, 4) NOT NULL CHECK (quantity_remaining >= 0),
    unit_cost NUMERIC(18, 4) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cost_layers_product ON tenant_data.cost_layers (tenant_id, product_id, created_at ASC);

ALTER TABLE tenant_data.cost_layers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_data.cost_layers FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_cost_layers
    ON tenant_data.cost_layers
    FOR ALL
    TO shopper_app
    USING (tenant_id = tenant_data.app_tenant_id())
    WITH CHECK (tenant_id = tenant_data.app_tenant_id());

GRANT SELECT, INSERT, UPDATE ON tenant_data.cost_layers TO shopper_app;
GRANT ALL ON tenant_data.cost_layers TO shopper_migrate;

-- Add WAC (Weighted Average Cost) tracker to products table (materialized cost)
ALTER TABLE tenant_data.products ADD COLUMN IF NOT EXISTS wac_cost NUMERIC(18, 4) NOT NULL DEFAULT 0;

-- Function to process inventory inward and outward movements
CREATE OR REPLACE FUNCTION tenant_data.process_inventory_valuation()
RETURNS trigger AS $$
DECLARE
    v_qty_to_deduct NUMERIC;
    v_layer RECORD;
    v_total_value NUMERIC := 0;
    v_total_stock NUMERIC := 0;
    v_current_wac NUMERIC := 0;
BEGIN
    IF NEW.transaction_type = 'in' THEN
        -- Add a new cost layer for IN transactions
        INSERT INTO tenant_data.cost_layers (
            tenant_id, product_id, transaction_id, quantity_original, quantity_remaining, unit_cost
        ) VALUES (
            NEW.tenant_id, NEW.product_id, NEW.id, NEW.quantity, NEW.quantity, COALESCE(NEW.unit_cost, 0)
        );

        -- Recalculate WAC
        SELECT COALESCE(SUM(quantity_remaining), 0), COALESCE(SUM(quantity_remaining * unit_cost), 0)
        INTO v_total_stock, v_total_value
        FROM tenant_data.cost_layers
        WHERE product_id = NEW.product_id AND quantity_remaining > 0;

        IF v_total_stock > 0 THEN
            v_current_wac := v_total_value / v_total_stock;
            UPDATE tenant_data.products SET wac_cost = v_current_wac WHERE id = NEW.product_id;
        END IF;

    ELSIF NEW.transaction_type = 'out' THEN
        v_qty_to_deduct := NEW.quantity;
        v_total_value := 0;

        -- Deplete FIFO cost layers
        FOR v_layer IN 
            SELECT * FROM tenant_data.cost_layers 
            WHERE product_id = NEW.product_id AND quantity_remaining > 0
            ORDER BY created_at ASC
            FOR UPDATE
        LOOP
            IF v_qty_to_deduct = 0 THEN
                EXIT;
            END IF;

            IF v_layer.quantity_remaining <= v_qty_to_deduct THEN
                v_qty_to_deduct := v_qty_to_deduct - v_layer.quantity_remaining;
                v_total_value := v_total_value + (v_layer.quantity_remaining * v_layer.unit_cost);
                
                UPDATE tenant_data.cost_layers 
                SET quantity_remaining = 0 
                WHERE id = v_layer.id;
            ELSE
                UPDATE tenant_data.cost_layers 
                SET quantity_remaining = quantity_remaining - v_qty_to_deduct 
                WHERE id = v_layer.id;
                
                v_total_value := v_total_value + (v_qty_to_deduct * v_layer.unit_cost);
                v_qty_to_deduct := 0;
            END IF;
        END LOOP;

        -- Update the out transaction with calculated FIFO outbound unit cost
        IF NEW.quantity > 0 THEN
            NEW.unit_cost := v_total_value / NEW.quantity;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_process_inventory_valuation ON tenant_data.stock_transactions;
CREATE TRIGGER trg_process_inventory_valuation
    BEFORE INSERT ON tenant_data.stock_transactions
    FOR EACH ROW
    EXECUTE FUNCTION tenant_data.process_inventory_valuation();
