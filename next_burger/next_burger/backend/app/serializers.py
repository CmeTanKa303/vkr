"""Преобразование ORM-объектов в JSON-совместимые словари для ответов API."""

from . import models


def ingredient_to_dict(ing: models.Ingredient) -> dict:
    return {
        "id": ing.id,
        "name": ing.name,
        "price": ing.price,
        "imageUrl": ing.image_url,
    }


def product_to_dict(p: models.Product) -> dict:
    items = [
        {"size": v.size, "type": v.type, "price": v.price} for v in p.variants
    ]
    min_price = min((v.price for v in p.variants), default=0)
    ingredient_ids = [pi.ingredient_id for pi in p.product_ingredients]
    return {
        "id": p.id,
        "name": p.name,
        "imageUrl": p.image_url,
        "categoryId": p.category_id,
        "isConstructor": p.is_constructor,
        "description": p.description,
        "ingredientIds": ingredient_ids,
        "items": items,
        "minPrice": min_price,
    }


def order_to_dict(order: models.Order) -> dict:
    items = []
    for it in order.items:
        items.append(
            {
                "name": it.name,
                "size": it.size,
                "type": it.type,
                "unitPrice": it.unit_price,
                "quantity": it.quantity,
                "lineTotal": it.unit_price * it.quantity,
                "ingredients": [
                    {"name": ing.name, "price": ing.price} for ing in it.ingredients
                ],
            }
        )
    return {
        "id": order.id,
        "status": order.status,
        "total": order.total,
        "customerName": order.customer_name,
        "phone": order.phone,
        "address": order.address,
        "comment": order.comment,
        "createdAt": order.created_at.isoformat() if order.created_at else "",
        "items": items,
    }
