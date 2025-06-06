# Wake on LAN (WoL) utility for RaspberryPi

## Needed
This tool and all scripts assume that you are running a RaspberyPi 3/4/5 Model B and have installed Ubuntu. The code and scripts should be easy to translate to any other SBC, distro, OLED or pinout.

## Installation
Make setup script executable with
```console
chmod +x setup.sh
```
then run with
```console
./setup.sh
```

## Configuration

`config.json` is already a valid example. Just name hosts and sequences whatever you like, adjust MAC and IP addresses and make sure the order inside the sequence is the order in which you want to boot the individual hosts.
