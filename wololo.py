import time

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import RPi.GPIO as GPIO

# Display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64)
fontBig = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 20)
fontSmall = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 14)

# Rotary Encoder
ENCODER_PIN_A = 17     # GPIO17 (Pin 11)
ENCODER_PIN_B = 27     # GPIO27 (Pin 13)
ENCODER_BTN   = 22     # GPIO22 (Pin 15)

GPIO.setmode(GPIO.BCM)
GPIO.setup(ENCODER_PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENCODER_PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENCODER_BTN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def show_message(line1, line2=""):
    with canvas(device) as draw:
        draw.text((0, 6), line1, font=fontBig, fill="white")
        draw.text((0, 30), line2, font=fontSmall, fill="white")

last_state_a = GPIO.input(ENCODER_PIN_A)
last_state_b = GPIO.input(ENCODER_PIN_B)

def encoder_rotated(channel):
    global last_state_a, last_state_b
    a = GPIO.input(ENCODER_PIN_A)
    b = GPIO.input(ENCODER_PIN_B)
    direction = None
    if a != last_state_a:  # A changed
        if a == b:
            direction = "Dreh: CW"
        else:
            direction = "Dreh: CCW"
    elif b != last_state_b:  # B changed
        if a != b:
            direction = "Dreh: CW"
        else:
            direction = "Dreh: CCW"
    last_state_a, last_state_b = a, b
    if direction:
        show_message(direction)


def encoder_pressed(channel):
    show_message("Knopf gedrückt")

GPIO.add_event_detect(ENCODER_PIN_A, GPIO.BOTH, callback=encoder_rotated, bouncetime=50)
GPIO.add_event_detect(ENCODER_PIN_B, GPIO.BOTH, callback=encoder_rotated, bouncetime=50)
GPIO.add_event_detect(ENCODER_BTN, GPIO.FALLING, callback=encoder_pressed, bouncetime=200)

def main():
    try:
        show_message("Bereit...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        GPIO.cleanup()
        show_message("Beende...")
        time.sleep(1)
        device.clear()

if __name__ == "__main__":
    main()