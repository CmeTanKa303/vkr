"""Модель данных (ORM).

Соответствует логической модели из ВКR (9 сущностей):
CATEGORY, PRODUCT, VARIANT, INGREDIENT, PRODUCT_INGREDIENT,
USERS, ORDERS, ORDER_ITEM, ORDER_ITEM_INGREDIENT.

Ключевой принцип: цена фиксируется в позиции заказа (ORDER_ITEM.unit_price,
ORDER_ITEM_INGREDIENT.price) — ранее оформленные заказы не меняются при
изменении цен в каталоге.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Каталог
# ---------------------------------------------------------------------------
class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    sort_order = Column(Integer, nullable=False, default=0)

    products = relationship(
        "Product", back_populates="category", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    image_url = Column(Text, nullable=False, default="")
    category_id = Column(
        Integer, ForeignKey("category.id", ondelete="CASCADE"), nullable=False
    )
    # Конструктор (бургер с выбором размера/типа/ингредиентов) либо простой товар
    is_constructor = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)

    category = relationship("Category", back_populates="products")
    variants = relationship(
        "Variant",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="Variant.id",
    )
    product_ingredients = relationship(
        "ProductIngredient",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class Variant(Base):
    """Вариант товара: сочетание размера и типа со своей ценой.

    Для простых товаров (не конструктор) — одна запись с size=None, type=None.
    size: 20 / 30 / 40 (маленький / средний / большой), type: 1 / 2 (классич. / острый)
    """

    __tablename__ = "variant"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    size = Column(Integer, nullable=True)
    type = Column(Integer, nullable=True)
    price = Column(Integer, nullable=False)

    product = relationship("Product", back_populates="variants")


class Ingredient(Base):
    __tablename__ = "ingredient"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    price = Column(Integer, nullable=False, default=0)
    image_url = Column(Text, nullable=False, default="")

    product_ingredients = relationship(
        "ProductIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )


class ProductIngredient(Base):
    """Связь «многие-ко-многим» товар ↔ ингредиент.

    Перечисляет доступные для добавления ингредиенты конструктора и те,
    что входят в состав по умолчанию.
    """

    __tablename__ = "product_ingredient"
    __table_args__ = (
        UniqueConstraint("product_id", "ingredient_id", name="uq_product_ingredient"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(
        Integer, ForeignKey("product.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id = Column(
        Integer, ForeignKey("ingredient.id", ondelete="CASCADE"), nullable=False
    )

    product = relationship("Product", back_populates="product_ingredients")
    ingredient = relationship("Ingredient", back_populates="product_ingredients")


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(120), nullable=False, default="")
    phone = Column(String(40), nullable=False, default="")
    role = Column(String(20), nullable=False, default="user")  # user | admin
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    orders = relationship("Order", back_populates="user")


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(String(20), nullable=False, default="new")
    # new -> cooking -> delivering -> done | cancelled
    total = Column(Integer, nullable=False, default=0)
    customer_name = Column(String(120), nullable=False, default="")
    phone = Column(String(40), nullable=False, default="")
    address = Column(Text, nullable=False, default="")
    comment = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_item"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(
        Integer, ForeignKey("product.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String(200), nullable=False)
    size = Column(Integer, nullable=True)
    type = Column(Integer, nullable=True)
    unit_price = Column(Integer, nullable=False)  # цена за единицу на момент заказа
    quantity = Column(Integer, nullable=False, default=1)

    order = relationship("Order", back_populates="items")
    ingredients = relationship(
        "OrderItemIngredient",
        back_populates="order_item",
        cascade="all, delete-orphan",
    )


class OrderItemIngredient(Base):
    __tablename__ = "order_item_ingredient"

    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(
        Integer, ForeignKey("order_item.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_id = Column(
        Integer, ForeignKey("ingredient.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String(120), nullable=False)
    price = Column(Integer, nullable=False)  # цена добавки на момент заказа

    order_item = relationship("OrderItem", back_populates="ingredients")
