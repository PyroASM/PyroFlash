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
from PyroFlash.Flashers.STM32Flash import Flasher 
from machine import Pin, UART

u = UART (2, baudrate=250000, timeout=100, rxbuf=1*1024)

tx = Pin("A2", mode=Pin.AF_PP, af=Pin.AF7_USART2)
rx = Pin("A3", mode=Pin.AF_PP, af=Pin.AF7_USART2)

bl = Flasher (u)

bl.flash(0x800_0000, file=None)
# specify binary file, bytearray
# or use None which runs base64 uploader 
bl.run ()
```


stm8f103 example 
```python
from PyroFlash.Flashers import stm8 as Flasher 

#
bl = Flasher (port, type=0)
#bl.Flash.rop_disable()

#bl.flash(0x8000, "out.bin")
#bl.run ()


from PyroFlash.machine_stm8 import ADC

adc = ADC (ADC.CORE_VREF)

print("vdd", adc.read_vdda())

for i in ADC.channels:
  adc = ADC (i)
  print (i, adc.read_v())
```

SPI Flash example 
```python
from PyroFlash.Flashers.SPIFlash import Flasher 
from machine import Pin

bl = Flasher (mosi="B5", sck="B12", miso="B4", cs="B2")
#bl.RM(0,16).hex()

bl.flash(0)
```
