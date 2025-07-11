import copy
from flask_babel import lazy_gettext

# Measurements
measurements_dict = {
    0: {'measurement': 'temperature', 'unit': 'C'},
    1: {'measurement': 'ion_concentration', 'unit': 'pH'},
    2: {'measurement': 'electrical_conductivity', 'unit': 'uS_cm'}
}

# Input information
INPUT_INFORMATION = {
    'input_name_unique': 'ESP32_SERIAL',
    'input_manufacturer': 'Custom',
    'input_name': 'ESP32 Hydroponics Serial',
    'input_library': 'pyserial',
    'measurements_name': 'Temperature, pH, Electrical Conductivity',
    'measurements_dict': measurements_dict,
    'url_manufacturer': '',
    'url_datasheet': '',
    'options_enabled': [
        'uart_location',
        'uart_baud_rate',
        'period',
        'pre_output'
    ],
    'options_disabled': ['interface'],
    'dependencies_module': [
        ('pip-pypi', 'pyserial')
    ],
    'interfaces': ['UART'],
    'uart_location': '/dev/ttyUSB0',
    'uart_baud_rate': 9600,
    'custom_commands_message': lazy_gettext('No custom commands for this input.'),
    'custom_commands': [],
    'input_description': lazy_gettext('Parses RTD, PH, EC readings from ESP32 serial output.'),
    'input_author': 'Your Name',
    'input_version': '1.0',
}
import re
import serial
from mycodo.inputs.base_input import AbstractInput

class InputModule(AbstractInput):
    """Custom input for ESP32 hydroponics serial data"""

    def __init__(self, input_dev, testing=False):
        super().__init__(input_dev, testing=testing, name=__name__)
        self.regex = re.compile(r"RTD:\s*([0-9.]+)\s+PH:\s*([0-9.]+)\s+EC:\s*([0-9.]+)")
        self.ser = None
        if not testing:
            self.try_initialize()

    def initialize(self):
        self.uart_location = self.input_dev.uart_location
        self.uart_baud_rate = self.input_dev.uart_baud_rate
        try:
            self.ser = serial.Serial(self.uart_location, self.uart_baud_rate, timeout=2)
        except Exception as err:
            self.logger.error(f"Serial init error: {err}")

    def get_measurement(self):
        self.return_dict = copy.deepcopy(measurements_dict)
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
                self.value_set(0, rtd)
                self.value_set(1, ph)
                self.value_set(2, ec)
        except Exception as err:
            self.logger.error(f"Serial read error: {err}")
        return self.return_dict