# Standard library imports
import time
from datetime import datetime
from threading import Thread
from typing import Optional, Tuple

# Third-party imports
import board
import busio
import requests
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from flask import Flask, jsonify

# Local imports
from .gpio_controller import GPIOController
from config import (
    API_BASE_URL,
    REQUEST_TIMEOUT,
    CARD_READ_TIMEOUT,
    READER_MODE,
    ENROLLER_MODE
)

class PN532Handler:
    """RFID读卡器主控制类"""
    
    def __init__(self, device_mode: int, retry_count: int = 3):
        self.device_mode = device_mode
        self.retry_count = retry_count
        # 初始化硬件控制器
        self.hw = GPIOController()
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

    def read_card(self, timeout: float = CARD_READ_TIMEOUT) -> Optional[str]:
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
                        f"{API_BASE_URL}/users", 
                        timeout = REQUEST_TIMEOUT
                    )
                    
                    users = response.json() 
                    print(f"users: {users}")
                    current_timestamp = int(time.time())
                    matched_user = list(filter(
                        lambda user: user.get('rfid') == card_id and 
                        int(datetime.fromisoformat(user.get('accessStart')).timestamp()) <= current_timestamp <= 
                        int(datetime.fromisoformat(user.get('accessEnd')).timestamp()),
                        users
                    ))
                    print(f"matched_user: {matched_user}")
                    
                    if matched_user:
                        print(f"환영합니다, 카드 ID: {card_id}")
                        user = matched_user[0]
                        post_data = {
                            "method": "rfid",
                            "userId": user.get('id'),
                            "result": True
                        }
                        requests.post(
                            f"{API_BASE_URL}/access/log", 
                            json=post_data,
                            timeout=REQUEST_TIMEOUT
                        )
                        self.hw.open_and_close_door()
                        self.hw.indicate_success()
                        
                    else:
                        post_data = {
                            "method": "rfid",
                            "result": False
                        }
                        requests.post(
                            f"{API_BASE_URL}/access/log", 
                            json=post_data,
                            timeout=REQUEST_TIMEOUT
                        )
                        print(f"경고! 미승인 카드 ID: {card_id}")
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
        app = Flask(__name__)
        
        @app.route('/api', methods=['POST'])
        def enroll():
            try:
                self.hw.start_enrollment_indicator()  # 등록 시작 표시
                card_id = self.read_card(timeout=10)
                
                if card_id is None:
                    self.hw.indicate_failure()
                    return jsonify({'status': 'error', 'message': '카드 읽기 시간 초과'}), 408
                    
                response = requests.post(
                    f"{API_BASE_URL}/users/enroll", 
                    json={'card_id': card_id},
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    self.hw.indicate_success()
                    return jsonify({
                        'type': 'rfid',
                        'card_id': card_id,
                        'status': 'success',
                        'message': '카드 등록 성공'
                    })
                else:
                    self.hw.indicate_failure()
                    return jsonify({
                        'status': 'error',
                        'message': '원격 서버 등록 실패'
                    }), 500
                    
            except Exception as e:
                self.hw.indicate_failure()
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()
        print(f"등록 서버가 포트 {port}에서 시작되었습니다.")        

    def __del__(self):
        """析构函数：清理硬件资源"""
        if hasattr(self, 'hw'):
            self.hw.cleanup()
