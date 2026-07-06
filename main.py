# i genuinely hate python, i might rewrite this on C++
import oscilloscope
import colors
import menucli as menu
import mido
import logo
import serial
import serial.tools.list_ports
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import signal
import threading
io_running = False

midi_input = None
serial_output : serial.Serial = None
window = None
stream_buffer = bytearray()
dirty_channels = set()
data_lock = threading.Lock()
oscilloscope.init_settings()

shutdown_requested = False

buffers = {
    i: np.zeros(oscilloscope.Channel.buffer_size,dtype=np.int16)
    for i in range(oscilloscope.settings["channels_amount"])
}

trigger_pos = {
    i: 0
    for i in range(oscilloscope.settings["channels_amount"])
}

write_pos = {
    i: 0
    for i in range(oscilloscope.settings["channels_amount"])
}
def create_window():
    global window, app, shutdown_requested
    shutdown_requested = False
    if not is_serial_valid() or not is_midi_valid() : return
    print("Press Control + C to stop")
    window = pg.GraphicsLayoutWidget(show=True)
    window.setWindowTitle("SynthTracer")
    app = pg.mkQApp("SynthTracer")
    oscilloscope.link_window(window)
def close_window():
    if not serial_output : return
    global window
    window.close()


def serialTX():
    global serial_output
    message = midi_input.poll()
    if message:
        try: serial_output.write(message.bytes())
        except Exception :
            serial_output = None
            return Exception



def serialRX():
    global stream_buffer, serial_output
    try:
        waiting = serial_output.in_waiting
    except Exception :
        serial_output = None
        return Exception
    if waiting == 0:
        return []

    stream_buffer.extend(serial_output.read(waiting))
    parsed_samples = []
    processed = 0
    while processed + 3 < len(stream_buffer):
        if stream_buffer[processed] != 255:
            processed += 1
            continue
        channel = stream_buffer[processed + 1]
        if channel < oscilloscope.settings["channels_amount"]:
            sample = (
                stream_buffer[processed + 2] << 8
                | stream_buffer[processed + 3]
            )

            if sample & 0x8000:
                sample -= 65536
            parsed_samples.append((channel, sample))
        processed += 4
    if processed:
        del stream_buffer[:processed]
    return parsed_samples

def background_io_loop():
    global io_running

    while io_running:
        serial = serialTX()
        samples = serialRX()
        
        if samples is Exception or serial is Exception:
            io_running = False
            colors.colorprint("[ERR] Disconnected!","red")
            return

        if not samples: # let the poort cpu rest while there is no data
            QtCore.QThread.msleep(1)
            continue

        with data_lock:
            for channel, sample in samples:
                if channel >= len(buffers):
                    continue

                buf = buffers[channel]
                prev_pos = (write_pos[channel] - 1) % len(buf)
                prev = buf[prev_pos]
                pos = write_pos[channel]
                buf[pos] = sample
                write_pos[channel] = (pos + 1) % len(buf)
                if prev < 0 and sample >= 0:
                    trigger_pos[channel] = write_pos[channel]

                dirty_channels.add(channel)


def sigint_handler(sig, frame):
    global shutdown_requested
    shutdown_requested = True


def draw():
    global shutdown_requested, io_running
    if shutdown_requested:
        io_running = False
        pg.mkQApp().quit()
        return
    if not io_running:
        pg.mkQApp().quit()
        return
    with data_lock:

        if not dirty_channels:
            return

        updated = list(dirty_channels)
        dirty_channels.clear()

    for channel in updated:
        pos = trigger_pos[channel]
        view = np.concatenate((buffers[channel][pos:], buffers[channel][:pos]))
        oscilloscope.channels[channel].set_data(view)

def handle_IO():
    global io_running

    io_running = True
    io_thread = threading.Thread(target=background_io_loop, daemon=True)
    io_thread.start()
    signal.signal(signal.SIGINT, sigint_handler)
    timer = QtCore.QTimer()
    timer.timeout.connect(draw)
    timer.start(16) # ~60 FPS

    pg.exec()

def is_serial_valid():
    return (
        serial_output is not None
        and serial_output.is_open
    )


def is_midi_valid():
    global midi_input

    return (
        midi_input is not None
        and not midi_input.closed
    )


def get_serial_port():
    while True:
        try:
            serial_ports = serial.tools.list_ports.comports()
            serial_ports = [p for p in serial_ports if not p.device.startswith('/dev/ttyS')]
            serial_ports_amount = len(serial_ports)

            print("Select a serial port")
            if (serial_ports_amount == 0):
                input("No serial ports detected! press enter to retry")
                continue
            for index, port in enumerate(serial_ports):
                print(index, "", port)
            port_id = menu.ask_value(int,"Enter port number : ", 0, serial_ports_amount - 1)
            if port_id == KeyboardInterrupt: return KeyboardInterrupt
            return str(serial_ports[port_id][0])
        except KeyboardInterrupt: return KeyboardInterrupt

def get_midi_port():
    while True:
        try:
            midi_input_ports = mido.get_input_names()
            midi_input_amount = len(midi_input_ports)

            if (midi_input is not None) : return
            print("Select a midi port")
            if (midi_input_amount == 0):
                input("No midi ports detected! press enter to refresh")
                continue
            for index, port in enumerate(midi_input_ports):
                print(index, "", port)
            port_id = menu.ask_value(int,"Enter port number : ", 0, midi_input_amount - 1)
            if port_id == KeyboardInterrupt: return KeyboardInterrupt
            return midi_input_ports[port_id]
        except KeyboardInterrupt: return KeyboardInterrupt
def configure_IO():
    global midi_input, serial_output
    if not is_serial_valid():
        serial_port = get_serial_port()
        if serial_port is KeyboardInterrupt: return KeyboardInterrupt
        baudrate = menu.ask_value(int,"Enter a baudrate (set to 0 if CDC) : ")
        if baudrate == KeyboardInterrupt : return KeyboardInterrupt
        serial_output = serial.Serial(serial_port,baudrate, timeout=0)
    if not is_midi_valid():
        print()
        midi_port = get_midi_port()
        if midi_port == KeyboardInterrupt : return KeyboardInterrupt
        midi_input = mido.open_input(midi_port)
    return True

def handle_oscilloscope():
    try:
        if configure_IO() == KeyboardInterrupt: return
        print()
        create_window()
        handle_IO()
        close_window()
        print("\n")
    except KeyboardInterrupt: return

def set_and_store_settings(index, value = None):
    index = index + 1
    match index:
        case 1:
            oscilloscope.settings["sampling_rate"] = value
        case 2:
            oscilloscope.settings["wave_cycles"] = value
        case 3:
            oscilloscope.settings["channels_amount"] = value
        case 4:
            oscilloscope.settings["min_val"] = value
        case 5:
            oscilloscope.settings["max_val"] = value
    oscilloscope.sync_json_settings()
    oscilloscope.init_settings()
ConfigurationMenu = menu.Menu([
    menu.MenuItem("Sampling Rate", int, "Enter a rate in hz : "),
    menu.MenuItem("Cycles", int, "Enter a number of cycles : "),
    menu.MenuItem("Channels amount", int, "Enter some channels amount : "),
    menu.MenuItem("Minimum value", int, "Enter a value : "),
    menu.MenuItem("Maximum value", int, "Enter a value : "),
    menu.MenuItem("Exit",menu.Exit)
],
set_and_store_settings, False)

MainMenu = menu.Menu([
    menu.MenuItem(colors.colortext("Start","green"),callable, target=handle_oscilloscope),
    menu.MenuItem("Configure",menu.Menu,target=ConfigurationMenu),
    menu.MenuItem(colors.colortext("Exit","orange"),menu.Exit)
],
None, False)

oscilloscope.init_settings()
menu.goToMenu(MainMenu)
colors.colorprint(logo.logo,'green')
print("SynthTracer by Guillermo Beckers (Mejolov24 on github)")
print("oscilloscope tool for sending serial midi and plotting incoming audio data")
while menu.render():
    try:
        print("\033[H\033[2J")
        colors.colorprint(logo.logo,'green')
    except KeyboardInterrupt: continue

print("Thanks for using!")
