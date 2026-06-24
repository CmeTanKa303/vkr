"""Каталог: категории, ингредиенты, товары (поиск и фильтры).

Эндпоинты соответствуют ВКР:
  GET /api/categories
  GET /api/ingredients
  GET /api/products       — каталог, поиск, фильтры
  GET /api/products/{id}  — детальная позиция
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..serializers import ingredient_to_dict, product_to_dict

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = (
        db.query(models.Category)
        .order_by(models.Category.sort_order, models.Category.id)
        .all()
    )
    return [{"id": c.id, "name": c.name, "sortOrder": c.sort_order} for c in cats]


@router.get("/ingredients")
def list_ingredients(db: Session = Depends(get_db)):
    ings = db.query(models.Ingredient).order_by(models.Ingredient.id).all()
    return [ingredient_to_dict(i) for i in ings]


def _parse_int_list(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


@router.get("/products")
def list_products(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    categoryId: Optional[int] = None,
    priceFrom: Optional[int] = None,
    priceTo: Optional[int] = None,
    types: Optional[str] = Query(None, description="через запятую: 1,2"),
    sizes: Optional[str] = Query(None, description="через запятую: 20,30,40"),
    ingredients: Optional[str] = Query(None, description="id через запятую"),
):
    """Каталог с поддержкой поиска и фильтрации на стороне сервера.

    Клиент-SPA для скорости фильтрует загруженный каталог сам, но API
    поддерживает все фильтры — это демонстрируется в /docs.
    """
    products = (
        db.query(models.Product)
        .order_by(models.Product.sort_order, models.Product.id)
        .all()
    )
    result = [product_to_dict(p) for p in products]

    if search:
        q = search.lower().strip()
        result = [p for p in result if q in p["name"].lower()]
    if categoryId is not None:
        result = [p for p in result if p["categoryId"] == categoryId]
    if priceFrom is not None:
        result = [p for p in result if p["minPrice"] >= priceFrom]
    if priceTo is not None:
        result = [p for p in result if p["minPrice"] <= priceTo]

    type_filter = set(_parse_int_list(types))
    if type_filter:
        result = [
            p
            for p in result
            if p["isConstructor"]
            and any(it["type"] in type_filter for it in p["items"])
        ]
    size_filter = set(_parse_int_list(sizes))
    if size_filter:
        result = [
            p
            for p in result
            if p["isConstructor"]
            and any(it["size"] in size_filter for it in p["items"])
        ]
    ing_filter = set(_parse_int_list(ingredients))
    if ing_filter:
        result = [
            p
            for p in result
            if p["isConstructor"] and ing_filter.issubset(set(p["ingredientIds"]))
        ]

    return result


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product_to_dict(p)
