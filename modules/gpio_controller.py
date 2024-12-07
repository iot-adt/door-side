import time
import RPi.GPIO as GPIO

# Local imports
from config import MOTOR_DURATION_SECONDS

class GPIOController:
    """Hardware control class: responsible for controlling LEDs and buzzer"""

    def __init__(self, 
                 motor_pin1=26, 
                 motor_pin2=19,
                 red_led_pin=13, 
                 green_led_pin=6,
                 buzzer_pin=5
                 ):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.pins = {
            'green_led': green_led_pin,
            'red_led': red_led_pin,
            'buzzer': buzzer_pin, 
            'motor_pin1': motor_pin1,
            'motor_pin2': motor_pin2, 
            
        }
        
        # Set all pins to output mode
        for pin in self.pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        self._blink_flag = False
    
    def _blink_led(self, led_pin: int, duration: float = 0.5):
        """Control LED blinking"""
        GPIO.output(led_pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(led_pin, GPIO.LOW)
    
    def _beep(self, duration: float = 0.2):
        """Buzzer sound"""
        GPIO.output(self.pins['buzzer'], GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.pins['buzzer'], GPIO.LOW)

    def indicate_success(self):
        """Success indication: green LED lights up + buzzer sounds once"""
        self._beep(0.1)
        self._blink_led(self.pins['green_led'], 2)

    def indicate_failure(self):
        """Failure indication: red LED blinks + buzzer sounds twice"""
        for _ in range(2):
            self._beep(0.1)
            time.sleep(0.1)
        self._blink_led(self.pins['red_led'], 2)

    def start_enrollment_indicator(self):
        """Start enrollment indication: green LED blinks"""
        self._blink_led(self.pins['green_led'], 0.5)
    

    def _open_door(self):
        """Motor moves forward and then stops"""
        
        GPIO.output(self.pins['motor_pin1'], GPIO.HIGH)
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)
        print("Motor moving forward...")
        
        time.sleep(MOTOR_DURATION_SECONDS) 
        
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)
        print("Motor stopped")

    def _close_door(self):
        """Motor moves backward and then stops"""
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)
        GPIO.output(self.pins['motor_pin2'], GPIO.HIGH)
        print("Motor moving backward...")
        
        time.sleep(MOTOR_DURATION_SECONDS + 0.03) # 0.03 seconds to ensure the door is fully closed
        
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)
        print("Motor stopped")
        
    def open_and_close_door(self):
        """Motor moves forward and then backward"""
        self._open_door()
        time.sleep(0.5)        
        self._close_door()
        
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
