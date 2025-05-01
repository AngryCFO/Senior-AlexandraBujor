#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import subprocess
import requests
import argparse
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

# Настройки по умолчанию
DEFAULT_SIMULATOR_PORT = 8080
DEFAULT_WEB_PORT = 3000
DEFAULT_HOST = "localhost"

def get_web_interface_html():
    """Возвращает HTML-код веб-интерфейса"""
    # Используем содержимое из complete-web-interface.html
    with open('complete-web-interface.html', 'r', encoding='utf-8') as f:
        return f.read()

class UVTesterConfig:
    """Конфигурация для тестирования системы УФ пеленгатора"""
    def __init__(self, sim_port=DEFAULT_SIMULATOR_PORT, web_port=DEFAULT_WEB_PORT, host=DEFAULT_HOST):
        self.simulator_port = sim_port
        self.web_port = web_port
        self.host = host
        self.simulator_url = f"http://{host}:{sim_port}/jsonrpc"
        self.web_url = f"http://{host}:{web_port}"
        
        # Пути к файлам
        self.script_dir = Path(__file__).parent.absolute()
        self.web_interface_path = self.script_dir / "web_interface.html"
        self.simulator_path = self.script_dir / "simulator.py"
        
        # Проверка наличия файлов
        if not self.web_interface_path.exists():
            with open(self.web_interface_path, "w", encoding="utf-8") as f:
                f.write(get_web_interface_html())
            print(f"Создан файл веб-интерфейса: {self.web_interface_path}")
        
        if not self.simulator_path.exists():
            raise FileNotFoundError(f"Файл симулятора не найден: {self.simulator_path}")

class SimpleHTTPRequestHandlerWithCORS(http.server.SimpleHTTPRequestHandler):
    """HTTP-обработчик с поддержкой CORS для статических файлов"""
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        http.server.SimpleHTTPRequestHandler.end_headers(self)
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

class SimulatorProcess:
    """Управление процессом симулятора"""
    def __init__(self, config):
        self.config = config
        self.process = None
        
    def start(self):
        """Запуск симулятора"""
        if self.process and self.process.poll() is None:
            print("Симулятор уже запущен")
            return
            
        print(f"Запуск симулятора на порту {self.config.simulator_port}...")
        self.process = subprocess.Popen(
            [sys.executable, str(self.config.simulator_path), str(self.config.simulator_port)],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Проверка, что симулятор запустился
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(0.5)
            try:
                response = requests.post(
                    self.config.simulator_url,
                    json={"jsonrpc": "2.0", "method": "VideoRpc.Status", "id": 1},
                    timeout=1
                )
                if response.status_code == 200:
                    print(f"Симулятор успешно запущен (попытка {attempt+1}/{max_attempts})")
                    return True
            except requests.exceptions.RequestException:
                if attempt == max_attempts - 1:
                    print(f"Не удалось подключиться к симулятору после {max_attempts} попыток")
                    return False
                continue
        
        return False
    
    def stop(self):
        """Остановка симулятора"""
        if self.process:
            print("Остановка симулятора...")
            self.process.terminate()
            stdout, stderr = self.process.communicate(timeout=5)
            print("Вывод симулятора:")
            print(stdout.decode("utf-8"))
            if stderr:
                print("Ошибки симулятора:")
                print(stderr.decode("utf-8"))
            self.process = None

class WebServer:
    """Веб-сервер для обслуживания интерфейса"""
    def __init__(self, config):
        self.config = config
        self.server = None
        self.thread = None
        
    def start(self):
        """Запуск веб-сервера"""
        if self.thread and self.thread.is_alive():
            print("Веб-сервер уже запущен")
            return
            
        # Устанавливаем текущий каталог на директорию скрипта
        os.chdir(self.config.script_dir)
        
        # Создаем и запускаем сервер в отдельном потоке
        handler = SimpleHTTPRequestHandlerWithCORS
        self.server = socketserver.TCPServer(("", self.config.web_port), handler)
        
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"Веб-сервер запущен на порту {self.config.web_port}")
        print(f"Веб-интерфейс доступен по адресу: {self.config.web_url}")
        
    def stop(self):
        """Остановка веб-сервера"""
        if self.server:
            print("Остановка веб-сервера...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.thread = None

class UVDetectorClient:
    """Клиент для взаимодействия с симулятором УФ пеленгатора"""
    def __init__(self, config):
        self.config = config
        self.request_id = 0
    
    def _send_request(self, method, params=None):
        """Отправка JSON-RPC запроса к симулятору"""
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id
        }
        
        if params:
            payload["params"] = params
        
        try:
            response = requests.post(self.config.simulator_url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": {
                        "code": response.status_code,
                        "message": f"HTTP Error: {response.text}"
                    }
                }
        except requests.exceptions.RequestException as e:
            return {
                "error": {
                    "code": -1,
                    "message": f"Connection error: {str(e)}"
                }
            }
    
    def get_status(self):
        """Получение текущего статуса симулятора"""
        response = self._send_request("VideoRpc.Status")
        if "result" in response:
            return response["result"]["res"]
        return None
    
    def start_streaming(self):
        """Запуск трансляции"""
        response = self._send_request("VideoRpc.Show")
        if "result" in response:
            return response["result"]["res"] == "show"
        return False
    
    def stop(self):
        """Остановка активности"""
        response = self._send_request("VideoRpc.Stop")
        if "result" in response:
            return response["result"]["res"] == "idle"
        return False
    
    def start_recording(self):
        """Запуск записи"""
        response = self._send_request("VideoRpc.Record")
        if "result" in response:
            return response["result"]["res"] == "record"
        return False

def main():
    """Основная функция для запуска тестовой системы"""
    parser = argparse.ArgumentParser(description="Тестовая система УФ пеленгатора")
    parser.add_argument("--sim-port", type=int, default=DEFAULT_SIMULATOR_PORT,
                       help=f"Порт симулятора (по умолчанию: {DEFAULT_SIMULATOR_PORT})")
    parser.add_argument("--web-port", type=int, default=DEFAULT_WEB_PORT,
                       help=f"Порт веб-интерфейса (по умолчанию: {DEFAULT_WEB_PORT})")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST,
                       help=f"Хост (по умолчанию: {DEFAULT_HOST})")
    parser.add_argument("--no-browser", action="store_true",
                       help="Не открывать браузер автоматически")
    
    args = parser.parse_args()
    
    try:
        # Инициализация конфигурации
        config = UVTesterConfig(
            sim_port=args.sim_port,
            web_port=args.web_port,
            host=args.host
        )
        
        # Запуск симулятора
        simulator = SimulatorProcess(config)
        if not simulator.start():
            print("Ошибка запуска симулятора. Завершение работы.")
            return 1
        
        # Запуск веб-сервера
        web_server = WebServer(config)
        web_server.start()
        
        # Создание клиента для тестирования
        client = UVDetectorClient(config)
        
        # Открытие браузера
        if not args.no_browser:
            webbrowser.open(config.web_url)
        
        print("\nТестовая система запущена. Нажмите Ctrl+C для остановки.")
        
        # Основной цикл работы
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nПолучен сигнал остановки. Завершение работы...")
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return 1
    finally:
        # Остановка сервисов
        if 'simulator' in locals():
            simulator.stop()
        if 'web_server' in locals():
            web_server.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())