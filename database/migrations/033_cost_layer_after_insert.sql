-- database/migrations/033_cost_layer_after_insert.sql
-- Stock-in movements failed: the BEFORE INSERT trigger on stock_transactions added a
-- cost_layers row that points at the transaction before that row existed (FK violation).
-- The 'in' part (new cost layer, WAC) now runs AFTER INSERT. The 'out' part stays
-- BEFORE INSERT because it sets NEW.unit_cost. Same logic as 013 otherwise.
-- Stock that has no cost layers would sell at cost 0, so each such product gets one
-- opening layer at its WAC (or buy price). Such a layer has no source transaction.
-- Safe to rerun.

BEGIN;

CREATE OR REPLACE FUNCTION tenant_data.process_inventory_valuation()
RETURNS trigger AS $$
DECLARE
    v_qty_to_deduct NUMERIC;
    v_layer RECORD;
    v_total_value NUMERIC := 0;
BEGIN
    IF NEW.transaction_type = 'out' THEN
        v_qty_to_deduct := NEW.quantity;

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
                UPDATE tenant_data.cost_layers SET quantity_remaining = 0 WHERE id = v_layer.id;
            ELSE
                UPDATE tenant_data.cost_layers
                SET quantity_remaining = quantity_remaining - v_qty_to_deduct
                WHERE id = v_layer.id;
                v_total_value := v_total_value + (v_qty_to_deduct * v_layer.unit_cost);
                v_qty_to_deduct := 0;
            END IF;
        END LOOP;

        IF NEW.quantity > 0 THEN
            NEW.unit_cost := v_total_value / NEW.quantity;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION tenant_data.add_cost_layer()
RETURNS trigger AS $$
DECLARE
    v_total_value NUMERIC := 0;
    v_total_stock NUMERIC := 0;
BEGIN
    INSERT INTO tenant_data.cost_layers (
        tenant_id, product_id, transaction_id, quantity_original, quantity_remaining, unit_cost
    ) VALUES (
        NEW.tenant_id, NEW.product_id, NEW.id, NEW.quantity, NEW.quantity, COALESCE(NEW.unit_cost, 0)
    );

    SELECT COALESCE(SUM(quantity_remaining), 0), COALESCE(SUM(quantity_remaining * unit_cost), 0)
    INTO v_total_stock, v_total_value
    FROM tenant_data.cost_layers
    WHERE product_id = NEW.product_id AND quantity_remaining > 0;

    IF v_total_stock > 0 THEN
        UPDATE tenant_data.products SET wac_cost = v_total_value / v_total_stock WHERE id = NEW.product_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_process_inventory_valuation ON tenant_data.stock_transactions;
CREATE TRIGGER trg_process_inventory_valuation
    BEFORE INSERT ON tenant_data.stock_transactions
    FOR EACH ROW
    WHEN (NEW.transaction_type = 'out')
    EXECUTE FUNCTION tenant_data.process_inventory_valuation();

DROP TRIGGER IF EXISTS trg_add_cost_layer ON tenant_data.stock_transactions;
CREATE TRIGGER trg_add_cost_layer
    AFTER INSERT ON tenant_data.stock_transactions
    FOR EACH ROW
    WHEN (NEW.transaction_type = 'in')
    EXECUTE FUNCTION tenant_data.add_cost_layer();

ALTER TABLE tenant_data.cost_layers ALTER COLUMN transaction_id DROP NOT NULL;

INSERT INTO tenant_data.cost_layers (
    tenant_id, product_id, transaction_id, quantity_original, quantity_remaining, unit_cost
)
SELECT p.tenant_id, p.id, NULL, p.stock_quantity, p.stock_quantity,
       COALESCE(NULLIF(p.wac_cost, 0), p.buy_price, 0)
  FROM tenant_data.products p
 WHERE p.stock_quantity > 0
   AND NOT EXISTS (
       SELECT 1 FROM tenant_data.cost_layers c
        WHERE c.tenant_id = p.tenant_id AND c.product_id = p.id
   );

UPDATE tenant_data.products p
   SET wac_cost = COALESCE(NULLIF(p.wac_cost, 0), p.buy_price, 0)
 WHERE p.wac_cost = 0
   AND p.stock_quantity > 0
   AND COALESCE(p.buy_price, 0) > 0;

COMMIT;
