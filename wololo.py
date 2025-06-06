import time

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from gpiozero import RotaryEncoder, Button

# Display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64)
fontBig = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 20)
fontSmall = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 14)

# Rotary Encoder
ENCODER_PIN_A = 17     # GPIO17 (Pin 11)
ENCODER_PIN_B = 27     # GPIO27 (Pin 13)
ENCODER_BTN   = 22     # GPIO22 (Pin 15)

encoder = RotaryEncoder(ENCODER_PIN_A, ENCODER_PIN_B, max_steps=0)
button = Button(ENCODER_BTN, pull_up=True)
last_step = 0

def show_message(line1, line2=""):
    with canvas(device) as draw:
        draw.text((0, 6), line1, font=fontBig, fill="white")
        draw.text((0, 30), line2, font=fontSmall, fill="white")

def on_rotate():
    global last_step
    current = encoder.steps
    if current > last_step:
        direction = "Dreh: CW"
    elif current < last_step:
        direction = "Dreh: CCW"
    else:
        return
    last_step = current
    show_message(direction)


def on_button():
    show_message("Knopf gedrückt")

encoder.when_rotated = on_rotate
button.when_pressed = on_button

def main():
    try:
        show_message("Bereit...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        encoder.close()
        button.close()
        show_message("Beende...")
        time.sleep(1)
        device.clear()

if __name__ == "__main__":
    main()