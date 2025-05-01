#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import threading
import requests
from typing import Callable, Dict, Any, Optional

class UVDetectorIntegration:
    """
    Модуль интеграции GUI с симулятором УФ пеленгатора.
    Обеспечивает API для управления устройством и мониторинг состояния.
    """
    
    def __init__(self, host="localhost", port=8080, status_callback=None):
        """
        Инициализация интеграционного модуля.
        
        Args:
            host (str): Хост симулятора (по умолчанию "localhost")
            port (int): Порт симулятора (по умолчанию 8080)
            status_callback (Callable): Функция обратного вызова для уведомления 
                                      о изменении статуса устройства
        """
        self.base_url = f"http://{host}:{port}/jsonrpc"
        self.request_id = 0
        self.status = "unknown"
        self.status_callback = status_callback
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        # Запускаем мониторинг состояния устройства
        self.start_status_monitoring()
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Отправка JSON-RPC запроса к симулятору.
        
        Args:
            method (str): Название метода JSON-RPC
            params (dict, optional): Параметры метода
            
        Returns:
            dict: JSON-ответ от симулятора
        """
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id
        }
        
        if params:
            payload["params"] = params
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=5)
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
    
    def _update_status(self, new_status: str):
        """
        Обновление внутреннего состояния и уведомление слушателей.
        
        Args:
            new_status (str): Новый статус устройства
        """
        if new_status != self.status:
            self.status = new_status
            if self.status_callback:
                self.status_callback(new_status)
    
    def start_status_monitoring(self, interval: float = 1.0):
        """
        Запуск фонового мониторинга статуса устройства.
        
        Args:
            interval (float): Интервал опроса в секундах
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._status_monitoring_worker,
            args=(interval,)
        )
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_status_monitoring(self):
        """
        Остановка фонового мониторинга статуса устройства.
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.stop_monitoring.set()
            self.monitoring_thread.join(timeout=2.0)
    
    def _status_monitoring_worker(self, interval: float):
        """
        Рабочий метод для фонового мониторинга статуса.
        
        Args:
            interval (float): Интервал опроса в секундах
        """
        while not self.stop_monitoring.is_set():
            # Получаем текущий статус устройства
            status = self.get_status()
            if status is not None:
                self._update_status(status)
                
            # Ждем до следующего опроса
            self.stop_monitoring.wait(interval)
    
    def get_status(self) -> Optional[str]:
        """
        Получение текущего статуса симулятора.
        
        Returns:
            str: Статус симулятора ("idle", "show", "record") или None в случае ошибки
        """
        response = self._send_request("VideoRpc.Status")
        if "result" in response:
            return response["result"]["res"]
        elif "error" in response:
            print(f"Ошибка получения статуса: {response['error']['message']}")
            return None
        else:
            print("Неизвестный формат ответа")
            return None
    
    def start_streaming(self) -> bool:
        """
        Запуск трансляции с устройства.
        
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        response = self._send_request("VideoRpc.Show")
        if "result" in response:
            self._update_status(response["result"]["res"])
            return response["result"]["res"] == "show"
        else:
            return False
    
    def stop(self) -> bool:
        """
        Остановка любой активности устройства.
        
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        response = self._send_request("VideoRpc.Stop")
        if "result" in response:
            self._update_status(response["result"]["res"])
            return response["result"]["res"] == "idle"
        else:
            return False
    
    def start_recording(self) -> bool:
        """
        Запуск записи с устройства.
        
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        response = self._send_request("VideoRpc.Record")
        if "result" in response:
            self._update_status(response["result"]["res"])
            return response["result"]["res"] == "record"
        else:
            return False
    
    def __del__(self):
        """
        Деструктор для корректного завершения фоновых потоков.
        """
        self.stop_status_monitoring()


# Пример использования модуля интеграции в GUI-приложении
if __name__ == "__main__":
    # Функция обратного вызова для обновления интерфейса
    def update_ui_status(status):
        print(f"[GUI] Обновление интерфейса: статус устройства = {status}")
    
    # Создаем экземпляр модуля интеграции
    integration = UVDetectorIntegration(status_callback=update_ui_status)
    
    # Пример имитации действий пользователя в GUI
    print("=== Демонстрация интеграции GUI с симулятором ===")
    
    print("\n[Пользователь] Нажимает кнопку 'Start Streaming'")
    if integration.start_streaming():
        print("[GUI] Трансляция запущена успешно")
    else:
        print("[GUI] Ошибка запуска трансляции")
    
    # Имитация просмотра трансляции
    time.sleep(3)
    
    print("\n[Пользователь] Нажимает кнопку 'Start Recording'")
    if integration.start_recording():
        print("[GUI] Запись запущена успешно")
    else:
        print("[GUI] Ошибка запуска записи")
    
    # Имитация записи
    time.sleep(3)
    
    print("\n[Пользователь] Нажимает кнопку 'Stop'")
    if integration.stop():
        print("[GUI] Устройство остановлено успешно")
    else:
        print("[GUI] Ошибка остановки устройства")
    
    # Останавливаем мониторинг перед выходом
    integration.stop_status_monitoring()
    print("\n=== Демонстрация завершена ===")
