"""Админ-модуль: управление каталогом и заказами.

Все эндпоинты требуют роль admin (JWT). Реализует функцию «добавлять товары»
и сопровождение заказов (изменение статуса).

  GET    /api/admin/stats
  GET    /api/admin/products            POST /api/admin/products
  PUT    /api/admin/products/{id}       DELETE /api/admin/products/{id}
  POST   /api/admin/ingredients         PUT/DELETE /api/admin/ingredients/{id}
  POST   /api/admin/categories          PUT/DELETE /api/admin/categories/{id}
  GET    /api/admin/orders              PATCH /api/admin/orders/{id}
  POST   /api/admin/upload              (загрузка картинки)
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..serializers import ingredient_to_dict, order_to_dict, product_to_dict

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(security.require_admin)],
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
# SVG намеренно НЕ разрешён: это XML, который браузер исполняет как документ
# (вектор stored-XSS). Разрешаем только растровые форматы.
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 МБ


def _looks_like_image(data: bytes) -> bool:
    """Проверка реального типа файла по сигнатуре (magic bytes), а не по имени."""
    if data[:3] == b"\xff\xd8\xff":               # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":           # PNG
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):         # GIF
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WEBP
        return True
    return False


# ---------------------------------------------------------------------------
# Статистика для дашборда
# ---------------------------------------------------------------------------
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "products": db.query(models.Product).count(),
        "categories": db.query(models.Category).count(),
        "ingredients": db.query(models.Ingredient).count(),
        "orders": db.query(models.Order).count(),
        "users": db.query(models.User).count(),
        "revenue": sum(
            o.total
            for o in db.query(models.Order)
            .filter(models.Order.status != "cancelled")
            .all()
        ),
    }


# ---------------------------------------------------------------------------
# Товары
# ---------------------------------------------------------------------------
@router.get("/products")
def admin_list_products(db: Session = Depends(get_db)):
    products = (
        db.query(models.Product)
        .order_by(models.Product.category_id, models.Product.sort_order, models.Product.id)
        .all()
    )
    return [product_to_dict(p) for p in products]


def _validate_refs(db: Session, data: schemas.ProductIn):
    cat = db.query(models.Category).filter(models.Category.id == data.categoryId).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Категория не найдена")
    for ing_id in data.ingredientIds:
        ing = db.query(models.Ingredient).filter(models.Ingredient.id == ing_id).first()
        if not ing:
            raise HTTPException(
                status_code=400, detail=f"Ингредиент #{ing_id} не найден"
            )


def _apply_variants_and_ingredients(product: models.Product, data: schemas.ProductIn):
    # варианты
    product.variants.clear()
    for v in data.items:
        product.variants.append(
            models.Variant(size=v.size, type=v.type, price=v.price)
        )
    # состав (только осмысленно для конструктора, но сохраняем как задано)
    product.product_ingredients.clear()
    seen = set()
    for ing_id in data.ingredientIds:
        if ing_id in seen:
            continue
        seen.add(ing_id)
        product.product_ingredients.append(
            models.ProductIngredient(ingredient_id=ing_id)
        )


@router.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(data: schemas.ProductIn, db: Session = Depends(get_db)):
    _validate_refs(db, data)
    product = models.Product(
        name=data.name.strip(),
        image_url=data.imageUrl.strip(),
        category_id=data.categoryId,
        is_constructor=data.isConstructor,
        description=data.description.strip(),
    )
    _apply_variants_and_ingredients(product, data)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product_to_dict(product)


@router.put("/products/{product_id}")
def update_product(
    product_id: int, data: schemas.ProductIn, db: Session = Depends(get_db)
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    _validate_refs(db, data)
    product.name = data.name.strip()
    product.image_url = data.imageUrl.strip()
    product.category_id = data.categoryId
    product.is_constructor = data.isConstructor
    product.description = data.description.strip()
    _apply_variants_and_ingredients(product, data)
    db.commit()
    db.refresh(product)
    return product_to_dict(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    db.delete(product)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Ингредиенты
# ---------------------------------------------------------------------------
@router.get("/ingredients")
def admin_list_ingredients(db: Session = Depends(get_db)):
    ings = db.query(models.Ingredient).order_by(models.Ingredient.id).all()
    return [ingredient_to_dict(i) for i in ings]


@router.post("/ingredients", status_code=status.HTTP_201_CREATED)
def create_ingredient(data: schemas.IngredientIn, db: Session = Depends(get_db)):
    exists = (
        db.query(models.Ingredient)
        .filter(models.Ingredient.name == data.name.strip())
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Такой ингредиент уже есть")
    ing = models.Ingredient(
        name=data.name.strip(), price=data.price, image_url=data.imageUrl.strip()
    )
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ingredient_to_dict(ing)


@router.put("/ingredients/{ingredient_id}")
def update_ingredient(
    ingredient_id: int, data: schemas.IngredientIn, db: Session = Depends(get_db)
):
    ing = (
        db.query(models.Ingredient)
        .filter(models.Ingredient.id == ingredient_id)
        .first()
    )
    if not ing:
        raise HTTPException(status_code=404, detail="Ингредиент не найден")
    ing.name = data.name.strip()
    ing.price = data.price
    ing.image_url = data.imageUrl.strip()
    db.commit()
    db.refresh(ing)
    return ingredient_to_dict(ing)


@router.delete("/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ing = (
        db.query(models.Ingredient)
        .filter(models.Ingredient.id == ingredient_id)
        .first()
    )
    if not ing:
        raise HTTPException(status_code=404, detail="Ингредиент не найден")
    db.delete(ing)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Категории
# ---------------------------------------------------------------------------
@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(data: schemas.CategoryIn, db: Session = Depends(get_db)):
    exists = (
        db.query(models.Category)
        .filter(models.Category.name == data.name.strip())
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Такая категория уже есть")
    cat = models.Category(name=data.name.strip(), sort_order=data.sortOrder)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "sortOrder": cat.sort_order}


@router.put("/categories/{category_id}")
def update_category(
    category_id: int, data: schemas.CategoryIn, db: Session = Depends(get_db)
):
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    cat.name = data.name.strip()
    cat.sort_order = data.sortOrder
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "sortOrder": cat.sort_order}


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    if cat.products:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить категорию с товарами. Сначала перенесите/удалите товары.",
        )
    db.delete(cat)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Заказы
# ---------------------------------------------------------------------------
@router.get("/orders")
def admin_list_orders(db: Session = Depends(get_db)):
    orders = (
        db.query(models.Order)
        .order_by(models.Order.created_at.desc(), models.Order.id.desc())
        .all()
    )
    return [order_to_dict(o) for o in orders]


@router.patch("/orders/{order_id}")
def update_order_status(
    order_id: int, data: schemas.OrderStatusIn, db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = data.status
    db.commit()
    db.refresh(order)
    return order_to_dict(order)


# ---------------------------------------------------------------------------
# Загрузка изображений
# ---------------------------------------------------------------------------
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Допустимые форматы: {', '.join(sorted(ALLOWED_IMAGE_EXT))}",
        )
    # читаем максимум на 1 байт больше лимита, чтобы не держать в памяти лишнее
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Файл больше 5 МБ")
    if not _looks_like_image(content):
        raise HTTPException(
            status_code=400, detail="Файл не является изображением (jpg/png/gif/webp)"
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / safe_name
    dest.write_bytes(content)
    return {"url": f"/uploads/{safe_name}"}
