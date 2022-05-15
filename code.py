import board
import busio
import digitalio
import time
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_bme280 import basic as adafruit_bme280
from adafruit_seesaw.seesaw import Seesaw
from secrets import secrets
i2c = busio.I2C(board.SCL1, board.SDA1,frequency=100000)
ss = Seesaw(i2c, addr=0x36)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
bme280.sea_level_pressure = 1019.0
pump_running = False
pump_reverse_direction = False
update_period = 30
pump_max_run_time = 20
last_update_time = time.monotonic()
pump_start_time = time.monotonic()


pump_fwd = digitalio.DigitalInOut(board.A3)
pump_rev = digitalio.DigitalInOut(board.A2)
pump_fwd.direction = digitalio.Direction.OUTPUT
pump_rev.direction = digitalio.Direction.OUTPUT

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
configuration_topic4 = "homeassistant/switch/plantEnvironmentW/config"
config_payload4 = """{"name": "Plant Water Pump Run",
                   "device_class": "switch",
                   "state_topic": "homeassistant/switch/plantEnvironment/state",
                   "command_topic": "homeassistant/switch/plantEnvironmentW/set",
                   "value_template": "{{value_json.pump_run}}",
                   "qos": 1}"""
configuration_topic5 = "homeassistant/switch/plantEnvironmentWR/config"
config_payload5 = """{"name": "Plant Water Pump Reverse Direction",
                   "device_class": "switch",
                   "state_topic": "homeassistant/switch/plantEnvironment/state",
                   "command_topic": "homeassistant/switch/plantEnvironmentWR/set",
                   "value_template": "{{value_json.pump_reverse}},"
                   "qos": 1}"""
configuration_topic6 = "homeassistant/sensor/plantEnvironmentM/config"
config_payload6 = """{"name": "Plant Moisture",
                   "state_topic": "homeassistant/sensor/plantEnvironment/state",
                   "value_template": "{{value_json.moisture}}"}"""

                    
state_topic = "homeassistant/sensor/plantEnvironment/state"
state_topic2 = "homeassistant/switch/plantEnvironment/state"
command_topic1 = "homeassistant/switch/plantEnvironmentW/set"
command_topic2 = "homeassistant/switch/plantEnvironmentWR/set"


mqtt_client = MQTT.MQTT(
    broker=secrets["broker"],
    port=secrets["port"],
    username=secrets["user"],
    password=secrets["broker_pass"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)


def connect(mqtt_client, userdata, flags, rc):
    print("Connected to MQTT Broker")
    print("Flags: {0}\nRC: {1}".format(flags, rc))
    
def disconnect(mqtt_client, userdata, rc):
    print("Disconnected from broker")
    
def subscribe(mqtt_client, userdata, topic, granted_qos):
    print("Subscribed to topic {0} with QOS level {1}".format(topic, granted_qos))
    
def unsubscribe(mqtt_client, userdata, topic, pid):
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))
    
def publish(mqtt_client, userdata, topic, pid):
    print("Published to {0} with PID {1}".format(topic,pid))
    
def message(client, topic, message):
    global pump_running
    global pump_reverse_direction
    global pump_start_time
    print("New message on topic {0}: {1}".format(topic, message))
    if topic == command_topic1:
        
        if message == "ON":
            pump_running = True
            pump_start_time = time.monotonic()
        elif message == "OFF":
            pump_running = False
            
    if topic == command_topic2:
        if message == "ON":
            pump_reverse_direction = True
        elif message == "OFF":
            pump_reverse_direction = False
            
    update_switch_state()
            
def update_switch_state():
    global pump_running
    global pump_reverse_direction
    pump_run_string = "ON" if pump_running else "OFF"
    pump_dir_string = "ON" if pump_reverse_direction else "OFF"
    mqtt_client.publish(state_topic2,
                        "{\"pump_run\":\"" + pump_run_string + "\",\"pump_reverse\":\"" + pump_dir_string + "\"}")         
    
mqtt_client.connect()

mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish
mqtt_client.on_message = message

mqtt_client.subscribe(command_topic1, qos=1)
mqtt_client.subscribe(command_topic2, qos=1)

mqtt_client.publish(configuration_topic1, config_payload1, retain=True)
mqtt_client.publish(configuration_topic2, config_payload2, retain=True)
mqtt_client.publish(configuration_topic3, config_payload3, retain=True)
mqtt_client.publish(configuration_topic4, config_payload4, retain=True)
mqtt_client.publish(configuration_topic5, config_payload5, retain=True)
mqtt_client.publish(configuration_topic6, config_payload6, retain=True)

while True:
    try:
        mqtt_client.loop()
    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        wifi.reset()
        mqtt_client.reconnect()
        continue
    
    now = time.monotonic()
    if now - last_update_time > update_period:
        mqtt_client.publish(state_topic, "{\"temperature\": %0.1f, \"humidity\": %0.1f, \"pressure\": %0.1f, \"moisture\": %d }" % (float(bme280.temperature*9/5+32), bme280.humidity, bme280.pressure, ss.moisture_read()))
        last_update_time = now
        
    if pump_running:
        if pump_reverse_direction:
            pump_fwd.value = False
            time.sleep(0.1)
            pump_rev.value = True
        else:
            pump_rev.value = False
            time.sleep(0.1)
            pump_fwd.value = True
    else:
        pump_fwd.value = False
        pump_rev.value = False
            
    if now - pump_start_time > pump_max_run_time and pump_running:
        pump_running = False
        update_switch_state()
        
    