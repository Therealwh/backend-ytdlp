@echo off
REM Скрипт для быстрого обновления backend на GitHub (Windows)

echo 🚀 Обновление backend на GitHub...

REM Переходим в папку backend
cd /d "%~dp0"

REM Проверяем есть ли git
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Git не установлен!
    pause
    exit /b 1
)

REM Проверяем инициализирован ли git
if not exist .git (
    echo 📦 Инициализируем git репозиторий...
    git init
    git branch -M main
    
    echo ⚠️  Нужно добавить remote URL!
    echo Выполни: git remote add origin https://github.com/ВАШ_USERNAME/youtube-downloader-backend.git
    pause
    exit /b 1
)

REM Добавляем все файлы
echo 📝 Добавляем файлы...
git add .

REM Коммитим
echo 💾 Создаём коммит...
git commit -m "Fix CORS and add proxy for YouTube downloads"

REM Пушим
echo ⬆️  Загружаем на GitHub...
git push origin main

echo ✅ Готово! Railway автоматически задеплоит новую версию.
echo 🔍 Проверь статус на https://railway.app/dashboard

pause
