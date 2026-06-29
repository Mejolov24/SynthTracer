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
    "sampling_rate": 8000,
    "wave_cycles": 3,
    "min_val": -32768,
    "max_val": 32767,
    "channels_amount": 16,
    "channel_names": {}
}

def calculate_buffer(sampling_rate : int, cycles : int, frecuency : int):
    return round( (sampling_rate * cycles) / frecuency)


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
        self.curve = None
    def set_name(self,name):
        self.name = name
        settings["channel_names"][str(self.id)] = name
    def clear_buffer(self):
        self.buffer_data_amount = 0
        self.buffer.fill(0)
    def set_data(self, data : np.ndarray):
        self.buffer = data
        self.update_ui()

    def update_ui(self):
        if self.curve is not None:
            self.curve.setData(self.buffer)

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
    
    Channel.min_val = settings["min_val"]
    Channel.max_val = settings["max_val"]
    Channel.sampling_rate = settings["sampling_rate"]
    Channel.buffer_size = calculate_buffer(settings["sampling_rate"], settings["wave_cycles"], 440)
    
    channels = []
    saved_names = settings.get("channel_names",{})

    for i in range(settings["channels_amount"]):
        ch = Channel(i)
        ch.buffer = np.zeros(Channel.buffer_size)
        if str(i) in saved_names:
            ch.set_name(saved_names[str(i)])
        channels.append(ch)

def sync_json_settings():
    global settings

    with open(settings_path, "w") as file:
        json.dump(settings, file, indent=4)





