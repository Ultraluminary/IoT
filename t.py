import time
from bmp280 import BMP280
from smbus2 import SMBus, i2c_msg
import paho.mqtt.client as mqtt

# Create an I2C bus object for BMP280 and BH1750
bus = SMBus(0)

# BMP280 setup
bmp280_address = 0x77
bmp280 = BMP280(i2c_addr=bmp280_address, i2c_dev=bus)
interval = 15  # Sample period in seconds

# BH1750 setup
bh1750_address = 0x23  # BH1750 I2C address
bus.write_byte(bh1750_address, 0x10)  # Set BH1750 to 1lx resolution mode 120ms

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_TOPIC = "channels/2792860/publish"
MQTT_CLIENT_ID = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_USER = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_PWD = "v6qqZcORL3PNP8i0tGe5vVGe"

# Functions for MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected OK with result code " + str(rc))
    else:
        print("Bad connection with result code " + str(rc))

def on_disconnect(client, userdata, flags, rc=0):
    print("Disconnected result code " + str(rc))

def on_message(client, userdata, msg):
    print("Received a message on topic: " + msg.topic + "; message: " + msg.payload)

# Function to get light value (lux) from BH1750
def get_light_value(bus, address):
    write = i2c_msg.write(address, [0x10])  # 1lx resolution 120ms
    read = i2c_msg.read(address, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return (((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2  # Conversion as per datasheet

# Set up MQTT Client
client = mqtt.Client(client_id=MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.enable_logger()  # Enable logging

# Connect to MQTT broker
print(f"Connecting to {MQTT_HOST}...")
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()  # Start the loop

# Main loop to read sensors and publish data
while True:
    # Measure data from BMP280
    bmp280_temperature = bmp280.get_temperature()
    bmp280_pressure = bmp280.get_pressure()
    
    # Measure light from BH1750
    lux = get_light_value(bus, bh1750_address)
    
    # Print the measured values
    print(f"Temperature: {bmp280_temperature:.1f}, Pressure: {bmp280_pressure:.1f}, Light: {lux:.2f} Lux")
    
    # Create the MQTT data structure
    MQTT_DATA = f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={lux}&status=MQTTPUBLISH"
    print(MQTT_DATA)

    # Publish the data to the MQTT broker
    try:
        client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        time.sleep(interval)
    except OSError:
        client.reconnect()
