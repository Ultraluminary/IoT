import time
from bmp280 import BMP280
from smbus2 import SMBus, i2c_msg  # Import i2c_msg from smbus2
import paho.mqtt.client as mqtt
import requests  # For HTTP requests to ThingSpeak
import wiringpi  # Use wiringpi for Orange Pi GPIO control

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

# GPIO setup for the LED using wiringpi
wiringpi.wiringPiSetup()  # Initialize wiringpi
LED_PIN = 2  # Example GPIO pin for the LED (change according to your wiring)
wiringpi.pinMode(LED_PIN, wiringpi.OUTPUT)  # Set LED pin as output

# ThingSpeak settings for LED control
THINGSPEAK_CHANNEL_ID = "2792860"  # Replace with your channel ID
THINGSPEAK_API_KEY = "TGE2GK5HIYAA6Z72"  # Replace with your Read API Key
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/1.json"

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

# Function to read LED state from ThingSpeak
def get_led_state():
    try:
        response = requests.get(f"{THINGSPEAK_URL}?api_key={THINGSPEAK_API_KEY}&results=1")
        if response.status_code == 200:
            data = response.json()
            feeds = data.get("feeds", [])
            if feeds:
                # Parse the latest field value
                return int(feeds[-1]["field1"])  # 1 for ON, 0 for OFF
    except Exception as e:
        print(f"Error reading from ThingSpeak: {e}")
    return None

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

# Light threshold for turning the LED on or off
LUX_THRESHOLD = 50  # Adjust this value based on your needs

# Main loop to read sensors and control the LED
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

    # Read LED state from ThingSpeak
    led_state = get_led_state()
    if led_state is not None:
        wiringpi.digitalWrite(LED_PIN, wiringpi.HIGH if led_state == 1 else wiringpi.LOW)
        print(f"LED state updated from ThingSpeak: {'ON' if led_state == 1 else 'OFF'}")

# Cleanup GPIO when exiting
wiringpi.digitalWrite(LED_PIN, wiringpi.LOW)  # Ensure LED is off when exiting
