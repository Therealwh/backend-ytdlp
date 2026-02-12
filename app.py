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
        
        # Настройки yt-dlp с обходом защиты YouTube
        # Скачиваем файл во временную директорию
        temp_dir = tempfile.gettempdir()
        output_template = os.path.join(temp_dir, f'{task_id}.%(ext)s')
        
        ydl_opts = {
            'format': get_format_string(quality),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'nocheckcertificate': True,
            'outtmpl': output_template,
            # Пробуем разные методы обхода
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'android', 'ios', 'web'],
                    'skip': ['hls', 'dash'],
                }
            },
            # Добавляем заголовки
            'http_headers': {
                'User-Agent': 'com.google.android.apps.youtube.creator/23.50.100 (Linux; U; Android 13)',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию и скачиваем
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise Exception("Не удалось получить информацию о видео")
            
            # Находим скачанный файл
            downloaded_file = None
            for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                potential_file = os.path.join(temp_dir, f'{task_id}.{ext}')
                if os.path.exists(potential_file):
                    downloaded_file = potential_file
                    break
            
            if not downloaded_file:
                raise Exception("Файл не был скачан")
            
            print(f"Task {task_id}: Downloaded to {downloaded_file}")
            
            # Обновляем задачу
            tasks[task_id].update({
                'status': 'completed',
                'file_path': downloaded_file,
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
        # Используем форматы которые не требуют склейки
        'best': 'best[ext=mp4]/best',
        'fhd': 'best[height<=1080][ext=mp4]/best[height<=1080]',
        'hd': 'best[height<=720][ext=mp4]/best[height<=720]',
        'audio': 'bestaudio[ext=m4a]/bestaudio',
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
    """Скачать файл"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        print(f"Download request for task: {task_id}")
        task = tasks.get(task_id)
        
        if not task:
            print(f"Task not found: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        if task['status'] != 'completed':
            print(f"Task not completed: {task['status']}")
            return jsonify({'error': 'Task not completed yet'}), 400
        
        file_path = task.get('file_path')
        if not file_path or not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        # Создаем безопасное имя файла
        safe_title = "video"
        try:
            safe_title = "".join(c for c in task['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = "video"
        except:
            safe_title = "video"
        
        # Определяем расширение
        ext = os.path.splitext(file_path)[1] or '.mp4'
        filename = f"{safe_title}{ext}"
        
        print(f"Sending file: {file_path} as {filename}")
        
        # Отправляем файл и удаляем после отправки
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
        # Удаляем файл после отправки
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Cleaned up file: {file_path}")
            except Exception as e:
                print(f"Error cleaning up file: {str(e)}")
        
        return response
        
    except Exception as e:
        print(f"Error in get_download: {str(e)}")
        import traceback
        traceback.print_exc()
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
            'nocheckcertificate': True,
            # Пробуем разные методы обхода
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'android', 'ios', 'web'],
                    'skip': ['hls', 'dash'],
                }
            },
            # Добавляем заголовки
            'http_headers': {
                'User-Agent': 'com.google.android.apps.youtube.creator/23.50.100 (Linux; U; Android 13)',
                'Accept-Language': 'en-US,en;q=0.9',
            }
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
