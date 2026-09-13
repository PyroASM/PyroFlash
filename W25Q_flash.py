from PyroFlash.Core.BaseFlasher import*

from machine import Pin, SPI, SoftSPI 
import time

class Flasher (BaseFlasher):
  tsz = 256
  psz = 4096
  wdelay = 100
  kw = {}
  addr=0
  def __init__ (self, spi=-1, cs=None, **kw):
     if type (spi) is int:
      if spi < 0:
       spi = SoftSPI(**kw)
      else:
       spi = SPI(spi, **kw)

     if type (cs) in (str,int):
       cs = Pin(cs, Pin.OUT, value=1)

     self.spi = spi
     self.cs = cs

     self.rbuf = bytearray (1024)

     super ().__init__()
     
  def start (self):
    time.sleep_ms(10)

    self.flush()
    
    sr=self.RDSR()
    print ("Status Reg", hex (sr))
    if sr & 0x1c:
      self.WRSR(0)
      print ("Block protection unlocked")

    for i in range (5):
      self.WRDI()
      v = self.RDSR()
      if (v & 2):
        raise Exception ("Device not connected", hex(v))
      self.WREN()
      v = self.RDSR()
      if not (v & 2): 
        raise Exception ("Device not connected", hex(v))


    self.flush()
    rv = self.RDID()
    print ("RDID", rv.hex())
    v = rv[0]

    if v == 0 or v==0xff:
      rv = self.RDID2()
      print ("Trying old RDID", rv.hex())
      v=rv[3]
      if (v == 0 or v==0xff):
        raise Exception ("No response from device")
      self._SE_CMD_=0xd7

    vendors = {
     0xEF: "Winbond",
     0x20: "Micron/Numonyx",
     0xC2: "Macronix",
     0x1F: "Atmel/Adesto",
     0xBF: "SST/Microchip",
     0x9d: "PMC",
    }
    
    if v in vendors:
      print ("Vendor:",vendors[v])
    else:
      print ("Vendor unknown",hex(v))

    

  def flush (self):
    self.spi.readinto(self.rbuf)

  def cmd (self, c, addr=None):
    if type (c) is int: c = c.to_bytes(1)

    self.cs.value(0)
    self.write (c)
     
    if addr is not None:
      self.write (addr.to_bytes(3,"big"))

  def write (self, src):
    if type (src) is bytes:
      dst = bytearray (src)
    else: dst= src

    self.spi.write_readinto(src, dst)
    return dst

  def RDID (self):
     self.flush()
     self.cmd (0x9f)
     rv = self.write(b"000")
     self.cs.value(1)
     return rv

  def RDID2 (self):
     self.flush()
     self.cmd (0xab)
     rv = self.write(b"000000")
     self.cs.value(1)
     return rv
     
  def WREN (self):
     self.cmd (6)
     self.cs.value(1)

  def WRDI (self):
     self.cmd (4)
     self.cs.value(1)

  def RDSR (self):
     self.cmd (5)
     rv = self.write(b'00')
     self.cs.value(1)
     return rv[0]

  def WRSR (self, v):
     self.WREN()

     self.cmd (1)
     self.write (v.to_bytes(1))
     self.cs.value(1)

  def RM (self, addr, cnt):
    self.cmd (3, addr)
    rv = self.write (bytearray (cnt))
    self.cs.value(1)

    return rv

  def PP (self, addr, block):
     if super ().WM (addr, block): return
     block = toBytes(block)
     
     self.WREN()
     
     self.cmd (2, addr)
     self.write (block)
     self.cs.value(1)

     self.wait()

  WM = PP

  _SE_CMD_ = 0x20
  def SE (self, addr):
     print ("SE",hex(addr))
     self.WREN()

     self.cmd (self._SE_CMD_ ,addr) # 0x20 or 0xd7
     self.cs.value(1)

     self.wait()

  CM = SE

  def BE (self, addr):
     self.WREN()

     self.cmd (0xD8, addr)
     self.cs.value(1)

     self.wait()

  def CE (self):
     self.WREN()

     self.cmd (0xC7)
     self.cs.value(1)

     self.wait()

  def DP (self):
     self.cmd (0xb9)
     self.cs.value(1)

  def RES (self):
     self.cmd (0xAB)
     self.cs.value(1)
##############################
  
  def wait (self):
    self.flush()
    while self.RDSR() & 1:
      pass

  def read_flash_size(self):
    rv = self.RDID()
    v = rv[0]
    if v == 0 or v ==0xff:
      rv = self.RDID2()
      v = rv[3]
      if (v == 0 or v==0xff):
        raise Exception ("No response from device")
      sz = rv[4]-0x6b
    else:
      sz=rv[2]

    if sz==0 or sz==255:
      print ("Wrong size",hex(sz))
      return 0
    elif sz < 5:
      rv = (32*1024)<<sz
      print ("!! Old chip, flash size is unreliable")
      #self.wsz = 1
    else:
      rv = 1<<sz

    return rv



  def readblocks(self, block_num, buf, offset=0):
    addr = block_num * self.psz + offset
    buf[:]=self.RM(addr, len(buf))[:]

  def writeblocks(self, block_num, buf, offset=None):
    if offset is None: # do erase, then write
      for i in range(len(buf) // self.psz):
        self.ioctl(6, block_num + i)
      offset = 0
    addr = block_num * self.psz + offset
    self.write_memory(addr, buf)

  def ioctl(self, op, arg):
    if op == 4:
      return self.read_flash_size()//self.psz
    if op == 5:
      return self.psz
    if op == 6:
      self.CM(addr=arg*self.psz)
      return 0



W25Q = Flasher

