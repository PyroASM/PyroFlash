from PyroFlash.Core.BaseBridge import *

import time
import machine

from machine import Pin, SPI, bitstream, SoftSPI
#bitstream used for low speed init sequence

SWIM_0=bytearray.fromhex("0003")
SWIM_1=bytearray.fromhex("3fff")

ACK = SWIM_1
NACK = SWIM_0

SWIM_bit = (SWIM_0,SWIM_1)


# to remap stm32 pins
def af_for_spi (pin, n):
  if not isinstance(pin, str):
    pin = pin.name() if hasattr(pin, "name") else str(pin)
  if not isinstance(n, int):
    n = spi_id(n)
  target = "SPI" + str(n)
  for af in Pin.af_list(Pin(pin)):
    if target in af.name():
      return af.index()

  raise Exception ("AF not found for Pin: "+ str (pin)+", SPI: "+ str(n))

def spi_id(spi_obj):
  if isinstance(spi_obj, int):
    return spi_obj
  return int(str(spi_obj).split("(")[1].split(",")[0])


class SWIM_SPI (BaseBridge):
  rst=None
  def __init__(self, comm, *args, rst=None, mosi=None, miso=None, sck=None, **kw):
    super ().__init__(*args, bsz=255, **kw)

    machine.freq(64000000)
    #SPI must have exact frequency of 8MHz

    self.mosi = Pin(mosi)
    self.miso = Pin(miso)
    self.sck = Pin(sck) #unused, stub for softspi 
    
    if type(comm) is int:
      comm = SPI(comm)

    comm.init(baudrate=8_000_000)
    self.comm = comm
    self.pins_afod ()

    if rst:
      self.rst=Pin(rst, Pin.OUT, value=1)

    RemotePerif.mem8 = self  # shortcut for periferals 

  def start (self, dbg=0):
    if self.rst:
      time.sleep_ms(100)
      self.rst.value(0)
      time.sleep_ms(100)
    
    self.swim_init(method=0)
    rv=self.swim_comm_rst(dbg=dbg)
    if not rv:
      raise Exception ("No answer")

    self.wof(0x7f80, 0x25)
    if dbg: print (self.rof (0x7f80,1).hex())
    
    if self.rst:
      self.rst.value(1)
      time.sleep_ms(10)

  def pins_afod(self):
    self.comm.init()

    self.mosi.init(mode=Pin.AF_OD, pull=Pin.PULL_UP, alt=af_for_spi(self.mosi,self.comm))
    self.miso.init(mode=Pin.AF_OD, pull=Pin.PULL_UP, alt=af_for_spi(self.miso,self.comm))

  def pins_od(self):
    self.comm.deinit()
    self.mosi.init(mode=Pin.OUT_OD, pull=Pin.PULL_UP)
    self.miso.init(mode=Pin.IN, pull=Pin.PULL_UP)

  def swim_init(self, method=0):
   if method==0:
    self.softspi = SoftSPI (16000, mosi=self.mosi, miso=self.miso, sck=self.sck)
    self.pins_od()
    self.softspi.write (bytearray.fromhex("00ff00ff00ff00ff00f0f0f0f0ffffffff"))
  
   elif method==1:  # don't work need dbg
    self.pins_od()
    timing = (500, 500, 1000, 1000)
    bitstream(self.mosi, 0, timing, b"\x07\x10")
    self.pins_od()

   self.pins_afod ()
    
  def swim_comm_rst(self, dbg=0):
    sz = 64//4+10
    seq = "00"*sz + "ff"*sz
    seq = bytearray.fromhex(seq)
    self.comm.write_readinto(seq, seq)

    if dbg:
      print (seq.hex())

    if seq[sz:].hex()=="ff"*sz:
      return False 

    return True

  def _packet(self, v, sz):
    rv = [0] #start bit
    n = 1<<(sz-1)
    p=0 #parity bit
    for i in range (sz):
      bit = v&n
      if bit>0: bit=1
      p = p^bit
      rv.append (bit)
      n=n>>1
    rv.append (p)
    
    rv = [SWIM_bit[bit] for bit in rv]
    b = bytearray ()
    for v in rv: b += v
    
    return b

  def transfer (self, v, sz, rv=1, dbg=0):
     p=self._packet (v, sz)
     if dbg: print (p.hex())

     idx = len (p)

     if rv:
       p += bytearray.fromhex("ff"*int(rv*3.1))

     self.comm.write_readinto(p,p)

     if dbg: print (p.hex())
     
     pulses = self.get_bits (p[idx:])
     rv = pulses [0]

     if len (pulses)>1:
       return pulses

     return rv

  def get_pulses(self, raw, dbg=0):
     psz = 0
     state= -1

     pulses=[]
     
     #count pulse length 
     for v in raw:
      for i in range (8):
       if v & 0x80 == state:
         if state==0:
           psz += 1  # inc pulse size 
         else:
           psz=0       # reset pulse size 
       else:
         if state == 0:
           pulses.append(psz)
         state= v & 0x80
         if state== 0:
           psz = 1
       v <<= 1

     if dbg: print (pulses)
     return pulses

  def get_bits(self, raw):
     pulses = self.get_pulses(raw)
     # resolve bits
     pulses = [0 if v>=9 else 1 for v in pulses]
     return pulses

  
  def swim_rst(self):
    return self.transfer(0,3)

  def wof(self, addr, data):
    if type (data) is int:
      data= data.to_bytes(1)
    elif type (data) is str:
      data= bytearray.fromhex(data)

    sz = len(data)

    if sz>255: 
      raise Exception ("max swim packet is 255 bytes, "+str(sz)+" given")

    rv = bytearray ()
    
    rv += sz.to_bytes(1)
    rv += addr.to_bytes(3,"big")
    rv += data

    self.transfer(2,3) #wof cmd

    for v in rv:
      self.transfer(v,8)

  def get_byte (self, bits):
     rv = 0
     if len (bits) != 10:
        raise Exception ("Wrong packet: "+str(bits))
     for v in bits[1:-1]:
       rv <<= 1
       rv |= v
     return rv

  def rof (self, addr, sz=1, dbg=0):
    if sz>255: 
      raise Exception ("max swim packet is 255 bytes, "+sz+" given")

    
    rv = bytearray ()

    rv += sz.to_bytes(1)
    rv += addr.to_bytes(3,"big")

    self.transfer(1,3) #rof cmd

    for v in rv:
      self.transfer(v,8)

    rv = bytearray (sz)
    for i in range (sz):
      p = bytearray ()
      if i==0:
        p += NACK  #repeat first byte
      else:
        p += ACK
      p += bytearray.fromhex("ffff"*20) #10 bits with extra gap

      self.comm.write_readinto(p,p)
      if dbg: print (p.hex())

      bits = self.get_bits(p)
      if dbg: print (bits)
      bits = bits [1:] # omit ack/nack loopback bit
      rv [i] = self.get_byte(bits)

    self.comm.write(ACK)
    return rv
  
  bwrite = wof
  bread = rof



SWIM = SWIM_SPI



