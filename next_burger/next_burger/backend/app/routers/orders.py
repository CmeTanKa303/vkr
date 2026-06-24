"""Оформление и просмотр заказов.

  POST /api/orders       — оформить заказ (требует авторизации)
  GET  /api/orders       — мои заказы
  GET  /api/orders/{id}  — заказ и его статус

Важно для безопасности: цены НЕ берутся от клиента, а пересчитываются на
сервере из БД. Зафиксированные цены сохраняются в позициях заказа.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..serializers import order_to_dict

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    data: schemas.OrderCreateIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    order = models.Order(
        user_id=user.id,
        status="new",
        total=0,
        customer_name=(data.customerName or user.name).strip(),
        phone=(data.phone or user.phone).strip(),
        address=data.address.strip(),
        comment=data.comment.strip(),
    )

    total = 0
    for line in data.items:
        product = (
            db.query(models.Product)
            .filter(models.Product.id == line.productId)
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=400, detail=f"Товар #{line.productId} не найден"
            )

        # Подбор варианта (размер/тип) и базовой цены — с сервера, не от клиента
        if not product.variants:
            raise HTTPException(
                status_code=400,
                detail=f"У товара «{product.name}» не задана цена",
            )

        def _match(size_val, type_val):
            return next(
                (v for v in product.variants if v.size == size_val and v.type == type_val),
                None,
            )

        if product.is_constructor:
            variant = _match(line.size, line.type)
            if variant is None:
                if line.size is None and line.type is None:
                    # клиент не выбрал размер/тип — берём базовый вариант
                    variant = product.variants[0]
                else:
                    # вариант ЗАДАН, но такого нет — это ошибка, а не повод подменить цену
                    raise HTTPException(
                        status_code=400,
                        detail=f"Выбранный вариант (размер/тип) товара «{product.name}» недоступен",
                    )
        else:
            # простой товар: при нескольких вариантах подбираем по запросу
            variant = _match(line.size, line.type) if (
                line.size is not None or line.type is not None
            ) else None
            if variant is None:
                variant = product.variants[0]

        base_price = variant.price
        size, vtype = variant.size, variant.type

        order_item = models.OrderItem(
            product_id=product.id,
            name=product.name,
            size=size,
            type=vtype,
            unit_price=base_price,
            quantity=line.quantity,
        )

        # Добавки (только для конструктора) — цена с сервера
        if product.is_constructor and line.ingredientIds:
            allowed = {pi.ingredient_id for pi in product.product_ingredients}
            for ing_id in line.ingredientIds:
                if ing_id not in allowed:
                    continue  # игнорируем ингредиенты не из состава товара
                ing = (
                    db.query(models.Ingredient)
                    .filter(models.Ingredient.id == ing_id)
                    .first()
                )
                if not ing:
                    continue
                order_item.unit_price += ing.price
                order_item.ingredients.append(
                    models.OrderItemIngredient(
                        ingredient_id=ing.id, name=ing.name, price=ing.price
                    )
                )

        total += order_item.unit_price * order_item.quantity
        order.items.append(order_item)

    order.total = total
    db.add(order)
    db.commit()
    db.refresh(order)
    return order_to_dict(order)


@router.get("")
def my_orders(
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    orders = (
        db.query(models.Order)
        .filter(models.Order.user_id == user.id)
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .all()
    )
    return [order_to_dict(o) for o in orders]


@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")
    return order_to_dict(order)
