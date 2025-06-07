import time
import json
import sys
import re
import ipaddress
import argparse

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from gpiozero import RotaryEncoder, Button

###################
### GLOBAL VARS ###
###################

last_step = 0
current_screen = 0
main_menu_index = 0
num_main_menu_items = 0
main_menu_items = []

#################
### ARGUMENTS ###
#################

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="Config file to use", default="config.json")
    parser.add_argument("--timeout", type=int, help="Time to wait for response from host", default=20)

    return parser.parse_args()

#########################
### ENCODER CALLBACKS ###
#########################

def on_rotate():
    global last_step, main_menu_index
    current_step = encoder.steps

    # Main menu
    if current_screen == 0:
        if current_step > last_step:
            main_menu_index += 1
            if main_menu_index > num_main_menu_items:
                main_menu_index = num_main_menu_items
        elif current_step < last_step:
            main_menu_index -= 1
            if main_menu_index < 0:
                main_menu_index = 0

    last_step = current_step

def on_button():
    global current_screen

    # Main Menu
    if current_screen == 0:
        # Move to refresh config screen
        if main_menu_index == num_main_menu_items:
            current_screen = 1
        # Move to sequence screen
        else:
            current_screen = 2

##############################
### LOAD & VALIDATE CONFIG ###
##############################

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

def read_config(configfile):
    global num_main_menu_items
    config, error = load_config(configfile)
    if error:
        #show_message("ERROR!", "Check terminal")
        print(error)
        time.sleep(5)
        sys.exit(1)
    else:
        #show_message("Config OK")
        print("Config OK")
        hosts = config["hosts"]
        sequences = config["sequences"]
        num_main_menu_items = len(sequences)
        time.sleep(2)
        return hosts, sequences

def draw_main_menu(draw):
    font_size = 14
    font = ImageFont.truetype(FONT_PATH, font_size)
    box_height = font_size + 4

    for offset in (-1, 0, 1):
        index = main_menu_index + offset
        y = (offset + 1) * box_height + 2
        if index < 0 or index >= num_main_menu_items:
            text = "-------------"
        else:
            text = main_menu_items[index]
        if offset == 0:
            draw.rectangle((0, y-2, device.width-1, y+box_height), outline=255)
        draw.text((4, y), text, font=font, fill=255)


### MAIN EXECUTION ########################################################

args = get_args()
hosts, sequences = read_config(args.config)
main_menu_items = [seq["title"] for seq in sequences] + ["Reload Config"]
num_main_menu_items = len(main_menu_items)

###############
### DISPLAY ###
###############

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64)
buffer = Image.new("1", device.size)
draw = ImageDraw.Draw(buffer)
FONT_PATH = "fonts/DejaVuSansMono.ttf"

###############
### ENCODER ###
###############

ENCODER_PIN_A = 17     # GPIO17 (Pin 11)
ENCODER_PIN_B = 27     # GPIO27 (Pin 13)
ENCODER_BTN   = 22     # GPIO22 (Pin 15)

encoder = RotaryEncoder(ENCODER_PIN_A, ENCODER_PIN_B, max_steps=0)
button = Button(ENCODER_BTN, pull_up=True)

encoder.when_rotated = on_rotate
button.when_pressed = on_button


while True:
    try:
        time.sleep(0.05)
    except KeyboardInterrupt:
        encoder.close()
        button.close()

    draw_main_menu(draw)
    device.display(buffer)