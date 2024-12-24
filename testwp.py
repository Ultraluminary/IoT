import wiringpi as wp
import time

# I2C setup
BH1750_ADDR = 0x23  # Detected address for BH1750
BMP280_ADDR = 0x77  # Detected address for BMP280

# BH1750 Commands
CMD_POWER_ON = 0x01
CMD_CONT_HIGH_RES = 0x10

# Initialize I2C devices
bh1750 = wp.wiringPiI2CSetup(BH1750_ADDR)
bmp280 = wp.wiringPiI2CSetup(BMP280_ADDR)

if bh1750 == -1 or bmp280 == -1:
    print("Failed to initialize I2C devices")
    exit(1)

# Initialize BH1750
def init_bh1750():
    try:
        wp.wiringPiI2CWrite(bh1750, CMD_POWER_ON)  # Power On
        time.sleep(0.5)
        print("BH1750 initialized successfully!")
    except Exception as e:
        print(f"Error initializing BH1750: {e}")

# Read light intensity from BH1750
def read_bh1750():
    try:
        wp.wiringPiI2CWrite(bh1750, CMD_CONT_HIGH_RES)  # High-resolution mode
        time.sleep(0.2)
        high_byte = wp.wiringPiI2CRead(bh1750)  # Read high byte
        low_byte = wp.wiringPiI2CRead(bh1750)   # Read low byte
        if high_byte == -1 or low_byte == -1:
            raise IOError("Failed to read BH1750 data")
        lux = (high_byte << 8 | low_byte) / 1.2
        return lux
    except Exception as e:
        print(f"Error reading BH1750: {e}")
        return None

# Initialize BMP280
def init_bmp280():
    try:
        wp.wiringPiI2CWriteReg8(bmp280, 0xF4, 0x27)  # Set normal mode
        wp.wiringPiI2CWriteReg8(bmp280, 0xF5, 0xA0)  # Set config
        print("BMP280 initialized successfully!")
    except Exception as e:
        print(f"Error initializing BMP280: {e}")

# Read temperature and pressure from BMP280
def read_bmp280():
    try:
        # Read raw temperature and pressure data
        data = [wp.wiringPiI2CReadReg8(bmp280, reg) for reg in range(0xF7, 0xF7 + 6)]
        if -1 in data:
            raise IOError("Failed to read BMP280 data")
        raw_pressure = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

        # Simplified conversion (not fully calibrated)
        temp = raw_temp / 16384.0
        pressure = raw_pressure / 256.0
        return temp, pressure
    except Exception as e:
        print(f"Error reading BMP280: {e}")
        return None, None

# Main loop
init_bh1750()
init_bmp280()

while True:
    # Read BH1750
    lux = read_bh1750()
    if lux is not None:
        print(f"Light Intensity: {lux:.2f} lux")

    # Read BMP280
    temp, pressure = read_bmp280()
    if temp is not None and pressure is not None:
        print(f"Temperature: {temp:.2f} °C, Pressure: {pressure:.2f} Pa")

    time.sleep(2)  # Delay between readings
