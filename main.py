from modules import PN532Handler
from config import DEVICE_MODE, READER_MODE, ENROLLER_MODE

"""
[Changes]
Done: 
    1. 将原代码分为main, rfid, gpio三部分. 
    3. (重新评估)read_card(self, timeout: float = 1) -> read_card(self, timeout: float = CARD_READ_TIMEOUT) 
    4. 
    
ToDo: 
    1. 更改GPIO引脚数, 以方便连接
    2. 所有的常量集中单独的config文件中
"""

if __name__ == "__main__":
    try:
        handler = PN532Handler(device_mode=DEVICE_MODE)
        if DEVICE_MODE == READER_MODE:
            handler.check_card_access()
        else:
            handler.start_enrollment_server()
            
    except Exception as e:
        print(f"程序错误：{str(e)}")
