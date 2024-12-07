import time
import board
import busio
import RPi.GPIO as GPIO

# Local imports
from config import MOTOR_DURATION_SECONDS

class GPIOController:
    """硬件控制类：负责LED和蜂鸣器的控制"""

    def __init__(self, 
                 motor_pin1=26, 
                 motor_pin2=19,
                 red_led_pin=13, 
                 green_led_pin=6,
                 buzzer_pin=5
                 ):
        # 初始化GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.pins = {
            'green_led': green_led_pin,
            'red_led': red_led_pin,
            'buzzer': buzzer_pin, 
            'motor_pin1': motor_pin1,
            'motor_pin2': motor_pin2, 
            
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
    

    def open_door(self):
        """马达前进后停止"""
        
        GPIO.output(self.pins['motor_pin1'], GPIO.HIGH)  # motor_pin1输出电压
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)  # motor_pin2停止输出电压
        print("电机前进中...")
        
        time.sleep(MOTOR_DURATION_SECONDS) 
        
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)  # motor_pin1停止输出电压
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)  # motor_pin2停止输出电压
        print("电机停止")

    def close_door(self):
        """马达后退后停止"""
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)  # motor_pin1停止输出电压
        GPIO.output(self.pins['motor_pin2'], GPIO.HIGH)  # motor_pin2输出电压
        print("电机后退中...")
        
        time.sleep(MOTOR_DURATION_SECONDS + 0.03) # 0.03秒是为了防止电机停止时门未完全关闭
        
        GPIO.output(self.pins['motor_pin1'], GPIO.LOW)  # motor_pin1停止输出电压
        GPIO.output(self.pins['motor_pin2'], GPIO.LOW)  # motor_pin2停止输出电压
        print("电机停止")

    def open_and_close_door(self):
        """电机左转"""
        self.open_door()
        time.sleep(0.5)        
        self.close_door()
        
    def cleanup(self):
        """清理GPIO资源"""
        GPIO.cleanup()
