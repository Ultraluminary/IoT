import time
from bmp280 import BMP280
from smbus2 import SMBus, i2c_msg
import paho.mqtt.client as mqtt
import wiringpi
import requests

# Create an I2C bus object for BMP280 and BH1750
bus = SMBus(0)

# BMP280 setup
bmp280_address = 0x77
bmp280 = BMP280(i2c_addr=bmp280_address, i2c_dev=bus)
interval = 15  # Sample period in seconds

# BH1750 setup
bh1750_address = 0x23
bus.write_byte(bh1750_address, 0x10)

# MQTT settings
MQTT_HOST = "mqtt3.thingspeak.com"
MQTT_PORT = 1883
MQTT_TOPIC = "channels/2792860/publish"
MQTT_CLIENT_ID = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_USER = "MyEaFQwwEhMCKBMbOCMzKig"
MQTT_PWD = "v6qqZcORL3PNP8i0tGe5vVGe"

# ThingSpeak settings
THINGSPEAK_CHANNEL_ID = "2792860"
THINGSPEAK_READ_API_KEY = "TGE2GK5HIYAA6Z72"
THINGSPEAK_WRITE_API_KEY = "3XUB0WG18QGZ00FM"
FIELD_NUMBER = 4  # Field for temperature goal

# GPIO setup for LED and buttons
wiringpi.wiringPiSetup()
LED_PIN = 2
BUTTON_DEC_PIN = 3  # Wiring 3 -> Physical Pin 8
BUTTON_INC_PIN = 4  # Wiring 4 -> Physical Pin 10
BUTTON_LED_TOGGLE_PIN = 6  # Wiring 6 -> Physical Pin 12

wiringpi.pinMode(LED_PIN, wiringpi.OUTPUT)
wiringpi.pinMode(BUTTON_DEC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_DEC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_INC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_INC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_LED_TOGGLE_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_LED_TOGGLE_PIN, wiringpi.PUD_UP)

# Default values
TEMPERATURE_GOAL = 25
LUX_GOAL = 100
manual_led_status = False

# Button state variables
previous_button_state = {
    BUTTON_DEC_PIN: wiringpi.HIGH,
    BUTTON_INC_PIN: wiringpi.HIGH,
}

# Functions for MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected OK" if rc == 0 else f"Bad connection: {rc}")

def on_disconnect(client, userdata, flags, rc=0):
    print(f"Disconnected: {rc}")

# Function to fetch temperature goal from ThingSpeak
def fetch_temperature_goal():
    api_url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/fields/{FIELD_NUMBER}/last.json"
    params = {'api_key': THINGSPEAK_READ_API_KEY}
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            goal = int(float(data.get(f'field{FIELD_NUMBER}', TEMPERATURE_GOAL)))
            print(f"Fetched Temperature Goal: {goal}")
            return goal
    except Exception as e:
        print(f"Error fetching temperature goal: {e}")
    return TEMPERATURE_GOAL

# Function to send updated temperature goal to ThingSpeak
def update_temperature_goal(new_goal):
    print(f"Updating Temperature Goal to {new_goal} on ThingSpeak...")
    api_url = "https://api.thingspeak.com/update"
    params = {'api_key': THINGSPEAK_WRITE_API_KEY, f'field{FIELD_NUMBER}': new_goal}
    try:
        response = requests.get(api_url, params=params)
        print(f"ThingSpeak Response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            print(f"Temperature Goal updated to {new_goal} on ThingSpeak.")
        else:
            print(f"Failed to update ThingSpeak. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error updating ThingSpeak: {e}")

# Function to get light value from BH1750
def get_light_value(bus, address):
    write = i2c_msg.write(address, [0x10])
    read = i2c_msg.read(address, 2)
    bus.i2c_rdwr(write, read)
    bytes_read = list(read)
    return int((((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2)

# MQTT Client setup
client = mqtt.Client(client_id=MQTT_CLIENT_ID)
client.username_pw_set(MQTT_USER, MQTT_PWD)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.loop_start()
client.connect(MQTT_HOST, MQTT_PORT)

# Main loop
last_publish_time = time.time()

while True:
    # Check button presses
    for pin in [BUTTON_DEC_PIN, BUTTON_INC_PIN]:
        current_state = wiringpi.digitalRead(pin)
        if current_state == wiringpi.LOW and previous_button_state[pin] == wiringpi.HIGH:
            if pin == BUTTON_DEC_PIN:
                TEMPERATURE_GOAL = max(0, TEMPERATURE_GOAL - 1)
                print(f"Button on pin {pin} Pressed! Decreased Temperature Goal to {TEMPERATURE_GOAL}")
            elif pin == BUTTON_INC_PIN:
                TEMPERATURE_GOAL += 1
                print(f"Button on pin {pin} Pressed! Increased Temperature Goal to {TEMPERATURE_GOAL}")

            # Update ThingSpeak immediately
            update_temperature_goal(TEMPERATURE_GOAL)
        previous_button_state[pin] = current_state

    # Publish sensor data every 15 seconds
    if time.time() - last_publish_time >= interval:
        bmp280_temperature = int(bmp280.get_temperature())
        bmp280_pressure = int(bmp280.get_pressure())
        lux = get_light_value(bus, bh1750_address)

        # Control the LED based on lux level
        led_status = 0
        if lux < LUX_GOAL:
            wiringpi.digitalWrite(LED_PIN, wiringpi.HIGH)
            led_status = 1
            print("Low light detected, LED is ON")
        else:
            wiringpi.digitalWrite(LED_PIN, wiringpi.LOW)
            print("Sufficient light, LED is OFF")

        # Print all relevant data
        print(f"Temperature: {bmp280_temperature}°C, Pressure: {bmp280_pressure} hPa, Light: {lux} Lux")
        print(f"Temperature Goal: {TEMPERATURE_GOAL}°C, Lux Goal: {LUX_GOAL}, LED Status: {'ON' if led_status else 'OFF'}")

        # Publish MQTT data
        MQTT_DATA = (f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={lux}&"
                     f"field4={TEMPERATURE_GOAL}&field5={LUX_GOAL}&field6={led_status}&status=MQTTPUBLISH")
        print("Publishing to MQTT:", MQTT_DATA)
        try:
            client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        except OSError:
            client.reconnect()
            print("Reconnecting to MQTT broker...")

        last_publish_time = time.time()

    time.sleep(0.1)  # Small delay for loop stability