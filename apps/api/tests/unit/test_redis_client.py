import pytest

from redis_client import build_ipn_idempotency_key


def test_ipn_idempotency_key_prefers_gateway_txn_id():
    k = build_ipn_idempotency_key("Demo", "sslcommerz", "ORD-1", "VAL-99")
    assert k == "shopper:ipn:v1:demo:sslcommerz:val-99"


def test_ipn_idempotency_key_falls_back_to_order_ref():
    k = build_ipn_idempotency_key("acme", "sslcommerz", "ORD-1", "")
    assert k == "shopper:ipn:v1:acme:sslcommerz:ord-1"


def test_ipn_idempotency_key_rejects_empty_refs():
    with pytest.raises(ValueError):
        build_ipn_idempotency_key("acme", "sslcommerz", "", "")
