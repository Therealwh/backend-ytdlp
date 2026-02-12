from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import time
import requests
from threading import Thread
import tempfile

app = Flask(__name__)

# Настройка CORS для всех endpoints
CORS(app, 
     origins="*",
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Disposition", "Content-Length"],
     supports_credentials=False)

# Хранилище задач в памяти
tasks = {}

def download_video(task_id, url, quality):
    """Фоновая задача для скачивания видео"""
    try:
        tasks[task_id]['status'] = 'processing'
        
        # Настройки yt-dlp с дополнительными опциями
        ydl_opts = {
            'format': get_format_string(quality),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о видео
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise Exception("Не удалось получить информацию о видео")
            
            # Получаем прямую ссылку на скачивание
            download_url = None
            
            # Пробуем разные способы получить URL
            if 'url' in info:
                download_url = info['url']
            elif 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                download_url = info['requested_downloads'][0].get('url')
            elif 'formats' in info and len(info['formats']) > 0:
                # Ищем формат с URL
                for fmt in reversed(info['formats']):
                    if fmt.get('url'):
                        download_url = fmt['url']
                        break
            
            if not download_url:
                raise Exception("Не удалось получить ссылку на скачивание")
            
            print(f"Task {task_id}: Got download URL")
            
            # Обновляем задачу
            tasks[task_id].update({
                'status': 'completed',
                'download_url': download_url,
                'title': info.get('title', 'video'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'channel': info.get('uploader', 'Unknown'),
            })
            
            print(f"Task {task_id}: Completed successfully")
            
    except Exception as e:
        error_msg = str(e)
        print(f"Task {task_id}: Error - {error_msg}")
        tasks[task_id].update({
            'status': 'failed',
            'error': error_msg
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

@app.after_request
def after_request(response):
    """Добавляем CORS заголовки ко всем ответам"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Disposition,Content-Length')
    return response

@app.route('/')
def home():
    return jsonify({
        'status': 'ok',
        'message': 'YouTube Downloader API with yt-dlp',
        'version': '1.0.0'
    })

@app.route('/start', methods=['POST', 'OPTIONS'])
def start_download():
    """Начать скачивание видео"""
    if request.method == 'OPTIONS':
        return '', 204
        
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
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'pending'
        })
        
    except Exception as e:
        print(f"Error in start_download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>', methods=['GET', 'OPTIONS'])
def get_status(task_id):
    """Получить статус задачи"""
    if request.method == 'OPTIONS':
        return '', 204
        
    task = tasks.get(task_id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(task)

@app.route('/download/<task_id>', methods=['GET', 'OPTIONS'])
def get_download(task_id):
    """Проксировать скачивание файла"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        task = tasks.get(task_id)
        
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        if task['status'] != 'completed':
            return jsonify({'error': 'Task not completed yet'}), 400
        
        download_url = task['download_url']
        title = task['title']
        
        # Проксируем файл
        print(f"Proxying download from: {download_url}")
        
        # Делаем запрос к YouTube с таймаутом
        try:
            response = requests.get(download_url, stream=True, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code != 200:
                print(f"YouTube returned status: {response.status_code}")
                return jsonify({'error': f'Failed to fetch video: {response.status_code}'}), 500
            
            print(f"Successfully connected to YouTube, streaming file...")
            
            # Простое ASCII имя файла
            import re
            safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '', title)[:50]  # Только безопасные символы
            if not safe_title:
                safe_title = 'video'
            filename = f"{safe_title}.mp4"
            
            print(f"Filename: {filename}")
            
            # Возвращаем файл с минимальными заголовками
            def generate():
                try:
                    bytes_sent = 0
                    chunk_size = 65536  # 64KB chunks для лучшей производительности
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            bytes_sent += len(chunk)
                            if bytes_sent % (chunk_size * 10) == 0:  # Логируем каждые 640KB
                                print(f"Streamed: {bytes_sent / 1024 / 1024:.2f} MB")
                            yield chunk
                    print(f"Streaming completed: {bytes_sent / 1024 / 1024:.2f} MB sent")
                except GeneratorExit:
                    print("Client disconnected during streaming")
                    raise
                except Exception as e:
                    print(f"Error during streaming: {str(e)}")
                    raise
            
            return Response(
                stream_with_context(generate()),
                content_type='video/mp4',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'no-cache',
                }
            )
            
        except requests.exceptions.Timeout:
            print("Request to YouTube timed out")
            return jsonify({'error': 'Request timed out'}), 504
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            return jsonify({'error': f'Request failed: {str(e)}'}), 500
        
    except Exception as e:
        print(f"Error in get_download: {str(e)}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/info', methods=['POST', 'OPTIONS'])
def get_video_info():
    """Получить информацию о видео без скачивания"""
    if request.method == 'OPTIONS':
        return '', 204
        
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
        print(f"Error in get_video_info: {str(e)}")
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
    app.run(host='0.0.0.0', port=port, debug=False)
