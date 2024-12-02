import time 
import boasrd
import busio
import RPi.GPIO as GPIO
from datetime import datetime
from typing import Tuple, Optional
from adafruit_pn532.i2c import PN532_I2C
import requests
from threading import Thread
from flask import Flask, jsonify

class HardwareController:
    """硬件控制类：负责LED和蜂鸣器的控制"""
    
    def __init__(self, green_led_pin=18, red_led_pin=23, buzzer_pin=24):
        # 初始化GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.pins = {
            'green_led': green_led_pin,
            'red_led': red_led_pin,
            'buzzer': buzzer_pin
        }
        
        # 所有引脚设置为输出模式
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        self._blink_flag = False
    
    def _blink_led(self, led_pin: int, duration: float = 0.5):
        """控制LED闪烁"""
        GPIO.output(led_pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(led_pin, GPIO.LOW)
    
    def _beep(self, duration: float = 0.2):
        """蜂鸣器响声"""
        GPIO.output(self.pins['buzzer'], GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.pins['buzzer'], GPIO.LOW)

    def indicate_success(self):
        """成功指示：绿色LED亮起 + 蜂鸣器响一次"""
        self._beep(0.1)
        self._blink_led(self.pins['green_led'], 2)

    def indicate_failure(self):
        """失败指示：红色LED闪烁 + 蜂鸣器响两次"""
        for _ in range(2):
            self._beep(0.1)
            time.sleep(0.1)
        self._blink_led(self.pins['red_led'], 2)

    def start_enrollment_indicator(self):
        """开始注册指示：绿色LED闪烁"""
        self._blink_led(self.pins['green_led'], 0.5)
    
    def cleanup(self):
        """清理GPIO资源"""
        GPIO.cleanup()


class PN532Handler:
    """RFID读卡器主控制类"""
    
    def __init__(self, device_mode: int, retry_count: int = 3):
        self.device_mode = device_mode
        self.retry_count = retry_count
        # 初始化硬件控制器
        self.hw = HardwareController()
        self._initialize_pn532()
    
    def _initialize_pn532(self):
        """初始化PN532，包含重试机制"""
        for attempt in range(self.retry_count):
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                time.sleep(1)
                self.pn532 = PN532_I2C(i2c, debug=False)
                self.pn532.SAM_configuration()
                version = self.pn532.firmware_version
                print(f"已确认PN532固件版本：{version}")
                return True
            except Exception as e:
                print(f"初始化尝试 {attempt + 1} 失败：{str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(2)
                else:
                    raise RuntimeError("PN532初始化失败。请检查硬件连接。")

    def read_card(self, timeout: float = 1) -> Optional[str]:
        """读取卡片UID"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                uid = self.pn532.read_passive_target(timeout=0.5)
                if uid is not None:
                    return bytes(uid).hex()
            except Exception as e:
                print(f"读取卡片错误：{str(e)}")
                time.sleep(0.1)
        return None

    def check_card_access(self):
        """读卡器模式：持续读取卡片并验证权限"""
        if self.device_mode != READER_MODE:
            raise RuntimeError("当前设备不是读卡器模式。")
            
        print("\n卡片访问验证模式开始... 按 Ctrl+C 结束。")
        try:
            while True:
                card_id = self.read_card()
                if card_id is None:
                    continue
                
                try:
                    response = requests.get(
                        f"{API_BASE_URL}/api/entry/{card_id}", # 检查这里
                        timeout=REQUEST_TIMEOUT
                    )
                    if response.status_code == 200 and response.json().get('allowed'):
                        print(f"欢迎，卡片ID：{card_id}")
                        self.hw.indicate_success()
                    else:
                        print(f"警告！未授权卡片ID：{card_id}")
                        self.hw.indicate_failure()
                except requests.RequestException as e:
                    print(f"服务器连接失败：{str(e)}")
                    self.hw.indicate_failure()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n卡片验证模式结束。")
        except Exception as e:
            print(f"卡片验证模式错误：{str(e)}")

    def start_enrollment_server(self, port: int = 5000):
        """注册器模式：启动Flask服务器，等待注册命令"""
        if self.device_mode != ENROLLER_MODE:
            raise RuntimeError("当前设备不是注册器模式。")
            
        print("\n卡片注册模式开始... 按 Ctrl+C 结束。")
        
        try:
            while True:
                self.hw.start_enrollment_indicator()  # 开始注册指示
                card_id = self.read_card(timeout=10)
                
                if card_id is None:
                    self.hw.indicate_failure()
                    time.sleep(0.5)
                    continue
                    
                response = requests.post(
                    f"{API_BASE_URL}/temporary-user?rfid={card_id}",
                )
                print(response)
                self.hw.indicate_success()
                print(f"正在注册，卡片ID：{card_id}")
                time.sleep(3)
                
        except Exception as e:
            self.hw.indicate_failure()

    def __del__(self):
        """析构函数：清理硬件资源"""
        if hasattr(self, 'hw'):
            self.hw.cleanup()

# 常量定义
READER_MODE = 0
ENROLLER_MODE = 1
API_BASE_URL = "http://10.144.85.43:8080/api"
REQUEST_TIMEOUT = 5
CARD_READ_TIMEOUT = 1

DEVICE_MODE = ENROLLER_MODE # 待完成

if __name__ == "__main__":
    try:
        handler = PN532Handler(device_mode = DEVICE_MODE)
        if DEVICE_MODE == READER_MODE:
            handler.check_card_access()
        else:
            handler.start_enrollment_server()
            
    except Exception as e:
        print(f"程序错误：{str(e)}")