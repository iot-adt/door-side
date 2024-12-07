import time
from datetime import datetime
from threading import Thread
from typing import Optional

import board
import busio
import requests
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from flask import Flask, jsonify

from .gpio_controller import GPIOController
from config import (
    API_BASE_URL,
    REQUEST_TIMEOUT,
    CARD_READ_TIMEOUT,
    READER_MODE,
    ENROLLER_MODE
)


class PN532Handler:
    """Main controller class for the RFID reader."""

    def __init__(self, device_mode: int, retry_count: int = 3):
        self.device_mode = device_mode
        self.retry_count = retry_count
        self.hw = GPIOController()
        self._initialize_pn532()

    def _initialize_pn532(self):
        """Initialize the PN532 with a retry mechanism."""
        for attempt in range(self.retry_count):
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                time.sleep(1)
                self.pn532 = PN532_I2C(i2c, debug=False)
                self.pn532.SAM_configuration()
                version = self.pn532.firmware_version
                print(f"PN532 firmware version confirmed: {version}")
                return True
            except Exception as e:
                print(f"Initialization attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(2)
                else:
                    raise RuntimeError("PN532 initialization failed. Please check hardware connections.")

    # Processing logic methods remain unchanged
    def read_card(self, timeout: float = CARD_READ_TIMEOUT) -> Optional[str]:
        """Read card UID."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                uid = self.pn532.read_passive_target(timeout=0.3)
                if uid is not None:
                    return bytes(uid).hex()
            except Exception as e:
                print(f"Error reading card: {e}")
                time.sleep(0.1)
        return None

    def check_card_access(self):
        """Reader mode: continuously read cards and verify access."""
        if self.device_mode != READER_MODE:
            raise RuntimeError("Current device is not in reader mode.")
        print("\nCard access verification mode started... Press Ctrl+C to exit.")
        try:
            while True:
                card_id = self.read_card()
                if card_id is None:
                    continue
                try:
                    response = requests.get(f"{API_BASE_URL}/users", timeout=REQUEST_TIMEOUT)
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
                        print(f"Welcome, Card ID: {card_id}")
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
                        print(f"Warning! Unauthorized Card ID: {card_id}")
                        self.hw.indicate_failure()
                except requests.RequestException as e:
                    print(f"Server connection failed: {e}")
                    self.hw.indicate_failure()
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nCard verification mode ended.")
        except Exception as e:
            print(f"Card verification mode error: {e}")

    def start_enrollment_server(self, port: int = 5000):
        """Enroller mode: start Flask server to wait for enrollment commands."""
        if self.device_mode != ENROLLER_MODE:
            raise RuntimeError("Current device is not in enroller mode.")
        print("\nCard enrollment mode started... Press Ctrl+C to exit.")
        app = Flask(__name__)

        @app.route('/api', methods=['POST'])
        def enroll():
            try:
                self.hw.start_enrollment_indicator()
                card_id = self.read_card(timeout=10)
                if card_id is None:
                    self.hw.indicate_failure()
                    return jsonify({'status': 'error', 'message': 'Card read timeout'}), 408
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
                        'message': 'Card enrollment successful'
                    })
                else:
                    self.hw.indicate_failure()
                    return jsonify({
                        'status': 'error',
                        'message': 'Remote server enrollment failed'
                    }), 500
            except Exception as e:
                self.hw.indicate_failure()
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()
        print(f"Enrollment server started on port {port}.")

    def __del__(self):
        """Destructor: clean up hardware resources."""
        if hasattr(self, 'hw'):
            self.hw.cleanup()
