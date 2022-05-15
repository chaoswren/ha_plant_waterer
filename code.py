import board
import busio
import time
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_bme280 import basic as adafruit_bme280
from secrets import secrets
i2c = busio.I2C(board.SCL1, board.SDA1,frequency=100000)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = 1019.0
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s" % secrets["ssid"])

pool = socketpool.SocketPool(wifi.radio)

configuration_topic1 = "homeassistant/sensor/plantEnvironmentT/config"
config_payload1 = """{"name": "Plant Environment Temperature",
                   "device_class": "temperature",
                   "state_topic": "homeassistant/sensor/plantEnvironment/state",
                   "unit_of_measurement": "℉",
                   "value_template": "{{value_json.temperature}}"}"""
configuration_topic2 = "homeassistant/sensor/plantEnvironmentH/config"
config_payload2 = """{"name": "Plant Environment Humidity",
                   "device_class": "humidity",
                   "state_topic": "homeassistant/sensor/plantEnvironment/state",
                   "unit_of_measurement": "%",
                   "value_template": "{{value_json.humidity}}"}"""
configuration_topic3 = "homeassistant/sensor/plantEnvironmentP/config"
config_payload3 = """{"name": "Plant Environment Pressure",
                   "device_class": "pressure",
                   "state_topic": "homeassistant/sensor/plantEnvironment/state",
                   "unit_of_measurement": "hPa",
                   "value_template": "{{value_json.pressure}}"}"""
                    
state_topic = "homeassistant/sensor/plantEnvironment/state"


mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["user"],
    password=secrets["broker_pass"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

mqtt_client.connect()
mqtt_client.publish(configuration_topic1, config_payload1, retain=True)
mqtt_client.publish(configuration_topic2, config_payload2, retain=True)
mqtt_client.publish(configuration_topic3, config_payload3, retain=True)

while True:
    mqtt_client.publish(state_topic, "{\"temperature\": %0.1f, \"humidity\": %0.1f, \"pressure\": %0.1f }" % (float(bme280.temperature*9/5+32), bme280.humidity, bme280.pressure))
    time.sleep(30)
