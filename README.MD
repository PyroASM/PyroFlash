# PyroFlash
Micropython Flash Tool

Supported targets

|target|description|
|------|-----------|
|STM32F103|UART bootloader|
|STM32F411|UART, alpha|
|STM8F103|SWIM emulation based on 8 MHz SPI|
SPI FLASH


STM32F411 blackpill example flashing STM32F103

```python
from PyroFlash import STM32
from machine import UART

flasher = STM32 (UART(2))

flasher.flash(addr=0x800_0000, file=None)
flasher.run () # run execution 

# specify binary file, bytearray
# or use None which reads base64 or ihex from stdin
```


SPI Flash example  
uses SoftSPI
```python
from PyroFlash import W25Q

flasher = W25Q (mosi="A7", sck="B3", miso="A6", cs="B2")
flasher.flash() # uploads 
```
