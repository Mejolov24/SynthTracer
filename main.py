# new
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
import time
io_running = False

midi_input = None
serial_output : serial.Serial = None
window = None
stream_buffer = bytearray()
dirty_channels = set()
data_lock = threading.Lock()
oscilloscope.init_settings()

shutdown_requested = False

latest_frame = None
new_frame = False
frame_counter = 0
drawn_frame_counter = -1

buffers = {
    i: np.zeros(oscilloscope.Channel.buffer_size,dtype=np.int16)
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
    # Drain all available MIDI messages immediately so they don't queue up
    while True:
        message = midi_input.poll()
        if not message:
            break
        try:
            serial_output.write(message.bytes())
        except Exception:
            serial_output = None
            return Exception


frame_lock = threading.Lock()

def serialRX():
    global stream_buffer, serial_output, latest_frame, frame_counter, new_frame

    try:
        waiting = serial_output.in_waiting
        if waiting:
            stream_buffer.extend(serial_output.read(waiting))
    except Exception:
        serial_output = None
        return False

    buffer_size = oscilloscope.Channel.buffer_size
    channel_amount = oscilloscope.settings["channels_amount"]

    channel_bytes = buffer_size * 2
    packet_size = 3 + channel_bytes

    if not hasattr(serialRX, "current_frame"):
        serialRX.current_frame = np.zeros(
            (channel_amount, buffer_size),
            dtype=np.int16
        )
        serialRX.received_channels = 0

    offset = 0
    buffer_length = len(stream_buffer)

    while buffer_length - offset >= packet_size:

        # 1. C-Optimized Header Search
        header_idx = stream_buffer.find(b'\xAA\x55', offset)
        
        if header_idx == -1:
            # Header not found. Discard garbage but keep the very last byte
            # just in case it is 0xAA waiting for its 0x55 counterpart.
            offset = max(0, buffer_length - 1)
            break
            
        if header_idx != offset:
            offset = header_idx
            # After jumping to the header, ensure we still have a full packet
            if buffer_length - offset < packet_size:
                break

        channel_id = stream_buffer[offset + 2]

        # Invalid channel handling
        if channel_id >= channel_amount:
            offset += 2 # Skip the current 0xAA to keep searching
            continue

        data_start = offset + 3

        # 2. Zero-Allocation Assignment
        # np.frombuffer creates a view. Assigning it directly to the slice 
        # copies the memory efficiently without a redundant .copy() heap allocation.
        serialRX.current_frame[channel_id, :] = np.frombuffer(
            stream_buffer,
            dtype="<i2",
            count=buffer_size,
            offset=data_start
        )

        serialRX.received_channels |= (1 << channel_id)
        offset += packet_size

        # Complete frame
        if serialRX.received_channels == (1 << channel_amount) - 1:
            with frame_lock:
                latest_frame = serialRX.current_frame.copy()
                new_frame = True
            serialRX.received_channels = 0

    # 3. Safe Deletion and Spiral-of-Death Prevention
    if offset > 0:
        del stream_buffer[:offset]
        
    # Hard limit: If the buffer holds more than 10 full multi-channel frames,
    # we are lagging. Flush the oldest data to forcefully catch up to real-time.
    max_safe_buffer = packet_size * channel_amount * 10
    if len(stream_buffer) > max_safe_buffer:
        del stream_buffer[:- (packet_size * channel_amount * 2)]

    return True





def background_io_loop():
    global io_running

    while io_running:

        serial_result = serialTX()
        rx_result = serialRX()

        if serial_result is Exception or rx_result is False:
            io_running = False
            colors.colorprint("[ERR] Disconnected!", "red")
            return
        time.sleep(0.001)

def sigint_handler(sig, frame):
    global shutdown_requested
    shutdown_requested = True


def draw():
    global shutdown_requested, io_running
    global latest_frame, new_frame

    if shutdown_requested:
        io_running = False
        pg.mkQApp().quit()
        return

    if not io_running:
        pg.mkQApp().quit()
        return

    with frame_lock:
        if latest_frame is None or not new_frame:
            return

        frame = latest_frame
        new_frame = False

    for channel in range(frame.shape[0]):
        oscilloscope.channels[channel].set_data(
            frame[channel]
        )

def handle_IO():
    global io_running

    io_running = True

    io_thread = threading.Thread(
        target=background_io_loop,
        daemon=True
    )
    io_thread.start()

    signal.signal(signal.SIGINT, sigint_handler)

    timer = QtCore.QTimer()
    timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
    timer.timeout.connect(draw)
    timer.start(16)

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
            oscilloscope.settings["buffer_size"] = value
        case 2:
            oscilloscope.settings["sampling_rate"] = value
        case 3:
            oscilloscope.settings["wave_cycles"] = value
        case 4:
            oscilloscope.settings["channels_amount"] = value
        case 5:
            oscilloscope.settings["min_val"] = value
        case 6:
            oscilloscope.settings["max_val"] = value
    oscilloscope.sync_json_settings()
    oscilloscope.init_settings()
ConfigurationMenu = menu.Menu([
    menu.MenuItem("Buffer Size", int, "Enter a size in bytes : "),
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
