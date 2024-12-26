import time
from bmp280 import BMP280
from smbus2 import SMBus, i2c_msg
from datetime import datetime, timedelta
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
LED_PIN = 2  # LED pin
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

# Default values (fallbacks)
TEMPERATURE_GOAL = 25
LUX_GOAL = 100
manual_led_status = False
manual_led_override = False

# Button state variables
previous_button_state = {
    BUTTON_DEC_PIN: wiringpi.HIGH,
    BUTTON_INC_PIN: wiringpi.HIGH,
    BUTTON_LED_TOGGLE_PIN: wiringpi.HIGH,
}

# Functions for MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected OK" if rc == 0 else f"Bad connection: {rc}")

def on_disconnect(client, userdata, flags, rc=0):
    print(f"Disconnected: {rc}")

# Function to fetch the last entry from ThingSpeak
def fetch_last_entry():
    global TEMPERATURE_GOAL, LUX_GOAL
    api_url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
    params = {'api_key': THINGSPEAK_READ_API_KEY}
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            TEMPERATURE_GOAL = int(float(data.get('field4', TEMPERATURE_GOAL)))
            LUX_GOAL = int(float(data.get('field5', LUX_GOAL)))
            raw_timestamp = data.get('created_at', 'Unknown Time')

            # Convert timestamp to local time (GMT+1)
            if raw_timestamp != 'Unknown Time':
                utc_time = datetime.strptime(raw_timestamp, "%Y-%m-%dT%H:%M:%SZ")
                local_time = utc_time + timedelta(hours=1)  # Adjust to GMT+1
                date = local_time.strftime("%Y-%m-%d")
                time = local_time.strftime("%H:%M:%S")
            else:
                date, time = "Unknown Date", "Unknown Time"

            print("==========================================")
            print("Initial Values Fetched from ThingSpeak:")
            print("------------------------------------------")
            print(f"Temperature Goal: {TEMPERATURE_GOAL}°C")
            print(f"Lux Goal: {LUX_GOAL}")
            print(f"Date: {date}")
            print(f"Time: {time}")
            print("==========================================")
        else:
            print(f"Failed to fetch last entry from ThingSpeak. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching last entry: {e}")

# Fetch the last entry from ThingSpeak before starting the main loop
print("Fetching initial values from ThingSpeak...")
fetch_last_entry()

# Function to update temperature goal on ThingSpeak
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
    for pin in [BUTTON_DEC_PIN, BUTTON_INC_PIN, BUTTON_LED_TOGGLE_PIN]:
        current_state = wiringpi.digitalRead(pin)
        if current_state == wiringpi.LOW and previous_button_state[pin] == wiringpi.HIGH:
            if pin == BUTTON_DEC_PIN:
                TEMPERATURE_GOAL = max(0, TEMPERATURE_GOAL - 1)
                print(f"Button on pin {pin} Pressed! Decreased Temperature Goal to {TEMPERATURE_GOAL}")
                update_temperature_goal(TEMPERATURE_GOAL)
            elif pin == BUTTON_INC_PIN:
                TEMPERATURE_GOAL += 1
                print(f"Button on pin {pin} Pressed! Increased Temperature Goal to {TEMPERATURE_GOAL}")
                update_temperature_goal(TEMPERATURE_GOAL)
            elif pin == BUTTON_LED_TOGGLE_PIN:
                manual_led_override = not manual_led_override
                manual_led_status = not manual_led_status
                wiringpi.digitalWrite(LED_PIN, wiringpi.HIGH if manual_led_status else wiringpi.LOW)
                print(f"Manual LED Toggle: {'ON' if manual_led_status else 'OFF'}")

        previous_button_state[pin] = current_state

    # Publish sensor data every 15 seconds
    if time.time() - last_publish_time >= interval:
        bmp280_temperature = int(bmp280.get_temperature())
        bmp280_pressure = int(bmp280.get_pressure())
        lux = get_light_value(bus, bh1750_address)

        # Control the LED based on lux level (only if not manually overridden)
        if not manual_led_override:
            if lux < LUX_GOAL:
                wiringpi.digitalWrite(LED_PIN, wiringpi.HIGH)
                manual_led_status = True
                print("Low light detected, LED is ON")
            else:
                wiringpi.digitalWrite(LED_PIN, wiringpi.LOW)
                manual_led_status = False
                print("Sufficient light, LED is OFF")

        # Print all relevant data
        print(f"Temperature: {bmp280_temperature}°C, Pressure: {bmp280_pressure} hPa, Light: {lux} Lux")
        print(f"Temperature Goal: {TEMPERATURE_GOAL}°C, Lux Goal: {LUX_GOAL}, LED Status: {'ON' if manual_led_status else 'OFF'}")

        # Publish MQTT data
        MQTT_DATA = (f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={lux}&"
                     f"field4={TEMPERATURE_GOAL}&field5={LUX_GOAL}&field6={1 if manual_led_status else 0}&status=MQTTPUBLISH")
        print("Publishing to MQTT:", MQTT_DATA)
        try:
            client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        except OSError:
            client.reconnect()
            print("Reconnecting to MQTT broker...")

        last_publish_time = time.time()

    time.sleep(0.1)  # Small delay for loop stability

    #Working code 
    #light auto werkt bij low light
    #turn on/off auto light werkt
    #enkel is de plus en min gebonden aan temperature goal