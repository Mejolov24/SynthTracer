# SynthTracer
Serial Plotting tool RX + Midi TX

![thumbnail](https://github.com/Mejolov24/SynthTracer/blob/main/thumbnail.png)

## Dependencies
- mido
- numpy
- pyqtgraph
- pyserial
- pyside6
- python-rtmidi

#### uv is recommended
https://docs.astral.sh/uv/

## Usage:
 - Start
 - Define Serial port and baudrate
 - Define Input Midi port

## Settings
 - Buffer Size
 - Minimum value
 - Maximum value
 - Channels
 - Channel names

### Recomended library for reading serial midi:
[MidiParser](https://github.com/Mejolov24/MidiParser)

## Serial TX protocol
```cpp
for (int channel_id = 0; channel_id < MAX_CHANNELS; channel_id++){
    Serial.write(0xAA);
    Serial.write(0xBB);
    Serial.write(channel_id);
    Serial.write((uint8_t*)serialbuffer[channel_id], BUFFER_SIZE * sizeof(int16_t));
}
```