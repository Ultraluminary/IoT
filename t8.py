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

# GPIO setup for LED and buttons
wiringpi.wiringPiSetup()
LED_PIN = 2  # LED pin for PWM
BUTTON_DEC_PIN = 3  # Wiring 3 -> Physical Pin 8
BUTTON_INC_PIN = 4  # Wiring 4 -> Physical Pin 10
BUTTON_TOGGLE_PIN = 6  # Wiring 6 -> Physical Pin 12

# Setup LED pin for software PWM
wiringpi.pinMode(LED_PIN, wiringpi.OUTPUT)
wiringpi.softPwmCreate(LED_PIN, 0, 100)  # Initialize PWM with range 0-100

wiringpi.pinMode(BUTTON_DEC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_DEC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_INC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_INC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_TOGGLE_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_TOGGLE_PIN, wiringpi.PUD_UP)

# Default values
LED_LUX_GOAL = 100
led_brightness = 50  # PWM brightness (range: 0 to 100)
manual_override = False  # Manual override state
previous_led_state = None  # Track the LED state for messages
Light_room_threshold = 40  # Lux threshold for automatic LED control

# Step sizes for brightness
BRIGHTNESS_STEP = 20  # Step size for LED brightness (0-100 scale)

# Initialize button states
previous_button_state = {
    BUTTON_DEC_PIN: wiringpi.digitalRead(BUTTON_DEC_PIN),
    BUTTON_INC_PIN: wiringpi.digitalRead(BUTTON_INC_PIN),
    BUTTON_TOGGLE_PIN: wiringpi.digitalRead(BUTTON_TOGGLE_PIN),
}

# Functions for MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected OK" if rc == 0 else f"Bad connection: {rc}")

def on_disconnect(client, userdata, flags, rc=0):
    print(f"Disconnected: {rc}")

# Function to fetch the last entry from ThingSpeak
def fetch_last_entry():
    global LED_LUX_GOAL, led_brightness
    api_url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
    params = {'api_key': THINGSPEAK_READ_API_KEY}
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            LED_LUX_GOAL = int(float(data.get('field5', LED_LUX_GOAL)))
            led_brightness = int((LED_LUX_GOAL / 1000) * 100)  # Scale to PWM range
            wiringpi.softPwmWrite(LED_PIN, led_brightness)  # Set initial LED brightness

            light_in_room = int(data.get('field3', 0))
            temperature = int(data.get('field1', 0))
            raw_timestamp = data.get('created_at', 'Unknown Time')

            if raw_timestamp != 'Unknown Time':
                utc_time = datetime.strptime(raw_timestamp, "%Y-%m-%dT%H:%M:%SZ")
                local_time = utc_time + timedelta(hours=1)
                date = local_time.strftime("%Y-%m-%d")
                time = local_time.strftime("%H:%M:%S")
            else:
                date, time = "Unknown Date", "Unknown Time"

            print("==========================================")
            print("Initial Values Fetched from ThingSpeak:")
            print("------------------------------------------")
            print(f"Temperature: {temperature}°C")
            print(f"Light in the room: {light_in_room}")
            print(f"LED Lux Goal: {LED_LUX_GOAL}")
            print(f"LED Brightness: {led_brightness}")
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

# Function to update LED lux goal on ThingSpeak
def update_led_lux_goal(new_goal):
    print(f"Updating LED Lux Goal to {new_goal} on ThingSpeak...")
    api_url = "https://api.thingspeak.com/update"
    params = {'api_key': THINGSPEAK_WRITE_API_KEY, 'field5': new_goal}
    try:
        response = requests.get(api_url, params=params)
        print(f"ThingSpeak Response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            print(f"LED Lux Goal updated to {new_goal} on ThingSpeak.")
    except Exception as e:
        print(f"Error updating ThingSpeak: {e}")

# Function to get light value from BH1750
def get_light_value(bus, address):
    try:
        write = i2c_msg.write(address, [0x10])
        read = i2c_msg.read(address, 2)
        bus.i2c_rdwr(write, read)
        bytes_read = list(read)
        return int((((bytes_read[0] & 3) << 8) + bytes_read[1]) / 1.2)
    except Exception as e:
        print(f"Error reading light value: {e}")
        return 0

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
    # Measure the light intensity
    light_in_room = get_light_value(bus, bh1750_address)

    # Check button presses
    for pin in [BUTTON_DEC_PIN, BUTTON_INC_PIN, BUTTON_TOGGLE_PIN]:
        current_state = wiringpi.digitalRead(pin)
        if current_state == wiringpi.LOW and previous_button_state[pin] == wiringpi.HIGH:
            if pin == BUTTON_DEC_PIN and manual_override:
                if led_brightness > 0:
                    led_brightness = max(0, led_brightness - BRIGHTNESS_STEP)
                    LED_LUX_GOAL = int((led_brightness / 100) * 1000)
                    wiringpi.softPwmWrite(LED_PIN, led_brightness)
                    print(f"Brightness decreased to {led_brightness}%, LED Lux Goal: {LED_LUX_GOAL}")
            elif pin == BUTTON_INC_PIN and manual_override:
                if led_brightness < 100:
                    led_brightness = min(100, led_brightness + BRIGHTNESS_STEP)
                    LED_LUX_GOAL = int((led_brightness / 100) * 1000)
                    wiringpi.softPwmWrite(LED_PIN, led_brightness)
                    print(f"Brightness increased to {led_brightness}%, LED Lux Goal: {LED_LUX_GOAL}")
            elif pin == BUTTON_TOGGLE_PIN:
                manual_override = not manual_override
                if manual_override:
                    wiringpi.softPwmWrite(LED_PIN, 0)
                    print("Manual override enabled. LED is OFF.")
                else:
                    wiringpi.softPwmWrite(LED_PIN, led_brightness)
                    print("Automatic LED control resumed.")
        previous_button_state[pin] = current_state

    # Automatic LED control
    if not manual_override:
        led_state = "ON" if light_in_room < Light_room_threshold else "OFF"
        if led_state != previous_led_state:
            print(f"Light in the room: {light_in_room}, LED is {led_state}.")
            wiringpi.softPwmWrite(LED_PIN, 100 if led_state == "ON" else 0)
        previous_led_state = led_state

    # Publish sensor data every 15 seconds
    if time.time() - last_publish_time >= interval:
        bmp280_temperature = int(bmp280.get_temperature())
        bmp280_pressure = int(bmp280.get_pressure())

        print("==========================================")
        print("Sending current measured data to ThingSpeak...")
        print("------------------------------------------")
        print(f"Temperature: {bmp280_temperature}°C")
        print(f"Pressure: {bmp280_pressure} hPa")
        print(f"Light in the room: {light_in_room}")
        print(f"LED Lux Goal: {LED_LUX_GOAL}")
        print(f"LED Brightness: {led_brightness}")
        print("==========================================")

        MQTT_DATA = (f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={light_in_room}&"
                     f"field5={LED_LUX_GOAL}&field6={1 if led_brightness > 0 else 0}&status=MQTTPUBLISH")
        try:
            client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        except OSError:
            client.reconnect()
            print("Reconnecting to MQTT broker...")

        last_publish_time = time.time()

    time.sleep(0.1)
    #werkt niet