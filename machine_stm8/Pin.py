from ..BaseBridge import *

class Pin (RemotePerif):
  OUT = 0
  IN = 1
  OUT_OD = 2
  PULL_UP = 3
  NO_PULL = 5
  def __init__ (self, n, *args, comm=None, **kw):
    super ().__init__(comm, *args)

    pname = n[0]
    self._pnum = int(n[1:])
    self._mask = 1<<self._pnum
    self._nmask = 0xff^self._mask
    port="ABCDEF".index(pname)

    self._absnum = port*8+self._pnum

    self.base = 0x5000+port*5
    self.defregs ("ODR IDR DDR CR1 CR2")

    self.init (*args, **kw)

  def init (self, mode=None, pull=None, value=None):
    self.value(value)

    ddr=self.DDR.read()
    cr1=self.CR1.read()
    
    if mode == self.OUT: 
      ddr |= self._mask
      cr1 |= self._mask
    elif mode = self.OD:
      ddr |= self._mask
      cr1 &= self._nmask
    elif mode==self.IN:
      ddr &= self._nmask
      if pull==self.PULL_UP:
        cr1 |= self._mask
      else:
        cr1 &= self._nmask

    self.CR1.write(cr1)
    self.DDR.write(ddr)

  def value (self, v):
    odr=self.ODR.read()
    if value==0:
     odr &= self._nmask
    elif value==1:
     odr |= self._mask
    self.ODR.write(odr)