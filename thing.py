import time
from bmp280 import BMP280
from smbus2 import SMBus
import paho.mqtt.client as mqtt

# Create an I2C bus object
bus = SMBus(0)
address = 0x77

# Setup BMP280
bmp280 = BMP280(i2c_addr=address, i2c_dev=bus)
interval = 15  # Sample period in seconds

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_TOPIC = "channels/2792860/publish"
MQTT_CLIENT_ID = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_USER = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_PWD = "v6qqZcORL3PNP8i0tGe5vVGe"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected OK with result code " + str(rc))
    else:
        print("Bad connection with result code " + str(rc))

def on_disconnect(client, userdata, flags, rc=0):
    print("Disconnected result code " + str(rc))

def on_message(client, userdata, msg):
    print("Received a message on topic: " + msg.topic + "; message: " + msg.payload)

# Set up MQTT Client
client = mqtt.Client(client_id=MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.enable_logger()  # Enable logging

print(f"Connecting to {MQTT_HOST}...")
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()  # Start the loop

while True:
    # Measure data
    bmp280_temperature = bmp280.get_temperature()
    bmp280_pressure = bmp280.get_pressure()
    print(f"Temperature: {bmp280_temperature:.1f}, Pressure: {bmp280_pressure:.1f}")
    
    # Create the JSON data structure
    MQTT_DATA = f"field1={bmp280_temperature}&field2={bmp280_pressure}&status=MQTTPUBLISH"
    print(MQTT_DATA)

    try:
        client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        time.sleep(interval)
    except OSError:
        client.reconnect()
