import time
import json
import sys
import re
import ipaddress

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from gpiozero import RotaryEncoder, Button

def validate_config(config):
    # Check if config reads as dict
    if not isinstance(config, dict):
        return False, "Config is not a dict"

    # Check if section "hosts" is present and a dict
    hosts = config.get("hosts")
    if hosts is None:
        return False, "'hosts' is missing"
    if not isinstance(hosts, dict):
        return False, "'hosts' is not a dict"
    
    # Define regex for MAC address
    # MAC Address: XX:XX:XX:XX:XX:XX in hexadecimal, allow for uppercase and lowercacse
    # 5 x (2 x (0-9, A-F, a-f) + :) + 2 x (0-9, A-F, a-f)
    mac_regex = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')

    # Check individual hosts
    for key, val in hosts.items():

        # Check if host-entry reads as dict
        if not isinstance(val, dict):
            return False, f"Host '{key}' is not a dict"

        # Check if hostname is present and a string
        host_name = val.get("host")
        if not host_name:
            return False, f"hostname missing for '{key}'"
        if not isinstance(host_name, str):
            return False, f"hostname for '{key}' is not a string"

        # Check if MAC address is present, is a string, and has the correct format
        mac = val.get("mac")
        if not mac:
            return False, f"MAC address missing for '{key}'"
        if not isinstance(mac, str):
            return False, f"MAC address for '{key}' is not a string"
        if not mac_regex.match(mac):
            return False, f"MAC address for '{key}' has the wrong format"
        
        # Check if IP address is present, is a string, and has the correct format
        ip = val.get("ip")
        if not ip:
            return False, f"IP address missing for '{key}'"
        if not isinstance(ip, str):
            return False, f"IP address for '{key}' is not a string"
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return False, f"IP address for '{key}' is invalid"

    # Check if section "sequences" is present and a list with entries
    sequences = config.get("sequences")
    if sequences is None:
        return False, "'sequences' is missing"
    if not isinstance(sequences, list):
        return False, "'sequences' is not an array"
    if not sequences:
        return False, "'sequences' is empty"
    

    # Check individual sequences
    for idx, seq in enumerate(sequences):
        # Check if sequence is a dict
        if not isinstance(seq, dict):
            return False, f"Sequence #{idx} is not a dict"
        
        # Check for title
        title = seq.get("title")
        if not title:
            return False, f"Title for sequence #{idx} is missing"
        if not isinstance(title, str):
            return False, f"Title for sequence #{idx} is not a string"

        # Check targets-arrays
        targets = seq.get("targets")
        if targets is None:
            return False, f"Targets for sequence #{idx} are missing"
        if not isinstance(targets, list):
            return False, f"Targets for sequence #{idx} is not an array"
        if not targets:
            return False, f"Sequence #{idx} has no targets"

        # Check individual targets
        for target in targets:
            if not isinstance(target, str):
                return False, f"Target '{target}' in sequence #{idx} is not a string"
            if target not in hosts:
                return False, f"Target '{target}' in sequence #{idx} is not defined in 'hosts'"

    return True, ""
    
def load_config(filepath):
    try:
        with open(filepath, "r") as file:
            cfg = json.load(file)
    except json.JSONDecodeError as e:
        return None, f"JSON syntax error: {e}"
    except Exception as e:
        return None, f"Error reading file: {e}"

    valid, msg = validate_config(cfg)
    if not valid:
        return None, f"Validating config failed: {msg}"

    return cfg, ""

config, error = load_config("config.json")

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