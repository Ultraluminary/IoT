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

# Setup LED pin for software PWM
wiringpi.pinMode(LED_PIN, wiringpi.OUTPUT)
wiringpi.softPwmCreate(LED_PIN, 0, 100)  # Initialize PWM with range 0-100

wiringpi.pinMode(BUTTON_DEC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_DEC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_INC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_INC_PIN, wiringpi.PUD_UP)

# Default values (fallbacks)
LUX_GOAL = 0  # Start with LED OFF
led_brightness = 0  # PWM brightness (range: 0 to 100)

# Step sizes for brightness
BRIGHTNESS_STEP = 20  # Step size for LED brightness (0-100 scale)

# Button state variables
previous_button_state = {
    BUTTON_DEC_PIN: wiringpi.HIGH,
    BUTTON_INC_PIN: wiringpi.HIGH,
}

# Flags to control messages
led_out_message_shown = False  # For "LED is out" message
led_max_message_shown = False  # For "LED is at maximum brightness" message

# Functions for MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected OK" if rc == 0 else f"Bad connection: {rc}")

def on_disconnect(client, userdata, flags, rc=0):
    print(f"Disconnected: {rc}")

# Function to fetch the last entry from ThingSpeak
def fetch_last_entry():
    global LUX_GOAL, led_brightness
    api_url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds/last.json"
    params = {'api_key': THINGSPEAK_READ_API_KEY}
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            LUX_GOAL = int(float(data.get('field5', LUX_GOAL)))
            led_brightness = int((LUX_GOAL / 1000) * 100)  # Scale to PWM range
            wiringpi.softPwmWrite(LED_PIN, led_brightness)  # Set initial LED brightness
            lux = int(data.get('field3', 0))
            temperature = int(data.get('field1', 0))
            print("==========================================")
            print("Initial Values Fetched from ThingSpeak:")
            print("------------------------------------------")
            print(f"Temperature: {temperature}°C")
            print(f"Lux: {lux} Lux")
            print(f"Lux Goal: {LUX_GOAL}")
            print(f"LED Brightness: {led_brightness}")
            print("==========================================")
        else:
            print(f"Failed to fetch last entry from ThingSpeak. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching last entry: {e}")

# Fetch the last entry from ThingSpeak before starting the main loop
print("Fetching initial values from ThingSpeak...")
fetch_last_entry()

# Function to update lux goal on ThingSpeak
def update_lux_goal(new_goal):
    print(f"Updating Lux Goal to {new_goal} on ThingSpeak...")
    api_url = "https://api.thingspeak.com/update"
    params = {'api_key': THINGSPEAK_WRITE_API_KEY, 'field5': new_goal}
    try:
        response = requests.get(api_url, params=params)
        print(f"ThingSpeak Response: {response.status_code} - {response.text}")
        if response.status_code == 200:
            print(f"Lux Goal updated to {new_goal} on ThingSpeak.")
        else:
            print(f"Failed to update ThingSpeak. Status code: {response.status_code}")
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
client = mqtt.Client(client_id=MQTT_CLIENT_ID, protocol=mqtt.MQTTv311)  # Specify protocol to avoid deprecation warning
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
                if led_brightness == 0:
                    print("The LED is already out, you can't lower it anymore.")
                else:
                    led_brightness = max(0, led_brightness - BRIGHTNESS_STEP)
                    LUX_GOAL = int((led_brightness / 100) * 1000)  # Scale lux goal
                    print(f"Button on pin {pin} Pressed! Decreased Brightness to {led_brightness}, Lux Goal to {LUX_GOAL}")
                    update_lux_goal(LUX_GOAL)
                    led_out_message_shown = False  # Reset the flag
                    led_max_message_shown = False  # Reset the flag
            elif pin == BUTTON_INC_PIN:
                if led_brightness < 100:
                    led_brightness = min(100, led_brightness + BRIGHTNESS_STEP)
                    LUX_GOAL = int((led_brightness / 100) * 1000)  # Scale lux goal
                    print(f"Button on pin {pin} Pressed! Increased Brightness to {led_brightness}, Lux Goal to {LUX_GOAL}")
                    update_lux_goal(LUX_GOAL)
                    led_out_message_shown = False  # Reset the flag
                    led_max_message_shown = False  # Reset the flag
                else:
                    print("The LED is at maximum brightness, you can't increase it further.")

            # Apply the updated brightness to the LED
            wiringpi.softPwmWrite(LED_PIN, led_brightness)

        previous_button_state[pin] = current_state

    # LED state check for logging
    if led_brightness == 0 and LUX_GOAL == 0:
        if not led_out_message_shown:  # Only display the message if it hasn't been shown already
            print("The LED is out.")
            led_out_message_shown = True
    elif led_brightness == 100:
        if not led_max_message_shown:  # Only display the message if it hasn't been shown already
            print("The LED is at maximum brightness.")
            led_max_message_shown = True
    else:
        led_out_message_shown = False  # Reset the flag when LED is no longer off
        led_max_message_shown = False  # Reset the flag when LED is no longer max

    # Publish sensor data every 15 seconds
    if time.time() - last_publish_time >= interval:
        bmp280_temperature = int(bmp280.get_temperature())
        bmp280_pressure = int(bmp280.get_pressure())
        lux = get_light_value(bus, bh1750_address)

        # Print all relevant data
        print(f"Temperature: {bmp280_temperature}°C, Pressure: {bmp280_pressure} hPa, Light: {lux} Lux")
        print(f"Lux Goal: {LUX_GOAL}, LED Brightness: {led_brightness}")

        # Publish MQTT data
        MQTT_DATA = (f"field1={bmp280_temperature}&field2={bmp280_pressure}&field3={lux}&"
                     f"field4=0&field5={LUX_GOAL}&field6={led_brightness}&status=MQTTPUBLISH")
        print("Publishing to MQTT:", MQTT_DATA)
        try:
            client.publish(MQTT_TOPIC, payload=MQTT_DATA, qos=0, retain=False)
        except OSError:
            client.reconnect()
            print("Reconnecting to MQTT broker...")

        last_publish_time = time.time()

    time.sleep(0.1)  # Small delay for loop stability

    #we zijn er bijna