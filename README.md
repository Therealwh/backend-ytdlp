# YouTube Downloader Backend (yt-dlp)

Бесплатный backend для скачивания YouTube видео с использованием yt-dlp.

## Возможности

- ✅ Скачивание YouTube видео в любом качестве
- ✅ Скачивание YouTube Shorts
- ✅ Извлечение аудио (MP3)
- ✅ Поддержка форматов: best, 1080p, 720p, audio
- ✅ Асинхронная обработка запросов
- ✅ CORS для работы с любым frontend
- ✅ Автоматическая очистка старых задач

## API Endpoints

### 1. GET `/`
Проверка работы API

**Response:**
```json
{
  "status": "ok",
  "message": "YouTube Downloader API with yt-dlp",
  "version": "1.0.0"
}
```

### 2. POST `/start`
Начать скачивание видео

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "quality": "best"
}
```

**Quality options:**
- `best` - лучшее качество
- `fhd` - 1080p
- `hd` - 720p
- `audio` - только аудио (MP3)

**Response:**
```json
{
  "task_id": "uuid-here",
  "status": "pending"
}
```

### 3. GET `/status/<task_id>`
Проверить статус задачи

**Response:**
```json
{
  "status": "processing",
  "url": "...",
  "quality": "best"
}
```

**Status values:**
- `pending` - в очереди
- `processing` - обрабатывается
- `completed` - готово
- `failed` - ошибка

### 4. GET `/download/<task_id>`
Получить ссылку на скачивание

**Response:**
```json
{
  "download_url": "https://...",
  "title": "Video Title",
  "thumbnail": "https://...",
  "duration": 180,
  "view_count": 1000000,
  "channel": "Channel Name"
}
```

### 5. POST `/info`
Получить информацию о видео без скачивания

**Request:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "title": "Video Title",
  "thumbnail": "https://...",
  "duration": 180,
  "view_count": 1000000,
  "channel": "Channel Name",
  "formats": [
    {"quality": "1080p", "height": 1080, "ext": "mp4"},
    {"quality": "720p", "height": 720, "ext": "mp4"}
  ]
}
```

## Деплой на Railway

### Шаг 1: Создать аккаунт
1. Зайди на https://railway.app
2. Зарегистрируйся через GitHub

### Шаг 2: Создать новый проект
1. Нажми "New Project"
2. Выбери "Deploy from GitHub repo"
3. Выбери репозиторий с этим кодом
4. Railway автоматически определит Python и установит зависимости

### Шаг 3: Настроить переменные окружения
В Railway добавь переменную:
- `PORT` = `5000` (обычно не нужно, Railway сам установит)

### Шаг 4: Деплой
Railway автоматически задеплоит приложение и даст тебе URL типа:
`https://your-app.railway.app`

## Деплой на Render

### Шаг 1: Создать аккаунт
1. Зайди на https://render.com
2. Зарегистрируйся через GitHub

### Шаг 2: Создать Web Service
1. Нажми "New +" → "Web Service"
2. Подключи GitHub репозиторий
3. Настройки:
   - **Name**: youtube-downloader-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

### Шаг 3: Деплой
Render автоматически задеплоит и даст URL типа:
`https://youtube-downloader-api.onrender.com`

## Локальный запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
python app.py
```

Сервер запустится на `http://localhost:5000`

## Тестирование

```bash
# Проверка работы
curl http://localhost:5000/

# Начать скачивание
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","quality":"hd"}'

# Проверить статус
curl http://localhost:5000/status/TASK_ID

# Получить ссылку
curl http://localhost:5000/download/TASK_ID
```

## Ограничения

- Задачи хранятся в памяти (при перезапуске сервера теряются)
- Старые задачи (>1 часа) автоматически удаляются
- Нет rate limiting (можно добавить при необходимости)

## Обновление yt-dlp

yt-dlp регулярно обновляется для поддержки изменений YouTube.

Обновить версию в `requirements.txt`:
```
yt-dlp==latest
```

Или установить последнюю версию:
```bash
pip install --upgrade yt-dlp
```

## Troubleshooting

### Ошибка "Unable to extract video data"
- YouTube изменил API, нужно обновить yt-dlp
- Видео недоступно или удалено
- Видео имеет возрастные ограничения

### Ошибка "HTTP Error 403"
- YouTube заблокировал IP сервера
- Попробуй использовать VPN или другой хостинг

### Медленная работа
- Используй качество `hd` вместо `best`
- Проверь скорость интернета на сервере

## Безопасность

- ✅ CORS настроен для работы с любым доменом
- ✅ Нет хранения файлов на сервере
- ✅ Автоматическая очистка старых задач
- ⚠️ Нет rate limiting (добавь при необходимости)
- ⚠️ Нет аутентификации (добавь при необходимости)

## Лицензия

MIT License - используй свободно!
