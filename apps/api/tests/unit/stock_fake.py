"""In-memory stand-in for the branches and stock_levels SQL in services.stock.

Router fakes call `stock.handles(sql)` first and pass the call on when it is true.
"""

from decimal import Decimal
from uuid import UUID

MAIN_BRANCH = UUID("00000000-0000-0000-0000-0000000000b1")


class StockLevels:
    def __init__(self, levels=None, branches=(MAIN_BRANCH,)):
        # levels: {product_id: qty} at the main branch, or {(branch_id, product_id): qty}
        self.levels = {}
        for key, qty in (levels or {}).items():
            key = key if isinstance(key, tuple) else (MAIN_BRANCH, key)
            self.levels[key] = Decimal(str(qty))
        self.branches = set(branches)
        self.locked = []

    @staticmethod
    def handles(sql: str) -> bool:
        return "tenant_data.branches" in sql or "tenant_data.stock_levels" in sql

    def at(self, product_id, branch_id=MAIN_BRANCH) -> Decimal:
        return self.levels.get((branch_id, product_id), Decimal("0"))

    async def fetchval(self, sql, *args):
        if "WHERE is_main" in sql:
            return MAIN_BRANCH
        if "FROM tenant_data.branches" in sql:
            return args[0] if args[0] in self.branches else None
        if "UPDATE tenant_data.stock_levels" in sql:
            branch_id, product_id, delta = args
            left = self.at(product_id, branch_id) + Decimal(str(delta))
            if (branch_id, product_id) not in self.levels or left < 0:
                return None
            self.levels[(branch_id, product_id)] = left
            return left
        if "SUM(quantity)" in sql and "branch_id <> $2" in sql:
            product_id, branch_id = args
            return sum((q for (b, p), q in self.levels.items() if p == product_id and b != branch_id), Decimal("0"))
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        branch_id, product_ids = args
        self.locked.append((branch_id, list(product_ids)))
        return [
            {"product_id": p, "quantity": self.levels[(branch_id, p)]}
            for p in product_ids
            if (branch_id, p) in self.levels
        ]

    async def execute(self, sql, *args):
        _tenant, branch_id, product_id, delta = args
        self.levels[(branch_id, product_id)] = self.at(product_id, branch_id) + Decimal(str(delta))
