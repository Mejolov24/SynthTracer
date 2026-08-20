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

    buffer_size = 256
    min_val = -32768
    max_val = 32767

    def __init__(self, channel_id):

        self.id = channel_id
        self.name = f"Channel {channel_id}"

        self.buffer = np.zeros(
            Channel.buffer_size,
            dtype=np.int16
        )

        self.curve = None

    def set_name(self,name):
        self.name = name
        settings["channel_names"][
            str(self.id)
        ] = name

    def set_data(self, data):
        np.copyto(self.buffer, data)
        self.curve.setData(self.buffer, _callSync="off")

def link_window(layout_widget):
    global channels

    pg.setConfigOptions(
        antialias=False,
        useOpenGL=True
    )

    for index, channel in enumerate(channels):

        plot = layout_widget.addPlot(
            title=channel.name
        )

        plot.setDownsampling(
            mode="peak",
            auto=True
        )

        plot.disableAutoRange()

        plot.setRange(
            xRange=[
                0,
                Channel.buffer_size
            ],
            yRange=[
                Channel.min_val,
                Channel.max_val
            ],
            padding=0
        )

        color = pg.intColor(
            channel.id,
            hues=len(channels)
        )

        channel.curve = plot.plot(
            pen=pg.mkPen(
                color,
                width=1
            )
        )

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
        ch.buffer = np.zeros(Channel.buffer_size, dtype=np.int16)
        if str(i) in saved_names:
            ch.set_name(saved_names[str(i)])
        channels.append(ch)

def sync_json_settings():
    global settings

    with open(settings_path, "w") as file:
        json.dump(settings, file, indent=4)





