import sys
from pathlib import Path
import json
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

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
    "channels_amount": 16,
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
        self.curve = None
        self.ptr = 0
    def set_name(self,name):
        self.name = name
        settings["channel_names"][str(self.id)] = name
    def clear_buffer(self):
        self.buffer_data_amount = 0
        self.buffer.fill(0)
    def get_buffer(self):
        return np.concatenate((self.buffer[self.ptr:], self.buffer[:self.ptr]))

    def append_sample(self, value):
        self.buffer[self.ptr] = value
        self.ptr = (self.ptr + 1) % Channel.buffer_size

    def update_ui(self):
        if self.curve is not None:
            self.curve.setData(self.get_buffer())

def update_plots():
    global channels
    for channel in channels:
        channel.update_ui()

def link_window(layout_widget: pg.GraphicsLayoutWidget):
    global channels
    for index, channel in enumerate(channels):
        plot_view = layout_widget.addPlot(title=channel.name)
        plot_view.setYRange(Channel.min_val, Channel.max_val)
        plot_view.setXRange(0, Channel.buffer_size)
        plot_view.showGrid(x=True, y=True, alpha=0.3)
        color = pg.intColor(channel.id,hues=(len(channels)))
        channel.curve = plot_view.plot(pen=pg.mkPen(color, width=1.5), name=channel.name)
        if (index + 1) % 4 == 0:
            layout_widget.nextRow()
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




