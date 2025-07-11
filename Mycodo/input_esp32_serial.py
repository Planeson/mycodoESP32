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
        'measurement': 'ion_concentration',
        'unit': 'pH'
    },
    2: {
        'measurement': 'electrical_conductivity',
        'unit': 'uS_cm'
    }
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ESP32_SERIAL',
    'input_manufacturer': '!Planeson',
    'input_name': 'Atlas Scientific Hydroponic Kit',
    'input_library': 'pyserial',
    'measurements_name': 'Temperature/pH/Electrical Conductivity',
    'measurements_dict': measurements_dict,
    'url_manufacturer': 'https://www.espressif.com/en/products/socs/esp32',
    'url_datasheet': 'https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf',

    'options_enabled': [
        'uart_location',
        'uart_baud_rate',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'serial', 'pyserial>=3.0')
    ],

    'interfaces': ['UART'],
    'uart_location': '/dev/ttyUSB0',
    'uart_baud_rate': 9600,
}

class InputModule(AbstractInput):
    """A sensor support class that monitors ESP32 via UART"""

    def __init__(self, input_dev, testing=False):
        super(InputModule, self).__init__(input_dev, testing=testing, name=__name__)

        self.uart_device = getattr(input_dev, 'uart_location', '/dev/ttyUSB0')
        self.uart_baud_rate = getattr(input_dev, 'uart_baud_rate', 9600)

        if not testing:
            self.setup_device()

    def setup_device(self):
        """Set up the serial connection"""
        try:
            self.serial_device = serial.Serial(
                port=self.uart_device,
                baudrate=self.uart_baud_rate,
                timeout=3  # Increased timeout
            )
            time.sleep(2)  # Give the device time to initialize
            # Clear any existing data in the buffer
            self.serial_device.reset_input_buffer()
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
            # flush input buffer to ensure no stale data
            self.serial_device.reset_input_buffer()
            time.sleep(1.5)  # Short delay to wait for new data

            # Read all data, find last complete line
            latest_line = None
            max_attempts = 10
            for attempt in range(max_attempts):
                if self.serial_device.in_waiting > 0:
                    try:
                        # Read a line
                        line = self.serial_device.readline().decode('utf-8').strip()
                        if line:  # If we got a non-empty line
                            latest_line = line
                            self.logger.debug(f"Read line (attempt {attempt + 1}): {line}")
                            
                            # Check if there's more data coming
                            time.sleep(0.1)  # Small delay to see if more data arrives
                            if self.serial_device.in_waiting == 0:
                                # No more data, this is likely the latest
                                break
                    except UnicodeDecodeError:
                        # Skip malformed data
                        continue
                else:
                    # No data available, wait a bit
                    time.sleep(0.1)
            
            if latest_line:
                self.logger.debug(f"Latest complete line: {latest_line}")
                
                # Parse the response (expecting format: "RTD: 23.34 PH: 4.56 EC: 34.53")
                if 'RTD:' in latest_line and 'PH:' in latest_line and 'EC:' in latest_line:
                    try:
                        # Extract values using split
                        parts = latest_line.split()
                        rtd_value = None
                        ph_value = None
                        ec_value = None
                        
                        for i, part in enumerate(parts):
                            if part == 'RTD:' and i + 1 < len(parts):
                                rtd_value = float(parts[i + 1])
                            elif part == 'PH:' and i + 1 < len(parts):
                                ph_value = float(parts[i + 1])
                            elif part == 'EC:' and i + 1 < len(parts):
                                ec_value = float(parts[i + 1])
                        
                        if rtd_value is not None and ph_value is not None and ec_value is not None:
                            self.value_set(0, rtd_value)
                            self.value_set(1, ph_value)
                            self.value_set(2, ec_value)
                            
                            self.logger.info(f"Successfully parsed - RTD: {rtd_value}, PH: {ph_value}, EC: {ec_value}")
                            return self.return_dict
                        else:
                            self.logger.warning("Could not parse all values from response")
                            
                    except ValueError as e:
                        self.logger.error(f"Error parsing values: {e}")
                else:
                    self.logger.debug(f"Invalid data format received: {latest_line}")
            else:
                self.logger.error("No valid data received")
                
            return None

        except Exception as e:
            self.logger.error(f"Error reading from ESP32: {e}")
            return None

    def stop_input(self):
        """Called when Input is stopped"""
        if hasattr(self, 'serial_device') and self.serial_device:
            self.serial_device.close()
            self.logger.info("ESP32 serial connection closed")