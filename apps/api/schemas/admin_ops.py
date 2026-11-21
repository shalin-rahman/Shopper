from __future__ import annotations
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class AccountTransferCreate(BaseModel):
    from_account_code: str = Field(min_length=1, max_length=50)
    to_account_code: str = Field(min_length=1, max_length=50)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _different(self):
        if self.from_account_code == self.to_account_code:
            raise ValueError("from and to accounts must differ")
        return self


class ExpenseCreate(BaseModel):
    category_id: UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)


class StaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    role: Literal["cashier", "accountant", "manager", "admin"] = "cashier"
    branch_id: UUID | None = None
