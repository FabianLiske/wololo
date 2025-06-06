import time

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

serial = i2c(port=1, address=0x3C)

device = sh1106(serial, width=128, height=64)

fontBig = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 20)
fontSmall = ImageFont.truetype("fonts/DejaVuSansMono.ttf", 14)

with canvas(device) as draw:
    draw.text((0, 6), "Grüzi", font=fontBig, fill="white")