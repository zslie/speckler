import board
import digitalio
import neopixel
import sys
import time

# Onboard NeoPixel Setup
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 0.2  # Keep it dim so it's not blinding

# Pin Configuration
laser = digitalio.DigitalInOut(board.A0)
laser.direction = digitalio.Direction.OUTPUT

camera_strobe = digitalio.DigitalInOut(board.A1)
camera_strobe.direction = digitalio.Direction.OUTPUT

# Startup Visual Check: Flash Green 3 times to prove code is running
for _ in range(3):
    pixel[0] = (0, 255, 0)  # Green
    time.sleep(0.15)
    pixel[0] = (0, 0, 0)    # Off
    time.sleep(0.15)

# Blue = Waiting for commands
pixel[0] = (0, 0, 255)

print("RP2040_READY")
while True: 
    laser.value = True
    pixel[0] = (255, 0, 0)  # Turn NeoPixel RED when laser is firing