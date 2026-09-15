from PyroFlash.Core.BaseBridge import *

class ADC (RemotePerif):
  CORE_VREF = 7
  VREF_V = 1.22

  channels=range (2,8)
  def __init__ (self, pin, *args, comm=None):
    
    super ().__init__(comm, *args)

    if pin not in self.channels:
      raise Exception ("ADC on pin "+ str(pin) + " does not supported")

    self.base = 0x5400
    self.defregs ("CSR CR1 CR2 CR3 DRH DRL")
    self.blocksz = 64

    self.pin = pin

    if self.CR1.read() & 1 == 0:
      self.CR1.write(1)

  def read_u16 (self, pin=None):
    pin = pin or self.pin

    self.CSR.write (pin) # set channel and clear EOC flag
    self.CR2.write (0x08) # align right

    self.CR1.write (1) # start conversion 

    for i in range (100):
      st = self.CSR.read()
      if st & 0x80:
        break
    else:
     raise Exception ("ADC timeout")
    
   # rv = self.DRH.read()<<8
   # rv += self.DRL.read()<<6 # read for left alignment 
    
    
    rv = self.DRL.read() # read for right alignment 
    rv += self.DRH.read() << 8
    rv <<= 6 # u16
    
    return rv 

  def read_v (self):
    vref = self.read_u16(pin=self.CORE_VREF)
    u16 = self.read_u16()

    rv = self.VREF_V*u16/vref

    return rv

  def read_vdda (self):
    vref = self.read_u16(pin=self.CORE_VREF)
    rv = self.VREF_V*65536/vref
    return rv
