import smbus2
import time

# I2C setup
bus = smbus2.SMBus(1)

# I2C addresses
BH1750_ADDR = 0x30  # Detected address for BH1750
BMP280_ADDR = 0x76  # Detected address for BMP280

# BH1750 Commands
CMD_POWER_ON = 0x01
CMD_CONT_HIGH_RES = 0x10

# Initialize BH1750
def init_bh1750():
    try:
        bus.write_byte(BH1750_ADDR, CMD_POWER_ON)  # Power On
        time.sleep(0.5)
        print("BH1750 initialized successfully!")
    except Exception as e:
        print(f"Error initializing BH1750: {e}")

# Read light intensity from BH1750
def read_bh1750():
    try:
        bus.write_byte(BH1750_ADDR, CMD_CONT_HIGH_RES)  # High-resolution mode
        time.sleep(0.2)
        data = bus.read_i2c_block_data(BH1750_ADDR, CMD_CONT_HIGH_RES, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return lux
    except Exception as e:
        print(f"Error reading BH1750: {e}")
        return None

# Initialize BMP280
def init_bmp280():
    try:
        bus.write_byte_data(BMP280_ADDR, 0xF4, 0x27)  # Set normal mode
        bus.write_byte_data(BMP280_ADDR, 0xF5, 0xA0)  # Set config
        print("BMP280 initialized successfully!")
    except Exception as e:
        print(f"Error initializing BMP280: {e}")

# Read temperature and pressure from BMP280
def read_bmp280():
    try:
        # Read raw temperature and pressure data
        data = bus.read_i2c_block_data(BMP280_ADDR, 0xF7, 6)
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