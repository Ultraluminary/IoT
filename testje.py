import smbus2

bus = smbus2.SMBus(1)

def test_device(address):
    try:
        bus.write_byte(address, 0x01)  # Attempt a write
        print(f"Device at 0x{address:02X} is responding!")
    except Exception as e:
        print(f"Error communicating with device at 0x{address:02X}: {e}")

# Test BH1750
test_device(0x23)

# Test BMP280
test_device(0x77)