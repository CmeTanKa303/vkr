#!/usr/bin/env bash
# Запуск локального сервера Next Burger (Linux/macOS).
# Windows: используйте start.bat
set -e
cd "$(dirname "$0")/backend"

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/3] Создаю виртуальное окружение..."
  python3 -m venv .venv
  echo "[2/3] Устанавливаю зависимости..."
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/python -m pip install -r requirements.txt
else
  echo "[OK] Окружение уже настроено."
fi

echo "[3/3] Сервер: http://localhost:8000  (Ctrl+C — остановить)"
echo "      Админ-панель: http://localhost:8000/admin"
echo "      Документация API: http://localhost:8000/docs"
exec ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
