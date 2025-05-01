#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import cv2
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Event

class VideoRpc:
    """
    Класс для обработки JSON-RPC запросов, имитирующий работу УФ пеленгатора.
    """
    
    def __init__(self):
        self.status = "idle"  # Начальное состояние: ожидание (idle)
        self.stream_thread = None
        self.stop_event = Event()
        self.frame_counter = 0
        self.last_frame = None
        self.recording_frames = []
    
    def Status(self, params=None):
        """Возвращает текущий статус устройства"""
        return {"res": self.status}
    
    def Show(self, params=None):
        """Переключает устройство в режим трансляции"""
        if self.status != "idle" and self.stream_thread and self.stream_thread.is_alive():
            self.stop_event.set()
            self.stream_thread.join()
            
        self.status = "show"
        self.stop_event.clear()
        self.stream_thread = Thread(target=self._stream_video)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        return {"res": self.status}
    
    def Stop(self, params=None):
        """Останавливает активность устройства"""
        if self.stream_thread and self.stream_thread.is_alive():
            self.stop_event.set()
            self.stream_thread.join()
            
        self.status = "idle"
        if self.recording_frames:
            print(f"Запись остановлена. Записано {len(self.recording_frames)} кадров.")
            self.recording_frames = []
            
        return {"res": self.status}
    
    def Record(self, params=None):
        """Переключает устройство в режим записи"""
        if self.status != "idle" and self.stream_thread and self.stream_thread.is_alive():
            self.stop_event.set()
            self.stream_thread.join()
            
        self.status = "record"
        self.recording_frames = []
        self.stop_event.clear()
        self.stream_thread = Thread(target=self._record_video)
        self.stream_thread.daemon = True
        self.stream_thread.start()
        return {"res": self.status}
    
    def _generate_uv_frame(self, width=640, height=480):
        """Генерирует фрейм с имитацией УФ-изображения"""
        # Создаем черное изображение
        frame = np.zeros((height, width, 3), np.uint8)
        
        # Добавляем синие точки, имитирующие УФ-излучение
        if self.frame_counter % 10 == 0:  # Регулярно изменяем расположение точек
            self.points = []
            for _ in range(np.random.randint(5, 15)):
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                radius = np.random.randint(2, 8)
                intensity = np.random.randint(100, 255)
                self.points.append((x, y, radius, intensity))
                
        # Рисуем точки УФ-излучения
        for x, y, radius, intensity in self.points:
            # Перемещаем точки для эффекта мерцания
            x_offset = np.random.randint(-3, 4)
            y_offset = np.random.randint(-3, 4)
            
            # Ограничиваем координаты, чтобы не выйти за границы
            x = max(radius, min(width - radius, x + x_offset))
            y = max(radius, min(height - radius, y + y_offset))
            
            # Рисуем градиентный круг (УФ-коронный разряд)
            for r in range(radius, 0, -1):
                fade = intensity * (r / radius)
                cv2.circle(frame, (x, y), r, (fade, 0, 0), 1)
            
        # Добавляем информацию о режиме и счетчике кадров
        text = f"Mode: {self.status.upper()} | Frame: {self.frame_counter}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Добавляем дату и время
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cv2.putText(frame, timestamp, (width - 220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        self.frame_counter += 1
        self.last_frame = frame
        return frame
    
    def _stream_video(self):
        """Имитация потоковой трансляции"""
        print("Режим трансляции запущен")
        while not self.stop_event.is_set():
            frame = self._generate_uv_frame()
            # В реальном приложении здесь мог бы быть код для трансляции видео
            time.sleep(0.1)  # Имитация задержки между кадрами
        print("Режим трансляции остановлен")
    
    def _record_video(self):
        """Имитация записи видео"""
        print("Режим записи запущен")
        while not self.stop_event.is_set():
            frame = self._generate_uv_frame()
            self.recording_frames.append(frame.copy())
            # В реальном приложении здесь мог бы быть код для сохранения видео
            time.sleep(0.1)  # Имитация задержки между кадрами
        print("Режим записи остановлен")

class JsonRpcServer(BaseHTTPRequestHandler):
    """
    HTTP сервер, обрабатывающий JSON-RPC запросы и отправляющий ответы.
    """
    
    rpc_methods = {
        "VideoRpc.Status": VideoRpc.Status,
        "VideoRpc.Show": VideoRpc.Show,
        "VideoRpc.Stop": VideoRpc.Stop,
        "VideoRpc.Record": VideoRpc.Record
    }
    
    video_rpc = VideoRpc()
    
    def do_POST(self):
        """Обработка POST-запросов с JSON-RPC"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            json_data = json.loads(post_data.decode('utf-8'))
            method = json_data.get("method")
            params = json_data.get("params")
            id = json_data.get("id")
            
            if method in self.rpc_methods:
                # Вызываем соответствующий метод
                result = self.rpc_methods[method](self.video_rpc, params)
                # Формируем успешный ответ
                response = {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": id
                }
            else:
                # Ошибка метода не найден
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method '{method}' not found"
                    },
                    "id": id
                }
                
            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS для API
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except json.JSONDecodeError:
            # Ошибка разбора JSON
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
        except Exception as e:
            # Другие ошибки
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": None
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Обработка предварительных запросов CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=8080):
    """Запуск HTTP сервера на указанном порту"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, JsonRpcServer)
    print(f"Запуск JSON-RPC сервера на порту {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
