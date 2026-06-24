"""Точка входа приложения Next Burger (FastAPI).

Запуск:
    uvicorn app.main:app --reload        (из каталога backend)

Приложение:
  * создаёт таблицы и наполняет БД начальными данными при первом запуске;
  * предоставляет REST API под /api/*;
  * отдаёт клиент-SPA (/) и админ-панель (/admin);
  * интерактивная документация API — /docs (Swagger UI).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, SessionLocal, engine
from .routers import admin, auth, catalog, orders
from .seed import run_seed

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
UPLOAD_DIR = BACKEND_DIR / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаём таблицы и наполняем БД при старте
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Next Burger API",
    description="REST API системы онлайн-заказов (ВКР). JSON, JWT-аутентификация.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — на случай, если клиент открывается с другого источника
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def security_headers(request, call_next):
    # Запрещаем браузеру угадывать тип содержимого (защита загруженных файлов)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# REST API
app.include_router(catalog.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(admin.router)

# Загруженные изображения
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Отдача клиентской части
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/admin", include_in_schema=False)
def serve_admin():
    return FileResponse(str(FRONTEND_DIR / "admin.html"))


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
