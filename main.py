import oscilloscope
import colors
import menucli as menu
import mido
import logo
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import serial
import serial.tools.list_ports

mido.set_backend('mido.backends.pygame') # temporal, for window test cus i hate compiling there

midi_input = None
serial_output : serial.Serial = None

def make_window():
    win = pg.GraphicsLayoutWidget(show=True)
    win.setWindowTitle("SynthTracer")
    app = pg.mkQApp("SynthTracer")

def serialTX():
    try:
        while True:
            message = midi_input.poll()
            if message:
                try: serial_output.write(message.bytes())
                except Exception :
                    colors.colorprint("[ERR] Disconnected!","red")
                    return
    except KeyboardInterrupt: return

def is_serial_valid():
    global serial_output

    try :
        serial_output.write(255)
        return True
    except Exception : return False


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

    try:
        if not is_serial_valid():
            serial_port = get_serial_port()
            baudrate = menu._ask_value(int,"Enter a baudrate (set to 0 if CDC) : ")
            serial_output = serial.Serial(serial_port,baudrate)
        if not is_midi_valid():
            print()
            midi_port = get_midi_port()
            midi_input = mido.open_input(midi_port)
    except KeyboardInterrupt: return

def handle_oscilloscope():
    configure_IO()
    print()
    print("Press Control + C to stop")
    make_window()
    serialTX()
    print("\n")

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


menu.goToMenu(MainMenu)
colors.colorprint(logo.logo,'green')
print("SynthTracer by Guillermo Beckers (Mejolov24 on github)")
print("oscilloscope tool for sending serial midi and plotting incoming audio data")
while menu.render():
    print("\033[H\033[2J")
    colors.colorprint(logo.logo,'green')

print("Thanks for using!")
