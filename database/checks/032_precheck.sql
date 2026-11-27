-- database/checks/032_precheck.sql
-- Run before migration 032 on a real DB, as the migrate role (RLS off for it).
-- One row per link that 032 makes tenant-qualified. Every count must be 0, or 032 fails on VALIDATE.
-- po_lines has no tenant_id before 032, so its links use the purchase order's tenant;
-- po_lines.po_id counts lines whose purchase order is missing (the backfill could not fill them).

SELECT 'product_categories.parent_id' AS link, count(*) AS bad
  FROM tenant_data.product_categories c
  JOIN tenant_data.product_categories p ON p.id = c.parent_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'products.category_id', count(*)
  FROM tenant_data.products c
  JOIN tenant_data.product_categories p ON p.id = c.category_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'stock_transactions.product_id', count(*)
  FROM tenant_data.stock_transactions c
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'stock_transactions.branch_id', count(*)
  FROM tenant_data.stock_transactions c
  JOIN tenant_data.branches p ON p.id = c.branch_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'invoices.customer_id', count(*)
  FROM tenant_data.invoices c
  JOIN tenant_data.customers p ON p.id = c.customer_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'invoice_lines.invoice_id', count(*)
  FROM tenant_data.invoice_lines c
  JOIN tenant_data.invoices p ON p.id = c.invoice_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'invoice_lines.product_id', count(*)
  FROM tenant_data.invoice_lines c
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'payments.invoice_id', count(*)
  FROM tenant_data.payments c
  JOIN tenant_data.invoices p ON p.id = c.invoice_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'cost_layers.product_id', count(*)
  FROM tenant_data.cost_layers c
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'cost_layers.transaction_id', count(*)
  FROM tenant_data.cost_layers c
  JOIN tenant_data.stock_transactions p ON p.id = c.transaction_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'purchase_orders.supplier_id', count(*)
  FROM tenant_data.purchase_orders c
  JOIN tenant_data.suppliers p ON p.id = c.supplier_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'po_lines.po_id' AS link, count(*) AS bad
  FROM tenant_data.po_lines c
  LEFT JOIN tenant_data.purchase_orders p ON p.id = c.po_id
 WHERE p.id IS NULL
UNION ALL
SELECT 'po_lines.product_id', count(*)
  FROM tenant_data.po_lines c
  JOIN tenant_data.purchase_orders po ON po.id = c.po_id
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> po.tenant_id
UNION ALL
SELECT 'expenses.category_id', count(*)
  FROM tenant_data.expenses c
  JOIN tenant_data.expense_categories p ON p.id = c.category_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'expenses.staff_id', count(*)
  FROM tenant_data.expenses c
  JOIN tenant_data.staff p ON p.id = c.staff_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'customer_collections.customer_id', count(*)
  FROM tenant_data.customer_collections c
  JOIN tenant_data.customers p ON p.id = c.customer_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'customer_collections.collected_by', count(*)
  FROM tenant_data.customer_collections c
  JOIN tenant_data.staff p ON p.id = c.collected_by
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'account_transfers.from_account_id', count(*)
  FROM tenant_data.account_transfers c
  JOIN tenant_data.accounts p ON p.id = c.from_account_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'account_transfers.to_account_id', count(*)
  FROM tenant_data.account_transfers c
  JOIN tenant_data.accounts p ON p.id = c.to_account_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'account_transfers.staff_id', count(*)
  FROM tenant_data.account_transfers c
  JOIN tenant_data.staff p ON p.id = c.staff_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'credit_notes.invoice_id', count(*)
  FROM tenant_data.credit_notes c
  JOIN tenant_data.invoices p ON p.id = c.invoice_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'debit_notes.supplier_id', count(*)
  FROM tenant_data.debit_notes c
  JOIN tenant_data.suppliers p ON p.id = c.supplier_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'debit_notes.po_id', count(*)
  FROM tenant_data.debit_notes c
  JOIN tenant_data.purchase_orders p ON p.id = c.po_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'supplier_payments.supplier_id', count(*)
  FROM tenant_data.supplier_payments c
  JOIN tenant_data.suppliers p ON p.id = c.supplier_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'supplier_payments.po_id', count(*)
  FROM tenant_data.supplier_payments c
  JOIN tenant_data.purchase_orders p ON p.id = c.po_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'credit_note_lines.credit_note_id', count(*)
  FROM tenant_data.credit_note_lines c
  JOIN tenant_data.credit_notes p ON p.id = c.credit_note_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'credit_note_lines.invoice_id', count(*)
  FROM tenant_data.credit_note_lines c
  JOIN tenant_data.invoices p ON p.id = c.invoice_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'credit_note_lines.invoice_line_id', count(*)
  FROM tenant_data.credit_note_lines c
  JOIN tenant_data.invoice_lines p ON p.id = c.invoice_line_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'credit_note_lines.product_id', count(*)
  FROM tenant_data.credit_note_lines c
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'stock_levels.branch_id', count(*)
  FROM tenant_data.stock_levels c
  JOIN tenant_data.branches p ON p.id = c.branch_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'stock_levels.product_id', count(*)
  FROM tenant_data.stock_levels c
  JOIN tenant_data.products p ON p.id = c.product_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'staff.branch_id', count(*)
  FROM tenant_data.staff c
  JOIN tenant_data.branches p ON p.id = c.branch_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'payment_refunds.payment_id', count(*)
  FROM tenant_data.payment_refunds c
  JOIN tenant_data.payments p ON p.id = c.payment_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'payment_refunds.invoice_id', count(*)
  FROM tenant_data.payment_refunds c
  JOIN tenant_data.invoices p ON p.id = c.invoice_id
 WHERE p.tenant_id <> c.tenant_id
UNION ALL
SELECT 'payment_refunds.credit_note_id', count(*)
  FROM tenant_data.payment_refunds c
  JOIN tenant_data.credit_notes p ON p.id = c.credit_note_id
 WHERE p.tenant_id <> c.tenant_id;
