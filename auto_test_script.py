#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import requests
import subprocess
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class UVDetectorSimulatorTest(unittest.TestCase):
    """
    Класс автоматизированного тестирования взаимодействия GUI УФ пеленгатора с симулятором устройства.
    Используется Selenium для автоматизации взаимодействия с пользовательским интерфейсом.
    """
    
    SIMULATOR_URL = "http://localhost:8080/jsonrpc"
    GUI_URL = "http://localhost:3000"  # Предполагаемый URL веб-интерфейса
    
    @classmethod
    def setUpClass(cls):
        """Запуск симулятора и GUI перед тестами"""
        # Запускаем симулятор в отдельном процессе
        cls.simulator_process = subprocess.Popen(["python", "simulator.py"], 
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
        print("Запуск симулятора устройства...")
        time.sleep(2)  # Даем время для запуска сервера
        
        # Проверяем, что симулятор запустился
        try:
            response = requests.post(
                cls.SIMULATOR_URL,
                json={"jsonrpc": "2.0", "method": "VideoRpc.Status", "id": 1}
            )
            if response.status_code != 200:
                raise Exception(f"Симулятор не запустился. Код ответа: {response.status_code}")
            print(f"Симулятор успешно запущен. Статус: {response.json()}")
        except Exception as e:
            print(f"Ошибка при проверке запуска симулятора: {e}")
            cls.tearDownClass()
            raise
            
        # Инициализация WebDriver для автоматизации браузера
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Запуск в фоновом режиме без UI
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        cls.driver = webdriver.Chrome(options=options)
        
        # Запуск GUI (в реальном сценарии)
        # cls.gui_process = subprocess.Popen(["npm", "start"], 
        #                                  cwd="./gui_app",
        #                                  stdout=subprocess.PIPE,
        #                                  stderr=subprocess.PIPE)
        # print("Запуск GUI...")
        # time.sleep(5)  # Даем время для запуска интерфейса
        
        # Для тестирования считаем, что GUI уже запущен на порту 3000
        print("Подключение к GUI интерфейсу...")
        
    @classmethod
    def tearDownClass(cls):
        """Остановка симулятора и GUI после тестов"""
        print("Завершение работы тестового окружения...")
        if hasattr(cls, 'driver'):
            cls.driver.quit()
        
        if hasattr(cls, 'simulator_process'):
            cls.simulator_process.terminate()
            stdout, stderr = cls.simulator_process.communicate()
            print(f"Вывод симулятора:\n{stdout.decode('utf-8')}")
            if stderr:
                print(f"Ошибки симулятора:\n{stderr.decode('utf-8')}")
                
        # if hasattr(cls, 'gui_process'):
        #     cls.gui_process.terminate()
        #     cls.gui_process.communicate()
    
    def send_jsonrpc_request(self, method, params=None):
        """Отправка JSON-RPC запроса к симулятору"""
        payload = {
            "jsonrpc": "2.0", 
            "method": method, 
            "id": int(time.time())
        }
        if params:
            payload["params"] = params
            
        response = requests.post(self.SIMULATOR_URL, json=payload)
        return response.json()
    
    def get_simulator_status(self):
        """Получение текущего статуса симулятора"""
        response = self.send_jsonrpc_request("VideoRpc.Status")
        return response.get("result", {}).get("res", "unknown")
    
    def test_01_simulator_default_state(self):
        """Тест 1: Проверка начального состояния симулятора"""
        print("\nТест 1: Проверка начального состояния симулятора")
        status = self.get_simulator_status()
        self.assertEqual(status, "idle", f"Начальное состояние симулятора должно быть 'idle', получено '{status}'")
        print(f"✓ Начальное состояние симулятора: {status}")
    
    def test_02_start_streaming(self):
        """Тест 2: Запуск трансляции и проверка состояния"""
        print("\nТест 2: Запуск трансляции")
        
        # Отправляем команду на запуск трансляции
        response = self.send_jsonrpc_request("VideoRpc.Show")
        self.assertIn("result", response, f"Ответ не содержит поле 'result': {response}")
        self.assertEqual(response["result"]["res"], "show", f"Ожидалось состояние 'show', получено '{response['result']['res']}'")
        
        # Проверяем статус после запуска
        status = self.get_simulator_status()
        self.assertEqual(status, "show", f"Статус симулятора должен быть 'show', получено '{status}'")
        print(f"✓ Состояние после запуска трансляции: {status}")
        
        # Делаем паузу для эмуляции просмотра трансляции
        time.sleep(2)
    
    def test_03_stop_streaming(self):
        """Тест 3: Остановка трансляции и проверка состояния"""
        print("\nТест 3: Остановка трансляции")
        
        # Отправляем команду на остановку трансляции
        response = self.send_jsonrpc_request("VideoRpc.Stop")
        self.assertIn("result", response, f"Ответ не содержит поле 'result': {response}")
        self.assertEqual(response["result"]["res"], "idle", f"Ожидалось состояние 'idle', получено '{response['result']['res']}'")
        
        # Проверяем статус после остановки
        status = self.get_simulator_status()
        self.assertEqual(status, "idle", f"Статус симулятора должен быть 'idle', получено '{status}'")
        print(f"✓ Состояние после остановки трансляции: {status}")
    
    def test_04_recording(self):
        """Тест 4: Запуск записи и проверка состояния"""
        print("\nТест 4: Запуск записи")
        
        # Отправляем команду на запуск записи
        response = self.send_jsonrpc_request("VideoRpc.Record")
        self.assertIn("result", response, f"Ответ не содержит поле 'result': {response}")
        self.assertEqual(response["result"]["res"], "record", f"Ожидалось состояние 'record', получено '{response['result']['res']}'")
        
        # Проверяем статус после запуска записи
        status = self.get_simulator_status()
        self.assertEqual(status, "record", f"Статус симулятора должен быть 'record', получено '{status}'")
        print(f"✓ Состояние после запуска записи: {status}")
        
        # Делаем паузу для эмуляции записи
        time.sleep(2)
        
        # Останавливаем запись
        response = self.send_jsonrpc_request("VideoRpc.Stop")
        status = self.get_simulator_status()
        self.assertEqual(status, "idle", f"Статус симулятора должен быть 'idle', получено '{status}'")
        print(f"✓ Состояние после остановки записи: {status}")

    def test_05_stress_test(self):
        """Тест 5: Стресс-тест быстрого переключения между режимами"""
        print("\nТест 5: Стресс-тест переключения режимов")
        
        commands = [
            ("VideoRpc.Show", "show"),
            ("VideoRpc.Record", "record"),
            ("VideoRpc.Stop", "idle"),
            ("VideoRpc.Show", "show"),
            ("VideoRpc.Stop", "idle"),
            ("VideoRpc.Record", "record"),
            ("VideoRpc.Show", "show"),
            ("VideoRpc.Stop", "idle")
        ]
        
        for i, (command, expected_status) in enumerate(commands, 1):
            response = self.send_jsonrpc_request(command)
            status = response["result"]["res"]
            self.assertEqual(status, expected_status, 
                       f"Шаг {i}: Ожидалось состояние '{expected_status}', получено '{status}'")
            print(f"✓ Шаг {i}: Команда {command} → Статус: {status}")
            time.sleep(0.5)
    
    def test_06_invalid_method_call(self):
        """Тест 6: Проверка обработки некорректного метода"""
        print("\nТест 6: Проверка обработки некорректного метода")
        
        response = self.send_jsonrpc_request("VideoRpc.InvalidMethod")
        self.assertIn("error", response, f"Ответ на некорректный метод должен содержать поле 'error': {response}")
        print(f"✓ Ошибка корректно обработана: {response.get('error', {}).get('message', '')}")

    # Если доступен веб-интерфейс, то добавляем тесты для него
    @unittest.skip("Тест GUI требует запущенный веб-интерфейс")
    def test_07_gui_integration(self):
        """Тест 7: Проверка интеграции с GUI"""
        print("\nТест 7: Проверка интеграции с GUI")
        
        try:
            # Открываем страницу GUI
            self.driver.get(self.GUI_URL)
            
            # Ждем загрузки элементов интерфейса
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "start-stream-btn"))
            )
            
            # Проверяем начальное состояние
            status_element = self.driver.find_element(By.ID, "device-status")
            self.assertEqual(status_element.text, "idle", 
                        f"Начальное состояние в GUI должно быть 'idle', отображается '{status_element.text}'")
            
            # Нажимаем кнопку запуска трансляции
            start_btn = self.driver.find_element(By.ID, "start-stream-btn")
            start_btn.click()
            
            # Ждем обновления статуса
            WebDriverWait(self.driver, 5).until(
                EC.text_to_be_present_in_element((By.ID, "device-status"), "show")
            )
            
            # Проверяем, что симулятор тоже перешел в режим трансляции
            status = self.get_simulator_status()
            self.assertEqual(status, "show", 
                        f"После нажатия кнопки 'Start' в GUI, симулятор должен быть в режиме 'show', сейчас '{status}'")
            
            # Нажимаем кнопку остановки
            stop_btn = self.driver.find_element(By.ID, "stop-btn")
            stop_btn.click()
            
            # Ждем обновления статуса
            WebDriverWait(self.driver, 5).until(
                EC.text_to_be_present_in_element((By.ID, "device-status"), "idle")
            )
            
            # Проверяем, что симулятор вернулся в режим ожидания
            status = self.get_simulator_status()
            self.assertEqual(status, "idle", 
                        f"После нажатия кнопки 'Stop' в GUI, симулятор должен быть в режиме 'idle', сейчас '{status}'")
                
            print("✓ Тест интеграции с GUI успешно пройден")
            
        except TimeoutException:
            self.fail("Превышено время ожидания при загрузке элементов GUI")

if __name__ == "__main__":
    unittest.main(verbosity=2)
