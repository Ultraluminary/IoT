import time
import wiringpi
import requests

# GPIO setup for buttons
wiringpi.wiringPiSetup()
BUTTON_DEC_PIN = 3  # Wiring 3 -> Physical Pin 8
BUTTON_INC_PIN = 4  # Wiring 4 -> Physical Pin 10
BUTTON_LED_TOGGLE_PIN = 6  # Wiring 6 -> Physical Pin 12

wiringpi.pinMode(BUTTON_DEC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_DEC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_INC_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_INC_PIN, wiringpi.PUD_UP)
wiringpi.pinMode(BUTTON_LED_TOGGLE_PIN, wiringpi.INPUT)
wiringpi.pullUpDnControl(BUTTON_LED_TOGGLE_PIN, wiringpi.PUD_UP)

# ThingSpeak settings
THINGSPEAK_WRITE_API_KEY = "3XUB0WG18QGZ00FM"  # Replace with the actual API key from `p4`
FIELD_NUMBER = 4  # Assuming temperature goal is in field4
TEMPERATURE_GOAL = 25  # Default value

# Button state variables
previous_button_state = {
    BUTTON_DEC_PIN: wiringpi.HIGH,
    BUTTON_INC_PIN: wiringpi.HIGH,
}

def update_temperature_goal(new_goal):
    """
    Update temperature goal on ThingSpeak.
    """
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

# Main loop
while True:
    for pin, action in [
        (BUTTON_DEC_PIN, lambda: update_temperature_goal(max(0, TEMPERATURE_GOAL - 1))),
        (BUTTON_INC_PIN, lambda: update_temperature_goal(TEMPERATURE_GOAL + 1)),
    ]:
        current_state = wiringpi.digitalRead(pin)
        if current_state == wiringpi.LOW and previous_button_state[pin] == wiringpi.HIGH:
            print(f"Button on pin {pin} Pressed!")
            if pin == BUTTON_DEC_PIN:
                TEMPERATURE_GOAL = max(0, TEMPERATURE_GOAL - 1)
                print(f"Decreased Temperature Goal to {TEMPERATURE_GOAL}")
            elif pin == BUTTON_INC_PIN:
                TEMPERATURE_GOAL += 1
                print(f"Increased Temperature Goal to {TEMPERATURE_GOAL}")
            action()
        previous_button_state[pin] = current_state

    time.sleep(0.1)  # Small delay to prevent excessive looping