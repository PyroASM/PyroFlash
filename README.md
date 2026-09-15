# PyroFlash
Micropython Flash Tool

Supported targets

|target|description|
|------|-----------|
|STM32F103|UART bootloader|
|STM32F411|UART, alpha|
|STM8F103|SWIM emulation based on 8 MHz hw SPI, sw SPI is used for init|
SPI FLASH


Currently STM32F411 blackpill Micropython board is tested 

firmware sources:
files: binary or .ihex
stdin: base64 or ihex (detected by ":")
raw objects: bytes, bytearray, memoryview 


Flashing examples

use file=None to read base64 or ihex from stdin
or specify file name

if no addr specified and not ihex, default flash org used 

keyword args are bypassed to init() of communication object (UART, SPI, SoftSPI)

STM32F103
```python
from PyroFlash import STM32
from machine import UART

flasher = STM32 (UART(2)) 

flasher.flash(addr=0x800_0000, file=None)
flasher.run () # run execution 

```


SPI Flash example  
uses SoftSPI
```python
from PyroFlash import W25Q

flasher = W25Q (mosi="A7", sck="B3", miso="A6", cs="B2")
flasher.flash() # uploads to default address
```

STM8F103 Flash example  
```python
from PyroFlash import STM8
from machine import SPI

flasher = STM8 (SPI(3), rst="B6", mosi="B5", miso="B4", sck="B12")
flasher.flash()
```


Other common methods:

RU () readout unprotect (clears whole chip)
run() start execution 

read_memory (addr, sz) read any amount of data from address space 

