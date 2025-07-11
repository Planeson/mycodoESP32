# coding=utf-8
import copy
import serial
import time
from flask_babel import lazy_gettext

from mycodo.inputs.base_input import AbstractInput
from mycodo.utils.database import db_retrieve_table_daemon

# Measurements
measurements_dict = {
    0: {
        'measurement': 'temperature',
        'unit': 'C'
    },
    1: {
        'measurement': 'humidity',
        'unit': 'percent'
    },
    2: {
        'measurement': 'pressure',
        'unit': 'Pa'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ESP32_SERIAL',
    'input_manufacturer': 'ESP32',
    'input_name': 'ESP32 Serial DHT22 + BMP280',
    'input_library': 'pyserial',
    'measurements_name': 'Temperature/Humidity/Pressure',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.espressif.com/en/products/socs/esp32',
    'url_datasheet': 'https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf',

    'options_enabled': [
        'uart_device',
        'uart_baud_rate',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'pyserial', 'pyserial==3.5')
    ],

    'interfaces': ['UART'],
    'uart_device': '/dev/ttyUSB0',
    'uart_baud_rate': 9600,
}

class InputModule(AbstractInput):
    """A sensor support class that monitors ESP32 via UART"""

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.uart_device = getattr(input_dev, 'uart_device', '/dev/ttyUSB0')
        self.uart_baud_rate = getattr(input_dev, 'uart_baud_rate', 9600)

        if not testing:
            self.setup_device()

    def setup_device(self):
        """Set up the serial connection"""
        try:
            self.serial_device = serial.Serial(
                port=self.uart_device,
                baudrate=self.uart_baud_rate,
                timeout=1
            )
            self.logger.info("ESP32 serial connection established")
        except Exception as e:
            self.logger.error(f"Failed to establish serial connection: {e}")
            self.serial_device = None

    def get_measurement(self):
        """Gets the measurements from ESP32"""
        if not self.serial_device:
            self.logger.error("Serial device not initialized")
            return None

        self.return_dict = copy.deepcopy(measurements_dict)

        try:
            # Request data from ESP32
            self.serial_device.write(b'READ\n')
            time.sleep(0.1)
            
            # Read response
            if self.serial_device.in_waiting:
                response = self.serial_device.readline().decode('utf-8').strip()
                self.logger.debug(f"Received: {response}")
                
                # Parse the response (expecting format: "temp,humidity,pressure")
                if ',' in response:
                    values = response.split(',')
                    if len(values) >= 3:
                        temperature = float(values[0])
                        humidity = float(values[1])
                        pressure = float(values[2])
                        
                        self.value_set(0, temperature)
                        self.value_set(1, humidity)
                        self.value_set(2, pressure)
                        
                        return self.return_dict
                    else:
                        self.logger.error("Invalid data format received")
                        return None
                else:
                    self.logger.error("No valid data received")
                    return None
            else:
                self.logger.error("No data available from ESP32")
                return None

        except Exception as e:
            self.logger.error(f"Error reading from ESP32: {e}")
            return None

    def stop_input(self):
        """Called when Input is stopped"""
        if hasattr(self, 'serial_device') and self.serial_device:
            self.serial_device.close()
            self.logger.info("ESP32 serial connection closed")