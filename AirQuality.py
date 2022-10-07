"""This module provides Air Quality Data using a Pimoroni EnviroPlus Hat."""
import collections
import threading
import time

import aqi
import paho.mqtt.client as mqtt

from EnviroPlus import EnviroPlus


class AirQuality:
    # Constants
    MQTT_CLIENT_NAME = 'MQTT_CLIENT_NAME'
    MQTT_USERNAME = 'MQTT_USERNAME'
    MQTT_PASSWORD = 'MQTT_PASSWORD'
    MQTT_HOST = 'MQTT_HOST_IP'
    TOPIC_TEMPERATURE = '/home/airquality/temperature'
    TOPIC_PRESSURE = '/home/airquality/pressure'
    TOPIC_HUMIDITY = '/home/airquality/humidity'
    TOPIC_LIGHT = '/home/airquality/light'
    TOPIC_PROXIMITY = '/home/airquality/proximity'
    TOPIC_REDUCING = '/home/airquality/gas/reducing'
    TOPIC_OXIDISING = '/home/airquality/gas/oxidising'
    TOPIC_NH3 = '/home/airquality/gas/nh3'
    TOPIC_PM_1 = '/home/airquality/pm/1'
    TOPIC_PM_2_5 = '/home/airquality/pm/2_5'
    TOPIC_PM_10 = '/home/airquality/pm/10'
    TOPIC_AQI = '/home/airquality/aqi'
    KEY_AQI = "aqi"

    # Class members
    client = None
    ep = None
    init_delay = None
    interval = None
    run_samples = True
    sampling_thread = None
    samples = None

    def __init__(self):
        """Create and initialize Air Quality."""
        self.ep = EnviroPlus()
        self.client = mqtt.Client(self.MQTT_CLIENT_NAME)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        # self.client.on_message = self.on_message
        # self.client.on_publish = self.on_publish
        # self.client.on_log = self.on_log

    def on_connect(self, client, obj, flags, rc):
        print("connect: " + str(rc))

    def on_disconnect(self, client, userdata, rc):
        # TODO
        print("disconnect: " + str(rc))

    def on_message(self, client, obj, msg):
        print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    def on_publish(self, client, obj, mid):
        print("publish: " + str(mid))

    def on_subscribe(self, client, obj, mid, granted_qos):
        print("subscribe: " + str(mid) + " " + str(granted_qos))

    def on_log(self, client, obj, level, string):
        print(string)

    def __connect(self):
        self.client.username_pw_set(self.MQTT_USERNAME, self.MQTT_PASSWORD)
        self.client.connect(self.MQTT_HOST)
        self.client.loop_start()

    def __disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def __initialize_sensors(self, delay):
        # Take and ignore readings for a specified delay in seconds to allow sensors time to warm up
        end_time = time.time() + delay
        while time.time() < end_time:
            self.ep.read()
            time.sleep(1)

    def __do_sampling(self):
        next_sample_time = time.time()
        next_publish_time = time.time() + self.interval
        while self.run_samples:
            # Get new data sample
            sample = self.ep.read()
            sample[self.KEY_AQI] = AirQuality.calculate_aqi(sample[EnviroPlus.KEY_PM_2_5], sample[EnviroPlus.KEY_PM_10])
            self.samples.append(sample)

            do_publish = time.time() >= next_publish_time
            if do_publish:
                # Iterate through all topics and calculate averages
                publish_sample = {}
                for topic in self.samples[0].keys():
                    # Calculate sum and average of values for current topic
                    value_sum = sum([current_sample[topic] for current_sample in self.samples])
                    value_avg = value_sum / len(self.samples)
                    publish_sample[topic] = value_avg
                self.__publish(publish_sample)
                next_publish_time += self.interval
            next_sample_time += 1
            time.sleep(max(next_sample_time - time.time(), 0))
        print("Stopping sampling thread")

    @staticmethod
    def calculate_aqi(pm_2_5, pm_10):
        try:
            return float(aqi.to_aqi([
                (aqi.POLLUTANT_PM25, str(pm_2_5)),
                (aqi.POLLUTANT_PM10, str(pm_10))
            ]))
        except IndexError:
            print('AQI IndexError! (PM 2.5 = ' + str(pm_2_5) + ', PM 10 = ' + str(pm_10) + ')')
            return 500.0

    def __stop_sampling(self):
        self.run_samples = False
        time.sleep(self.interval)
        self.sampling_thread = None

    def __publish(self, sample):
        self.client.publish(self.TOPIC_TEMPERATURE, sample[EnviroPlus.KEY_TEMPERATURE], qos=0)
        self.client.publish(self.TOPIC_PRESSURE, sample[EnviroPlus.KEY_PRESSURE], qos=0)
        self.client.publish(self.TOPIC_HUMIDITY, sample[EnviroPlus.KEY_HUMIDITY], qos=0)
        self.client.publish(self.TOPIC_LIGHT, sample[EnviroPlus.KEY_LIGHT], qos=0)
        self.client.publish(self.TOPIC_PROXIMITY, sample[EnviroPlus.KEY_PROXIMITY], qos=0)
        self.client.publish(self.TOPIC_REDUCING, sample[EnviroPlus.KEY_REDUCING], qos=0)
        self.client.publish(self.TOPIC_OXIDISING, sample[EnviroPlus.KEY_OXIDISING], qos=0)
        self.client.publish(self.TOPIC_NH3, sample[EnviroPlus.KEY_NH3], qos=0)
        self.client.publish(self.TOPIC_PM_1, sample[EnviroPlus.KEY_PM_1], qos=0)
        self.client.publish(self.TOPIC_PM_2_5, sample[EnviroPlus.KEY_PM_2_5], qos=0)
        self.client.publish(self.TOPIC_PM_10, sample[EnviroPlus.KEY_PM_10], qos=0)
        self.client.publish(self.TOPIC_AQI, sample[self.KEY_AQI], qos=0)

    def start(self, init_delay=15, interval=5):
        self.init_delay = init_delay
        self.interval = interval
        self.samples = collections.deque(maxlen=interval)
        self.ep.start_pms()
        time.sleep(1)
        self.__initialize_sensors(init_delay)
        self.__connect()
        if self.sampling_thread is not None:
            self.__stop_sampling()
        self.sampling_thread = threading.Thread(target=self.__do_sampling())
        self.sampling_thread.daemon = True
        self.run_samples = True
        self.sampling_thread.start()
        return self.sampling_thread

    def stop(self):
        self.__stop_sampling()
        self.ep.stop_pms()
        self.__disconnect()
