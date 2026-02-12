# 🚀 Пошаговая инструкция по деплою backend на Railway

## Шаг 1: Подготовка

### 1.1 Создай GitHub репозиторий
1. Зайди на https://github.com
2. Нажми "New repository"
3. Название: `youtube-downloader-backend`
4. Сделай публичным (Public)
5. Создай репозиторий

### 1.2 Загрузи код на GitHub
```bash
cd youtube-downloader/backend-ytdlp
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/ВАШ_USERNAME/youtube-downloader-backend.git
git push -u origin main
```

---

## Шаг 2: Деплой на Railway

### 2.1 Регистрация
1. Зайди на https://railway.app
2. Нажми "Login" → "Login with GitHub"
3. Авторизуй Railway доступ к GitHub

### 2.2 Создание проекта
1. Нажми "New Project"
2. Выбери "Deploy from GitHub repo"
3. Выбери репозиторий `youtube-downloader-backend`
4. Railway автоматически:
   - Определит Python
   - Установит зависимости из `requirements.txt`
   - Запустит через `gunicorn`

### 2.3 Получение URL
1. Дождись окончания деплоя (2-3 минуты)
2. Нажми на проект
3. Перейди в "Settings" → "Networking"
4. Нажми "Generate Domain"
5. Скопируй URL типа: `https://your-app.up.railway.app`

### 2.4 Проверка работы
Открой в браузере:
```
https://your-app.up.railway.app/
```

Должен вернуться JSON:
```json
{
  "status": "ok",
  "message": "YouTube Downloader API with yt-dlp",
  "version": "1.0.0"
}
```

✅ Backend готов!

---

## Шаг 3: Подключение к Frontend

### 3.1 Обновить код frontend

Открой файл `youtube-downloader/src/services/ytdlProxyApi.ts`

Замени строку:
```typescript
const API_BASE_URL = 'https://yt-downloader9.p.rapidapi.com';
```

На:
```typescript
const API_BASE_URL = 'https://your-app.up.railway.app';
```

### 3.2 Убрать RapidAPI ключ

Удали или закомментируй строки с RapidAPI ключом:
```typescript
// const RAPIDAPI_KEY = 'f161d6bffbmsh5a0ccc2fe490703p155c76jsn0d8124f8bd9d';
// const RAPIDAPI_HOST = 'yt-downloader9.p.rapidapi.com';
```

### 3.3 Пересобрать проект
```bash
cd youtube-downloader
npm run build
```

### 3.4 Загрузить на хостинг
Загрузи обновлённый `dist/` на свой хостинг.

✅ Готово! Теперь сайт использует твой бесплатный backend!

---

## Альтернатива: Render.com

Если Railway не подходит, используй Render:

### 1. Регистрация
1. Зайди на https://render.com
2. Зарегистрируйся через GitHub

### 2. Создание Web Service
1. Нажми "New +" → "Web Service"
2. Подключи GitHub репозиторий
3. Настройки:
   - **Name**: youtube-downloader-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

### 3. Деплой
Render задеплоит и даст URL типа:
`https://youtube-downloader-api.onrender.com`

⚠️ **Важно:** Render засыпает через 15 минут без активности. Первый запрос после сна = 30-60 секунд ожидания.

---

## Проверка работы

### Тест 1: Проверка API
```bash
curl https://your-app.up.railway.app/
```

### Тест 2: Получение информации о видео
```bash
curl -X POST https://your-app.up.railway.app/info \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

### Тест 3: Начать скачивание
```bash
curl -X POST https://your-app.up.railway.app/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","quality":"hd"}'
```

Вернёт `task_id`, затем проверь статус:
```bash
curl https://your-app.up.railway.app/status/TASK_ID
```

---

## Мониторинг

### Railway Dashboard
1. Зайди на https://railway.app/dashboard
2. Выбери свой проект
3. Смотри:
   - **Deployments** - история деплоев
   - **Metrics** - использование ресурсов
   - **Logs** - логи приложения

### Проверка квоты
Railway показывает использованные часы в dashboard.

---

## Обновление backend

### Способ 1: Через Git
```bash
cd backend-ytdlp
# Внеси изменения в код
git add .
git commit -m "Update"
git push
```

Railway автоматически задеплоит новую версию!

### Способ 2: Через Railway Dashboard
1. Зайди в проект
2. Нажми "Deployments"
3. Нажми "Redeploy"

---

## Troubleshooting

### Ошибка "Build failed"
- Проверь `requirements.txt` на опечатки
- Проверь `Procfile` и `railway.json`

### Ошибка "Application failed to respond"
- Проверь логи в Railway Dashboard
- Убедись что `gunicorn app:app` правильный

### Ошибка "CORS"
- Убедись что в `app.py` есть `CORS(app)`
- Проверь что frontend делает запросы на правильный URL

### Backend медленно работает
- Railway: нормально, сервер просыпается
- Render: первый запрос после сна = 30-60 сек

---

## Стоимость

### Railway (рекомендуется)
- ✅ 500 часов бесплатно в месяц
- ✅ Хватит на 10,000+ скачиваний
- ✅ Нет холодного старта

### Render
- ✅ Неограниченное время
- ⚠️ Холодный старт 30-60 сек
- ✅ Полностью бесплатно

---

## Готово! 🎉

Теперь у тебя:
- ✅ Свой бесплатный backend
- ✅ Неограниченные скачивания
- ✅ Никаких API ключей
- ✅ Полный контроль

Удачи! 🚀
