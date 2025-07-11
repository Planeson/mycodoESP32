INPUT_INFORMATION = {
    "input_name": "ESP32 Serial",
    "input_description": "Parses RTD, PH, EC readings from ESP32 serial output.",
    "input_author": "Your Name",
    "input_version": "1.0",
    "input_channels": [
        {"name": "RTD", "unit": "°C"},
        {"name": "PH", "unit": ""},
        {"name": "EC", "unit": "uS/cm"}
    ]
}
import re
import serial
from mycodo.inputs.base_input import Input

class InputESP32Serial(Input):
    """Custom input for ESP32 hydroponics serial data"""

    def __init__(self, *args, **kwargs):
        super(InputESP32Serial, self).__init__(*args, **kwargs)
        self.regex = re.compile(r"RTD:\s*([0-9.]+)\s+PH:\s*([0-9.]+)\s+EC:\s*([0-9.]+)")
        self.serial_port = '/dev/ttyUSB0'  # Change to your actual device
        self.baudrate = 9600
        self.timeout = 2
        self.ser = None

    def initialize(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baudrate, timeout=self.timeout)
        except Exception as err:
            self.logger.error(f"Serial init error: {err}")

    def read(self):
        if not self.ser or not self.ser.is_open:
            self.initialize()
            if not self.ser or not self.ser.is_open:
                return

        try:
            line = self.ser.readline().decode().strip()
            match = self.regex.search(line)
            if match:
                rtd = float(match.group(1))
                ph = float(match.group(2))
                ec = float(match.group(3))
                self.add_measurement(0, rtd)  # Channel 0: RTD
                self.add_measurement(1, ph)   # Channel 1: PH
                self.add_measurement(2, ec)   # Channel 2: EC
        except Exception as err:
            self.logger.error(f"Serial read error: {err}")