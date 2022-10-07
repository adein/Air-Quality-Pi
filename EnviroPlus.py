"""This module provides convenient access to the Pimoroni EnviroPlus Hat."""
import threading
import time
import traceback
from subprocess import PIPE, Popen

from bme280 import BME280
from enviroplus import gas
from ltr559 import LTR559
from pms5003 import PMS5003, ReadTimeoutError


class EnviroPlus:
    # Constants
    KEY_PM_1 = "pm1"
    KEY_PM_2_5 = "pm2_5"
    KEY_PM_10 = "pm10"
    KEY_PROXIMITY = "proximity"
    KEY_LIGHT = "light"
    KEY_TEMPERATURE = "temperature"
    KEY_PRESSURE = "pressure"
    KEY_HUMIDITY = "humidity"
    KEY_OXIDISING = "oxidising"
    KEY_REDUCING = "reducing"
    KEY_NH3 = "nh3"

    # Class members
    bme280 = None
    ltr559 = None
    pms5003 = None
    latest_pms_readings = None
    pm_thread = None
    run_pm_thread = True

    def __init__(self):
        """Create and initialize EnviroPlus."""
        self.bme280 = BME280()
        self.pms5003 = PMS5003()
        self.ltr559 = LTR559()

    def get_cpu_temperature(self):
        process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
        output, _error = process.communicate()
        return float(output[output.index('=') + 1:output.rindex("'")])

    def start_pms(self):
        if self.pm_thread is not None:
            self.stop_pms()
        self.latest_pms_readings = {}
        self.run_pm_thread = True
        self.pm_thread = threading.Thread(target=self.__read_pms_continuously)
        self.pm_thread.daemon = True
        self.pm_thread.start()

    def stop_pms(self):
        self.run_pm_thread = False
        time.sleep(1)
        self.pm_thread = None

    def __read_pms_continuously(self):
        """Continuously reads from the PMS5003 sensor and stores the most recent values
        in `self.latest_pms_readings` as they become available.
        If the sensor is not polled continuously then readings are buffered on the PMS5003,
        and over time a significant delay is introduced between changes in PM levels and
        the corresponding change in reported levels."""
        while self.run_pm_thread:
            try:
                pm_data = self.pms5003.read()
                self.latest_pms_readings = {
                    self.KEY_PM_1: pm_data.pm_ug_per_m3(1.0, atmospheric_environment=True),
                    self.KEY_PM_2_5: pm_data.pm_ug_per_m3(2.5, atmospheric_environment=True),
                    self.KEY_PM_10: pm_data.pm_ug_per_m3(None, atmospheric_environment=True),
                }
            except ReadTimeoutError:
                print("Failed to read from PMS5003. Resetting sensor.")
                traceback.print_exc()
                self.pms5003.reset()
        print("Stopping PMS thread")

    def read(self):
        gas_data = gas.read_all()
        readings = {
            self.KEY_PROXIMITY: self.ltr559.get_proximity(),
            self.KEY_LIGHT: self.ltr559.get_lux(),
            self.KEY_TEMPERATURE: self.bme280.get_temperature() * 9.0 / 5.0 + 32.0,
            self.KEY_PRESSURE: self.bme280.get_pressure(),
            self.KEY_HUMIDITY: self.bme280.get_humidity(),
            self.KEY_OXIDISING: gas_data.oxidising / 1000,
            self.KEY_REDUCING: gas_data.reducing / 1000,
            self.KEY_NH3: gas_data.nh3 / 1000,
        }
        readings.update(self.latest_pms_readings)
        return readings
