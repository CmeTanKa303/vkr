"""Начальное наполнение базы данных.

Переносит исходный каталог (категории, ингредиенты, товары) из прежней
статической версии в БД и создаёт учётную запись администратора.
Выполняется один раз — если база уже содержит данные, повторно не наполняет.
"""

from sqlalchemy.orm import Session

from . import models, security

# Учётная запись администратора по умолчанию
ADMIN_EMAIL = "admin@nextburger.ru"
ADMIN_PASSWORD = "admin123"

# Демонстрационный обычный пользователь
DEMO_EMAIL = "user@nextburger.ru"
DEMO_PASSWORD = "user123"

CATEGORIES = ["Бургеры", "Завтрак", "Закуски", "Коктейли", "Напитки"]

# (orig_id, name, price, image_url)
INGREDIENTS = [
    (1, "Двойная котлета", 149, "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=110&h=110&fit=crop&crop=center"),
    (2, "Сыр Чеддер", 59, "https://images.unsplash.com/photo-1589881133825-b9c24c2b5e85?w=110&h=110&fit=crop"),
    (3, "Бекон", 79, "https://images.unsplash.com/photo-1528607929212-2636ec44253e?w=110&h=110&fit=crop"),
    (4, "Острый перец", 49, "https://cdn.dodostatic.net/static/Img/Ingredients/11ee95b6bfdf98fb88a113db92d7b3df.png"),
    (5, "Жареный лук", 39, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A22FA54A81411E9AFA60AE6464C"),
    (6, "Маринованные огурцы", 39, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A21DA51A81211E9EA89958D782B"),
    (7, "Авокадо", 89, "https://images.unsplash.com/photo-1632158929022-84e68b6d8b56?w=110&h=110&fit=crop"),
    (8, "Шампиньоны", 59, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A22FA54A81411E9AFA67259A324"),
    (9, "Яйцо жареное", 49, "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=110&h=110&fit=crop"),
    (10, "Свежие томаты", 39, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A39D824A82E11E9AFA7AC1A1D67"),
    (11, "Листья салата", 29, "https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=110&h=110&fit=crop"),
    (12, "Красный лук", 39, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A22FA54A81411E9AFA60AE6464C"),
    (13, "Халапеньо", 49, "https://cdn.dodostatic.net/static/Img/Ingredients/11ee95b6bfdf98fb88a113db92d7b3df.png"),
    (14, "Соус BBQ", 59, "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?w=110&h=110&fit=crop"),
    (15, "Соус Чили", 49, "https://images.unsplash.com/photo-1528207776546-365bb710ee93?w=110&h=110&fit=crop"),
    (16, "Сыр Колби", 69, "https://cdn.dodostatic.net/static/Img/Ingredients/000D3A22FA54A81411E9AFA69C1FE796"),
    (17, "Хрустящий лук", 49, "https://images.unsplash.com/photo-1639024471283-03518883512d?w=110&h=110&fit=crop"),
]

# name, category_name, image_url, is_constructor, [ingredient_orig_ids], [(size,type,price)]
PRODUCTS = [
    # Бургеры
    ("Классический Смэш", "Бургеры",
     "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&h=300&fit=crop",
     True, [1, 2, 6, 10, 11],
     [(20, 1, 299), (30, 1, 449), (40, 1, 599), (20, 2, 329), (30, 2, 479), (40, 2, 629)]),
    ("BBQ Барбекю", "Бургеры",
     "https://images.unsplash.com/photo-1550547660-d9450f859349?w=300&h=300&fit=crop",
     True, [1, 2, 3, 5, 12, 14],
     [(20, 1, 349), (30, 1, 499), (40, 1, 649), (20, 2, 379), (30, 2, 529)]),
    ("Чизбургер Делюкс", "Бургеры",
     "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=300&h=300&fit=crop",
     True, [1, 2, 16, 6, 10, 5, 11],
     [(20, 1, 389), (30, 2, 549), (40, 2, 699)]),

    # Завтрак
    ("Яичный Бургер Утренний", "Завтрак",
     "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=300&h=300&fit=crop",
     False, [], [(None, None, 259)]),
    ("Бекон и Яйцо", "Завтрак",
     "https://images.unsplash.com/photo-1553979459-d2229ba7433a?w=300&h=300&fit=crop",
     False, [], [(None, None, 279)]),
    ("Кофе Латте", "Завтрак",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61B0C26A3F85D97A78FEEE00AD.webp",
     False, [], [(None, None, 199)]),

    # Закуски
    ("Картофель Фри", "Закуски",
     "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=300&h=300&fit=crop",
     False, [], [(None, None, 149)]),
    ("Куриные Наггетсы", "Закуски",
     "https://media.dodostatic.net/image/r:292x292/11EE7D618B5C7EC29350069AE9532C6E.webp",
     False, [], [(None, None, 189)]),
    ("Луковые Кольца", "Закуски",
     "https://images.unsplash.com/photo-1639024471283-03518883512d?w=300&h=300&fit=crop",
     False, [], [(None, None, 179)]),
    ("Хот-Дог Классический", "Закуски",
     "https://images.unsplash.com/photo-1612392062631-94f26a4ea9b9?w=300&h=300&fit=crop",
     False, [], [(None, None, 219)]),
    ("Острый Хот-Дог 🌶️🌶️", "Закуски",
     "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=300&h=300&fit=crop",
     False, [], [(None, None, 239)]),

    # Коктейли
    ("Банановый молочный коктейль", "Коктейли",
     "https://media.dodostatic.net/image/r:292x292/11EEE20B8772A72A9B60CFB20012C185.webp",
     False, [], [(None, None, 249)]),
    ("Карамельное яблоко молочный коктейль", "Коктейли",
     "https://media.dodostatic.net/image/r:292x292/11EE79702E2A22E693D96133906FB1B8.webp",
     False, [], [(None, None, 299)]),
    ("Молочный коктейль с печеньем Орео", "Коктейли",
     "https://media.dodostatic.net/image/r:292x292/11EE796FA1F50F8F8111A399E4C1A1E3.webp",
     False, [], [(None, None, 319)]),
    ("Классический молочный коктейль 👶", "Коктейли",
     "https://media.dodostatic.net/image/r:292x292/11EE796F93FB126693F96CB1D3E403FB.webp",
     False, [], [(None, None, 229)]),

    # Напитки
    ("Ирландский Капучино", "Напитки",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61999EBDA59C10E216430A6093.webp",
     False, [], [(None, None, 179)]),
    ("Кофе Карамельный капучино", "Напитки",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61AED6B6D4BFDAD4E58D76CF56.webp",
     False, [], [(None, None, 199)]),
    ("Кофе Кокосовый латте", "Напитки",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61B19FA07090EE88B0ED347F42.webp",
     False, [], [(None, None, 249)]),
    ("Кофе Американо", "Напитки",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61B044583596548A59078BBD33.webp",
     False, [], [(None, None, 149)]),
    ("Кофе Латте ", "Напитки",
     "https://media.dodostatic.net/image/r:292x292/11EE7D61B0C26A3F85D97A78FEEE00AD.webp",
     False, [], [(None, None, 199)]),
]


def ensure_admin(db: Session) -> None:
    """Гарантирует наличие администратора и демо-пользователя."""
    admin = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()
    if not admin:
        db.add(
            models.User(
                email=ADMIN_EMAIL,
                password_hash=security.hash_password(ADMIN_PASSWORD),
                name="Администратор",
                role="admin",
            )
        )
    demo = db.query(models.User).filter(models.User.email == DEMO_EMAIL).first()
    if not demo:
        db.add(
            models.User(
                email=DEMO_EMAIL,
                password_hash=security.hash_password(DEMO_PASSWORD),
                name="Гость Демо",
                phone="+7 900 000-00-00",
                role="user",
            )
        )
    db.commit()


def seed_catalog(db: Session) -> None:
    """Наполняет каталог, если он пуст."""
    if db.query(models.Category).count() > 0:
        return

    # Категории
    cat_by_name = {}
    for idx, name in enumerate(CATEGORIES):
        cat = models.Category(name=name, sort_order=idx)
        db.add(cat)
        cat_by_name[name] = cat
    db.flush()

    # Ингредиенты
    ing_by_orig = {}
    for orig_id, name, price, url in INGREDIENTS:
        ing = models.Ingredient(name=name, price=price, image_url=url)
        db.add(ing)
        ing_by_orig[orig_id] = ing
    db.flush()

    # Товары
    for sort_idx, (name, cat_name, url, is_constructor, ing_ids, variants) in enumerate(PRODUCTS):
        product = models.Product(
            name=name.strip(),
            image_url=url,
            category=cat_by_name[cat_name],
            is_constructor=is_constructor,
            sort_order=sort_idx,
        )
        for size, vtype, price in variants:
            product.variants.append(models.Variant(size=size, type=vtype, price=price))
        for ing_id in ing_ids:
            ing = ing_by_orig.get(ing_id)
            if ing is not None:
                product.product_ingredients.append(
                    models.ProductIngredient(ingredient=ing)
                )
        db.add(product)

    db.commit()


def run_seed(db: Session) -> None:
    seed_catalog(db)
    ensure_admin(db)
