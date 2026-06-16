import time
import serial
import mido
mido.set_backend('mido.backends.pygame')
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
import numpy as np
import random
import threading

# --- CONFIGURATION ---
SERIAL_PORT = 'COM3'
BAUD_RATE = 1000000
BUFFER_SIZE = 400  # Zoomed in: shows 50ms of data at 8kHz
CHANNELS = 15      # REMOVED Master Mix (17 -> 16)
FPS = 60           
PERIOD_MS = int(1000 / FPS)

# --- SERIAL SETUP ---
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
ser.set_buffer_size(rx_size=65536, tx_size=16384)

# --- PLOT SETUP ---
app = pg.mkQApp("ESP32 MIDI Visualizer")
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle("16-Channel 16-Bit Oscilloscope")

colors = ['y', 'r', 'g', 'b', 'c', 'm']
plots = []
curves = []
data_channels = [np.zeros(BUFFER_SIZE) for _ in range(CHANNELS)]
channels_to_update = set()
data_lock = threading.Lock()

for i in range(CHANNELS):
    # Layout: 2 columns of 8 rows
    if i % 2 != 0:
        win.nextRow()
    
    title = f"Channel {i + 1}"
    p = win.addPlot(title=title)
    
    # Optimization & Zoom
    p.setDownsampling(mode='peak')
    p.setClipToView(True)
    p.setRange(xRange=[0, BUFFER_SIZE], yRange=[-32768, 32767], padding=0)
    p.disableAutoRange()
    
    c = p.plot(pen=random.choice(colors))
    
    plots.append(p)
    curves.append(c)

# --- LOGIC THREADS ---

def update_midi():
    """Reads MIDI from input port and pipes it directly to Serial."""
    while True:
        message = midi_input.poll()
        if message:
            ser.write(message.bytes())
        time.sleep(0.001)

def update_logic():
    """Handles incoming 16-bit serial data using fast chunk processing."""
    global channels_to_update
    stream_buffer = bytearray()
    
    while True:
        # Check if data is available; if not, yield CPU time to prevent GUI starvation
        in_waiting = ser.in_waiting
        if in_waiting == 0:
            time.sleep(0.001)
            continue
            
        # Read all available bytes at once
        stream_buffer.extend(ser.read(in_waiting))
        
        processed_bytes = 0
        buffer_length = len(stream_buffer)
        
        with data_lock:
            # We need at least 4 bytes for a complete packet (Header + ID + 2 Byte Sample)
            while processed_bytes <= buffer_length - 4:
                if stream_buffer[processed_bytes] != 255:
                    processed_bytes += 1
                    continue  # Scan forward until we hit a sync header
                
                # Extract packet data safely
                channel_id = stream_buffer[processed_bytes + 1]
                
                if channel_id < CHANNELS:
                    # Convert 2 bytes back to signed 16-bit integer quickly
                    b1 = stream_buffer[processed_bytes + 2]
                    b2 = stream_buffer[processed_bytes + 3]
                    sample = (b1 << 8) | b2
                    if sample & 0x8000:  # Compute two's complement sign
                        sample -= 65536
                    
                    # High-speed in-place buffer update (Avoids costly np.roll memory copies)
                    data_channels[channel_id][:-1] = data_channels[channel_id][1:]
                    data_channels[channel_id][-1] = sample
                    channels_to_update.add(channel_id)
                
                processed_bytes += 4
                
        # Remove processed bytes from the stream buffer
        if processed_bytes > 0:
            del stream_buffer[:processed_bytes]

def update_graph():
    """Main UI thread update for plotting."""
    with data_lock:
        if not channels_to_update:
            return
        for ch in channels_to_update:
            curves[ch].setData(data_channels[ch])
        channels_to_update.clear()

def start_system():
    available_ports = mido.get_input_names()
    if not available_ports:
        print("No MIDI ports found!")
        return

    for i, name in enumerate(available_ports):
        print(f"[{i}] {name}")
    
    try:
        selection = int(input("Select MIDI Port Number: "))
        port_name = available_ports[selection]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    global midi_input
    midi_input = mido.open_input(port_name)

    # Launch processing threads
    threading.Thread(target=update_midi, daemon=True).start()
    threading.Thread(target=update_logic, daemon=True).start()

    # PyQtGraph high-frequency timer
    global timer
    timer = QtCore.QTimer()
    timer.timeout.connect(update_graph)
    timer.start(PERIOD_MS)

if __name__ == '__main__':
    start_system()
    pg.exec()