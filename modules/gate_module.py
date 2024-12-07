from flask import Flask, jsonify, request
from modules.gpio_controller import GPIOController

app = Flask(__name__)
gate_controller = None  # Global variable to store the instance

class GateController:
    def __init__(self):
        self.hw = GPIOController()
    
    def open_door(self):  # Change to a regular instance method
        print("Open door function called")
        self.hw.open_and_close_door()
        self.hw.indicate_success()

def start_flask_app():
    global gate_controller
    gate_controller = GateController()  # Create a global instance
    app.run(host='0.0.0.0', port=5000, debug=False)
    
# Flask route using a regular function
@app.route('/api/open-door', methods=['POST'])
def remote_open_door():
    try:
        gate_controller.open_door()
        return jsonify({'status': 'success', 'message': 'doorOpened'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
