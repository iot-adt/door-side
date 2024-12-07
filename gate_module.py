from flask import Flask, jsonify, request
from threading import Thread
import requests
from config import API_BASE_URL, REQUEST_TIMEOUT

app = Flask(__name__)        

class GateController:
    def __init__(self, gpio_controller):
        self.hw = gpio_controller

    def open_and_close_door(self):
        # 实现开门功能
        print("开门功能被调用")
        self.hw.open_and_close_door()
        self.hw.indicate_success()  # 假设这是开门指示

@app.route('/api/open-door', methods=['POST'])
def open_door():
    try:
        gate_controller.open_and_close_door()
        return jsonify({'status': 'success', 'message': 'doorOpened'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def start_flask_app():
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    from modules.gpio_controller import GPIOController
    gpio_controller = GPIOController()
    gate_controller = GateController(gpio_controller)
    
    # 启动Flask应用
    flask_thread = Thread(target=start_flask_app)
    flask_thread.start()
    
    # 其他初始化代码可以放在这里
    print("门禁系统已启动，正在监听 /api/opendoor 请求...")
    
# def open_door():
#     try:
#         while True:
            
            
#         self.hw.start_enrollment_indicator()  # 등록 시작 표시
#         card_id = self.read_card(timeout=10)
        
#         if card_id is None:
#             self.hw.indicate_failure()
#             return jsonify({'status': 'error', 'message': '카드 읽기 시간 초과'}), 408
            
#         response = requests.post(
#             f"{API_BASE_URL}/users/enroll", # Check Here
#             json={'card_id': card_id},
#             timeout=REQUEST_TIMEOUT
#         )
        
#         if response.status_code == 200:
#             self.hw.indicate_success()
#             return jsonify({
#                 'type': 'rfid',
#                 'card_id': card_id,
#                 'status': 'success',
#                 'message': '카드 등록 성공'
#             })
#         else:
#             self.hw.indicate_failure()
#             return jsonify({
#                 'status': 'error',
#                 'message': '원격 서버 등록 실패'
#             }), 500
            
#     except Exception as e:
#         self.hw.indicate_failure()
#         return jsonify({
#             'status': 'error',
#             'message': str(e)
#         }), 500

# Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False)).start()
# print(f"등록 서버가 포트 {port}에서 시작되었습니다.") # Check Here