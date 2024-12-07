from threading import Thread
from modules import PN532Handler
from modules.gpio_controller import GPIOController
from modules.gate_module import GateController, start_flask_app  # Import the standalone start_flask_app function
from config import DEVICE_MODE, READER_MODE, ENROLLER_MODE

if __name__ == "__main__":
    try:
        # Initialize GPIO controller (shared by two services)
        gpio_controller = GPIOController()
        
        # Initialize gate controller
        gate_controller = GateController()
        gate_thread = Thread(target=start_flask_app, daemon=True)  # Correctly create thread
        gate_thread.start()
        print("Gate access system has started, listening to /api/opendoor requests...")

        # Initialize RFID processor
        handler = PN532Handler(device_mode=DEVICE_MODE)
        if DEVICE_MODE == READER_MODE:
            handler.check_card_access()
        else:
            handler.start_enrollment_server()
            
    except Exception as e:
        print(f"Program error：{str(e)}")