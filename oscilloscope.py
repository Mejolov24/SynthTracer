import sys
from pathlib import Path
import json
import numpy as np

script_path = Path(__file__).parent.resolve()
settings_path = script_path / "settings.json"
settings = {}
channels = []

DEFAULT_SETTINGS = {
    "buffer_size": 400,
    "min_val": -32768,
    "max_val": 32767,
    "rx_rate": 8000,
    "data_window_ms": 50,
    "channels_amount": 15,
    "channel_names": {}
}

class Channel:
    # globals
    buffer_size = 400
    min_val = -32768
    max_val = 32767
    rx_rate = 8000

    def __init__(self, channel_id):
        self.id = channel_id
        self.name = f"Channel {channel_id}"
        self.buffer = np.zeros(Channel.buffer_size)
        self.buffer_data_amount : int = 0
    def set_name(self,name):
        self.name = name
        settings["channel_names"][str(self.id)] = name
    def clear_buffer(self):
        self.buffer_data_amount = 0
        self.buffer.fill(0)
    def get_buffer(self):
        return self.buffer
    def append_sample(self,value):
        previous_sample = self.buffer[-1]

        self.bufffer = np.roll(self.buffer,-1)
        self.buffer[-1] = value

        if self.buffer_data_amount == self.buffer_size and (previous_sample <= 0 and value > 0):
            self.clear_buffer()
        else:
            self.buffer_data_amount += 1

def init_settings():
    global settings, channels

    if not settings_path.exists():
        with open(settings_path, "w") as file:
            json.dump(DEFAULT_SETTINGS, file, indent=4)
    with open(settings_path, "rb") as file:
        settings = json.load(file)
    
    Channel.buffer_size = settings["buffer_size"]
    Channel.min_val = settings["min_val"]
    Channel.max_val = settings["max_val"]
    Channel.rx_rate = settings["rx_rate"]

    channels = []
    saved_names = settings.get("channel_names",{})

    for i in range(settings["channels_amount"]):
        ch = Channel(i)
        if str(i) in saved_names:
            ch.set_name(saved_names[str(i)])
        channels.append(ch)

def sync_json_settings():
    global settings

    with open(settings_path, "w") as file:
        json.dump(settings, file, indent=4)




init_settings()




