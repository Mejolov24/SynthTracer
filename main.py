import oscilloscope
import colors
import menucli as menu
import mido
import logo
import serial
import serial.tools.list_ports
import struct
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
mido.set_backend('mido.backends.pygame') # temporal, for window test cus i hate compiling there
import signal
from pyqtgraph.Qt import QtCore, QtGui

midi_input = None
serial_output : serial.Serial = None
window = None
stream_buffer = bytearray()

def create_window():
    if not is_serial_valid() or not is_midi_valid() : return
    print("Press Control + C to stop")
    global window, app
    window = pg.GraphicsLayoutWidget(show=True)
    window.setWindowTitle("SynthTracer")
    app = pg.mkQApp("SynthTracer")
    oscilloscope.link_window(window)
def close_window():
    if not serial_output : return
    global window
    window.close()


def serialTX():
    message = midi_input.poll()
    if message:
        try: serial_output.write(message.bytes())
        except Exception :
            colors.colorprint("[ERR] Disconnected!","red")
            return


def serialRX():
    global stream_buffer

    waiting = serial_output.in_waiting
    if waiting == 0:
        return

    stream_buffer.extend(
        serial_output.read(waiting)
    )

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
            oscilloscope.channels[channel].append_sample(sample)
        processed += 4
    if processed:
        del stream_buffer[:processed]

def handle_IO():
    # 1. Custom signal handler to cleanly raise a KeyboardInterrupt
    def sigint_handler(sig, frame):
        # This breaks pg.exec() and raises the exception Python expects
        pg.mkQApp().quit() 
        raise KeyboardInterrupt

    # Register our clean handler instead of the nuclear default one
    signal.signal(signal.SIGINT, sigint_handler)

    timer = QtCore.QTimer()
    timer.timeout.connect(serialRX)
    timer.timeout.connect(serialTX)
    timer.timeout.connect(oscilloscope.update_plots)
    fps = 60
    timer.start(int(1000 / fps))
    
    interrupt_timer = QtCore.QTimer()
    interrupt_timer.start(100)
    interrupt_timer.timeout.connect(lambda: None) 
    
    try:
        pg.exec()
    except KeyboardInterrupt:
        # Catch it here if it happens inside pg.exec()
        pass
    finally:
        timer.stop()
        interrupt_timer.stop()
        # 2. Reset back to Python's default behavior so the main menu can handle SIGINT again
        signal.signal(signal.SIGINT, signal.default_int_handler)

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
    serial_ports = serial.tools.list_ports.comports()
    serial_ports_amount = len(serial_ports)

    print("Select a serial port")
    if (serial_ports_amount == 0):
        input("No serial ports detected! press enter to retry")
        return get_serial_port()
    for index, port in enumerate(serial_ports):
        print(index, "", port)
    port_id = menu._ask_value(int,"Enter port number : ", 0, serial_ports_amount - 1)
    return str(serial_ports[port_id][0])

def get_midi_port():
    midi_input_ports = mido.get_input_names()
    midi_input_amount = len(midi_input_ports)

    if (midi_input is not None) : return
    print("Select a midi port")
    if (midi_input_amount == 0):
        input("No midi ports detected! press enter to refresh")
        return get_midi_port()
    for index, port in enumerate(midi_input_ports):
        print(index, "", port)
    port_id = menu._ask_value(int,"Enter port number : ", 0, midi_input_amount - 1)
    return midi_input_ports[port_id]

def configure_IO():
    global midi_input, serial_output
    if not is_serial_valid():
        serial_port = get_serial_port()
        baudrate = menu._ask_value(int,"Enter a baudrate (set to 0 if CDC) : ")
        serial_output = serial.Serial(serial_port,baudrate, timeout=0)
    if not is_midi_valid():
        print()
        midi_port = get_midi_port()
        midi_input = mido.open_input(midi_port)


def handle_oscilloscope():
    try:
        configure_IO()
        print()
        create_window()
        handle_IO()
        close_window()
        print("\n")
    except KeyboardInterrupt: return

def set_and_store_settings(index, value = None):
    match index:
        case 0:
            oscilloscope.settings["buffer_size"] = value
        case 1:
            oscilloscope.settings["rx_rate"] = value
        case 2:
            oscilloscope.settings["data_window_ms"] = value
        case 3:
            oscilloscope.settings["channels_amount"] = value
        case 4:
            oscilloscope.settings["min_val"] = value
        case 5:
            oscilloscope.settings["max_val"] = value

    oscilloscope.sync_json_settings()

ConfigurationMenu = menu.Menu([
    menu.MenuItem("Buffer size", int, "Enter a size : "),
    menu.MenuItem("Rx rate", int, "Enter a rate in hz : "),
    menu.MenuItem("Data Window", int, "Enter a window in ms : "),
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
