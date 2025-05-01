#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
import requests

class UVDetectorClient:
    """
    Клиент для взаимодействия с симулятором УФ пеленгатора через JSON-RPC API.
    """
    
    def __init__(self, host="localhost", port=8080):
        """
        Инициализация клиента с указанием хоста и порта симулятора.
        
        Args:
            host (str): Хост симулятора (по умолчанию "localhost")
            port (int): Порт симулятора (по умолчанию 8080)
        """
        self.base_url = f"http://{host}:{port}/jsonrpc"
        self.request_id = 0
    
    def _send_request(self, method, params=None):
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
            response = requests.post(self.base_url, json=payload)
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
        """
        Получение текущего статуса симулятора.
        
        Returns:
            str: Статус симулятора ("idle", "show", "record")
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
    
    def start_streaming(self):
        """
        Запуск трансляции.
        
        Returns:
            str: Новый статус симулятора
        """
        response = self._send_request("VideoRpc.Show")
        if "result" in response:
            return response["result"]["res"]
        elif "error" in response:
            print(f"Ошибка запуска трансляции: {response['error']['message']}")
            return None
        else:
            print("Неизвестный формат ответа")
            return None
    
    def stop(self):
        """
        Остановка любой активности (трансляция или запись).
        
        Returns:
            str: Новый статус симулятора
        """
        response = self._send_request("VideoRpc.Stop")
        if "result" in response:
            return response["result"]["res"]
        elif "error" in response:
            print(f"Ошибка остановки: {response['error']['message']}")
            return None
        else:
            print("Неизвестный формат ответа")
            return None
    
    def start_recording(self):
        """
        Запуск записи.
        
        Returns:
            str: Новый статус симулятора
        """
        response = self._send_request("VideoRpc.Record")
        if "result" in response:
            return response["result"]["res"]
        elif "error" in response:
            print(f"Ошибка запуска записи: {response['error']['message']}")
            return None
        else:
            print("Неизвестный формат ответа")
            return None

def main():
    """
    Демонстрация использования клиента для взаимодействия с симулятором УФ пеленгатора.
    """
    client = UVDetectorClient()
    
    print("=== Тестирование клиента для УФ пеленгатора ===")
    
    # Получаем начальный статус
    status = client.get_status()
    print(f"Текущий статус: {status}")
    
    # Запускаем трансляцию
    print("\nЗапуск трансляции...")
    status = client.start_streaming()
    print(f"Статус после запуска трансляции: {status}")
    
    # Ждем некоторое время для демонстрации трансляции
    time.sleep(3)
    
    # Останавливаем трансляцию
    print("\nОстановка трансляции...")
    status = client.stop()
    print(f"Статус после остановки трансляции: {status}")
    
    # Запускаем запись
    print("\nЗапуск записи...")
    status = client.start_recording()
    print(f"Статус после запуска записи: {status}")
    
    # Ждем некоторое время для записи
    time.sleep(3)
    
    # Останавливаем запись
    print("\nОстановка записи...")
    status = client.stop()
    print(f"Статус после остановки записи: {status}")
    
    print("\n=== Тестирование завершено ===")

if __name__ == "__main__":
    main()