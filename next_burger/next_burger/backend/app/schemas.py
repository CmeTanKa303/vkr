"""Схемы запросов/ответов (Pydantic).

Валидация входных данных — часть требований к безопасности (см. ВКР):
проверка форматов, длины, диапазонов до обращения к БД.
Имена полей — в camelCase, чтобы напрямую совпадать с JSON клиента (JS).
"""

import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_image_url(v: str) -> str:
    """Разрешаем только относительные пути (/uploads/...) и http(s)-ссылки.

    Блокируем потенциально опасные схемы (javascript:, data:, vbscript:).
    """
    v = (v or "").strip()
    if not v:
        return v
    low = v.lower()
    if low.startswith(("javascript:", "data:", "vbscript:")):
        raise ValueError("Недопустимый URL изображения")
    if not (v.startswith("/") or low.startswith("http://") or low.startswith("https://")):
        raise ValueError("URL изображения должен начинаться с http(s):// или /")
    return v


# ---------------------------------------------------------------------------
# Авторизация / пользователи
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)
    name: str = ""
    phone: str = ""

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Некорректный e-mail")
        return v


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _norm_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    phone: str
    role: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------------------
# Каталог
# ---------------------------------------------------------------------------
class CategoryOut(BaseModel):
    id: int
    name: str


class IngredientOut(BaseModel):
    id: int
    name: str
    price: int
    imageUrl: str


class VariantOut(BaseModel):
    size: Optional[int] = None
    type: Optional[int] = None
    price: int


class ProductOut(BaseModel):
    id: int
    name: str
    imageUrl: str
    categoryId: int
    isConstructor: bool
    description: str
    ingredientIds: List[int]
    items: List[VariantOut]
    minPrice: int


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------
class OrderItemIn(BaseModel):
    productId: int
    size: Optional[int] = None
    type: Optional[int] = None
    quantity: int = Field(ge=1, le=99)
    ingredientIds: List[int] = []


class OrderCreateIn(BaseModel):
    items: List[OrderItemIn] = Field(min_length=1)
    customerName: str = Field("", max_length=120)
    phone: str = Field("", max_length=40)
    address: str = Field("", max_length=500)
    comment: str = Field("", max_length=1000)


class OrderItemIngredientOut(BaseModel):
    name: str
    price: int


class OrderItemOut(BaseModel):
    name: str
    size: Optional[int]
    type: Optional[int]
    unitPrice: int
    quantity: int
    lineTotal: int
    ingredients: List[OrderItemIngredientOut]


class OrderOut(BaseModel):
    id: int
    status: str
    total: int
    customerName: str
    phone: str
    address: str
    comment: str
    createdAt: str
    items: List[OrderItemOut]


# ---------------------------------------------------------------------------
# Админ — ввод
# ---------------------------------------------------------------------------
class VariantIn(BaseModel):
    size: Optional[int] = None
    type: Optional[int] = None
    price: int = Field(ge=0, le=1_000_000)


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    imageUrl: str = ""
    categoryId: int
    isConstructor: bool = False
    description: str = ""
    ingredientIds: List[int] = []
    items: List[VariantIn] = Field(min_length=1)

    @field_validator("imageUrl")
    @classmethod
    def _check_image(cls, v: str) -> str:
        return validate_image_url(v)

    @model_validator(mode="after")
    def _check_consistency(self):
        if not self.items:
            raise ValueError("Нужен хотя бы один вариант с ценой")
        if self.isConstructor:
            # запрещаем дублирующиеся пары (размер, тип)
            seen = set()
            for v in self.items:
                key = (v.size, v.type)
                if key in seen:
                    raise ValueError("Дублирующиеся варианты (размер/тип)")
                seen.add(key)
        else:
            # простой товар — ровно один вариант без размера и типа
            self.items = [self.items[0]]
            self.items[0].size = None
            self.items[0].type = None
        return self


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: int = Field(ge=0, le=1_000_000)
    imageUrl: str = ""

    @field_validator("imageUrl")
    @classmethod
    def _check_image(cls, v: str) -> str:
        return validate_image_url(v)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sortOrder: int = 0


class OrderStatusIn(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: str) -> str:
        allowed = {"new", "cooking", "delivering", "done", "cancelled"}
        if v not in allowed:
            raise ValueError(f"Недопустимый статус. Разрешены: {', '.join(sorted(allowed))}")
        return v
