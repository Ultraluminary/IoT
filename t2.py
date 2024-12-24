import time
from bmp280 import BMP280
from smbus2 import SMBus, i2c_msg  # Import i2c_msg from smbus2
import paho.mqtt.client as mqtt
import wiringpi  # Use wiringpi for Orange Pi GPIO control
import requests  # To fetch goal values from ThingSpeak

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

# ThingSpeak settings for reading temperature goal
THINGSPEAK_CHANNEL_ID = "2792860"
THINGSPEAK_GOAL_FIELD = "6"  # Replace with the field number for the LED status
THINGSPEAK_READ_API_KEY = "TGE2GK5HIYAA6Z72"  # Replace with your channel's read API key

# GPIO setup for the LED using wiringpi
wiringpi.wiringPiSetup()  # Initialize wiringpi
LED_PIN = 2  # Example GPIO pin for the LED (change according to your wiring)
wiringpi.pinMode(LED_PIN, wiringpi.OUTPUT)  # Set LED pin as output

# Default goal values
TEMPERATURE_GOAL = 25  # Default temperature goal in Celsius
LUX_GOAL = 100  # Default lux goal

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
    return int((((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2)  # Conversion as per datasheet, rounded to int

# Function to fetch temperature goal from ThingSpeak
def fetch_temperature_goal():
    api_url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/4/last.json"  # Field 4 for temperature goal
    params = {'api_key': THINGSPEAK_READ_API_KEY}
    
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            goal = int(float(data.get('field4', TEMPERATURE_GOAL)))
            print(f"Fetched Temperature Goal: {goal}")
            return goal
    except Exception as e:
        print(f"Error fetching temperature goal: {e}")
    
    return TEMPERATURE_GOAL  # Fallback to default goal

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
    bmp280_temperature = int(bmp280.get_temperature())  # Convert to integer
    bmp280_pressure = int(bmp280.get_pressure())        # Convert to integer
    
    # Measure light from BH1750
    lux = get_light_value(bus, bh1750_address)          # Already an integer
    
    # Fetch updated temperature goal
    TEMPERATURE_GOAL = fetch_temperature_goal()         # Already an integer
    
    # Control the LED based on lux level relative to the goal
    led_status = 0  # Default OFF
    if lux < LUX_GOAL:  # If lux is below the goal
        wiringpi.digitalWrite(LED_PIN, wiringpi.HIGH)  # Turn on LED
        led_status = 1  # ON
        print("Low light detected, LED is ON")
    else:
        wiringpi.digitalWrite(LED_PIN, wiringpi.LOW)   # Turn off LED
        print("Sufficient light, LED is OFF")
    
    # Print the measured values to terminal
    print(f"Temperature: {bmp280_temperature}°C, Pressure: {bmp280_pressure} hPa, Light: {lux} Lux")
    print(f"Temperature Goal: {TEMPERATURE_GOAL}°C, Lux Goal: {LUX_GOAL}")
    
    # Create the MQTT data structure
    MQTT_DATA = (f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={lux}&"
                 f"field4={TEMPERATURE_GOAL}&field5={LUX_GOAL}&field6={led_status}&status=MQTTPUBLISH")
    print("Publishing to MQTT:", MQTT_DATA)

    # Publish the data to the MQTT broker
    try:
        client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        time.sleep(interval)
    except OSError:
        client.reconnect()
        print("Reconnecting to MQTT broker...")

# Cleanup GPIO when exiting
wiringpi.digitalWrite(LED_PIN, wiringpi.LOW)  # Ensure LED is off when exiting