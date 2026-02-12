from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import os
import uuid
import time
import requests
from threading import Thread

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "expose_headers": ["Content-Disposition", "Content-Length"]
    }
})  # Разрешаем запросы с любых доменов

# Хранилище задач в памяти
tasks = {}

def download_video(task_id, url, quality):
    """Фоновая задача для скачивания видео"""
    try:
        tasks[task_id]['status'] = 'processing'
        
        # Настройки yt-dlp
        ydl_opts = {
            'format': get_format_string(quality),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            
            # Получаем прямую ссылку на скачивание
            if 'url' in info:
                download_url = info['url']
            elif 'formats' in info:
                # Выбираем лучший формат
                formats = info['formats']
                best_format = formats[-1]
                download_url = best_format['url']
            else:
                raise Exception("Не удалось получить ссылку на скачивание")
            
            # Обновляем задачу
            tasks[task_id].update({
                'status': 'completed',
                'download_url': download_url,
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'channel': info.get('uploader', 'Unknown'),
            })
            
    except Exception as e:
        tasks[task_id].update({
            'status': 'failed',
            'error': str(e)
        })

def get_format_string(quality):
    """Преобразует качество в формат yt-dlp"""
    quality_map = {
        'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'fhd': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'hd': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
        'audio': 'bestaudio[ext=m4a]/bestaudio/best',
    }
    return quality_map.get(quality, quality_map['best'])

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'YouTube Downloader API with yt-dlp',
        'version': '1.0.0'
    })

@app.route('/start', methods=['POST'])
def start_download():
    """Начать скачивание видео"""
    try:
        data = request.json
        url = data.get('url')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Создаём уникальный ID задачи
        task_id = str(uuid.uuid4())
        
        # Создаём задачу
        tasks[task_id] = {
            'status': 'pending',
            'url': url,
            'quality': quality,
            'created_at': time.time()
        }
        
        # Запускаем фоновую задачу
        thread = Thread(target=download_video, args=(task_id, url, quality))
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'pending'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Получить статус задачи"""
    task = tasks.get(task_id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(task)

@app.route('/download/<task_id>', methods=['GET'])
def get_download(task_id):
    """Получить ссылку на скачивание или проксировать файл"""
    task = tasks.get(task_id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task['status'] != 'completed':
        return jsonify({'error': 'Task not completed yet'}), 400
    
    # Проверяем параметр proxy
    if request.args.get('proxy') == 'true':
        # Проксируем файл через наш сервер
        try:
            download_url = task['download_url']
            
            # Делаем запрос к YouTube
            response = requests.get(download_url, stream=True, timeout=30)
            
            # Определяем имя файла
            filename = f"{task['title']}.mp4".replace('/', '_').replace('\\', '_')
            
            # Возвращаем файл с правильными заголовками
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return Response(
                stream_with_context(generate()),
                content_type=response.headers.get('content-type', 'video/mp4'),
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': response.headers.get('content-length', ''),
                }
            )
        except Exception as e:
            return jsonify({'error': f'Proxy failed: {str(e)}'}), 500
    
    # Возвращаем просто ссылку
    return jsonify({
        'download_url': task['download_url'],
        'title': task['title'],
        'thumbnail': task['thumbnail'],
        'duration': task['duration'],
        'view_count': task['view_count'],
        'channel': task['channel'],
    })

@app.route('/info', methods=['POST'])
def get_video_info():
    """Получить информацию о видео без скачивания"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Получаем доступные форматы
            formats = []
            if 'formats' in info:
                seen_heights = set()
                for f in info['formats']:
                    if f.get('height') and f['height'] not in seen_heights:
                        formats.append({
                            'quality': f'{f["height"]}p',
                            'height': f['height'],
                            'ext': f.get('ext', 'mp4')
                        })
                        seen_heights.add(f['height'])
            
            return jsonify({
                'title': info.get('title', 'Unknown'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'channel': info.get('uploader', 'Unknown'),
                'formats': sorted(formats, key=lambda x: x['height'], reverse=True)
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Очистка старых задач (старше 1 часа)
def cleanup_old_tasks():
    current_time = time.time()
    to_delete = []
    for task_id, task in tasks.items():
        if current_time - task.get('created_at', 0) > 3600:  # 1 час
            to_delete.append(task_id)
    
    for task_id in to_delete:
        del tasks[task_id]

@app.before_request
def before_request():
    cleanup_old_tasks()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
