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

#################
### ARGUMENTS ###
#################

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="Config file to use", default="config.json")
    parser.add_argument("--timeout", type=int, help="Time to wait for response from host", default=20)

    return parser.parse_args()
args = get_args()

###############
### DISPLAY ###
###############

serial = i2c(port=1, address=0x3C)
device = sh1106(serial, width=128, height=64)
FONT_PATH = "fonts/DejaVuSansMono.ttf"

class DisplayManager:
    def __init__(self, device):
        self.device = device
        self.width, self.height = device.width, device.height
        self.clear_buffer()

    def clear_buffer(self):
        self.buffer = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.buffer)

    def render(self):
        self.device.display(self.buffer)

    def show_menu(self, items, index):
        self.clear_buffer()
        font_size = 12
        font = ImageFont.truetype(FONT_PATH, font_size)
        line_h = font_size + 4
        
        for offset in (-1, 0, 1):
            idx = index + offset
            y = (offset + 1) * line_h + 2
            if idx < 0 or idx >= len(items):
                continue
            text = items[idx]
            if offset == 0:
                self.draw.rectangle((0, y-2, self.width-1, y+line_h), outline=255)
            self.draw.text((4, y), text, font=font, fill=255)
        self.render()

    def show_sequence(self, title, host, elapsed, total):
        self.clear_buffer()
        title_size = 20
        host_size = 16
        title_font = ImageFont.truetype(FONT_PATH, title_size)
        host_font = ImageFont.truetype(FONT_PATH, host_size)

        self.draw.text((2, 2), title, font=title_font, fill=255)

        host_y = (self.height - host_size) // 2
        self.draw.text((2, host_y), host, font=host_font, fill=255)

        bar_h = 8
        x0, y0 = 2, self.height - bar_h - 2
        bar_w = self.width - 4
        self.draw.rectangle((x0, y0, x0+bar_w, y0+bar_h), outline=255)
        if total > 0:
            fill_w = int(bar_w * elapsed / total)
        else:
            fill_w = 0
        self.draw.rectangle((x0, y0, x0+fill_w, y0+bar_h), fill=255)

        self.render()


display = DisplayManager(device)

###############
### ENCODER ###
###############

ENCODER_PIN_A = 17     # GPIO17 (Pin 11)
ENCODER_PIN_B = 27     # GPIO27 (Pin 13)
ENCODER_BTN   = 22     # GPIO22 (Pin 15)

encoder = RotaryEncoder(ENCODER_PIN_A, ENCODER_PIN_B, max_steps=0)
button = Button(ENCODER_BTN, pull_up=True)

def on_rotate():
    global last_step, current_menu_idx
    current = encoder.steps
    if current > last_step:
        if current_menu_idx < len(menu_items) - 1:
            current_menu_idx += 1
    elif current < last_step:
        if current_menu_idx > 0:
            current_menu_idx -= 1
    else:
        return
    last_step = current
    display.show_menu(menu_items, current_menu_idx)

def on_button():
    global current_menu_idx, menu_items, hosts, sequences
    choice = menu_items[current_menu_idx]
    if choice == "reload config":
        hosts, sequences = read_config(args.config)
        menu_items[:] = [seq["title"] for seq in sequences] + ["reload config"]
        current_menu_idx = 0
        display.show_menu(menu_items, current_menu_idx)
    else:
        idx = menu_items.index(choice)
        for key in sequences[idx]["targets"]:
            info = hosts[key]
            # while booting, show combined layout
            for elapsed in range(args.timeout+1):
                display.show_sequence(sequences[idx]["title"], info["host"], elapsed, args.timeout)
                time.sleep(1)
        # after sequence, back to menu
        display.show_menu(menu_items, current_menu_idx)

encoder.when_rotated = on_rotate
button.when_pressed = on_button

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
        time.sleep(2)
        return hosts, sequences

hosts, sequences = read_config(args.config)

###############
### MENU #####
###############

# Build menu items from sequence titles plus reload option
menu_items = [seq["title"] for seq in sequences] + ["reload config"]
current_menu_idx = 0
last_step = 0

def main():
    display.show_menu(menu_items, current_menu_idx)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        encoder.close()
        button.close()

if __name__ == "__main__":
    main()