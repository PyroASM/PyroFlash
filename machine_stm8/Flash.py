from PyroFlash.Core.BaseBridge import *

import time

class Flash(RemotePerif):
  def __init__ (self, *args, comm=None):
    super ().__init__(comm, *args)
    self.base = 0x505a
    self.defregs ("CR1 CR2 NCR2 FPR NFPR IAPSR . . PUKR . DUKR")
    self.blocksz = 64

  def rop_disable(self):
    self.unlock_data()
    self.option_write (bytearray.fromhex("0000ff00ff00ff00ff00ff"))
    print ("new option status", self.option_status())

  def print_status(self):
     flags = self.IAPSR.read()
     flags = bin (flags)
     print ("HVOFF:", flags [-7])
     print ("DUL:", flags [-4])
     print ("EOP:", flags [-3])
     print ("PUL:", flags [-2])
     print ("WR_PG_DIS:", flags [-1])
  
  def unlock_flash(self):
    self.PUKR.write(0x56)
    self.PUKR.write(0xae)
  
  def unlock_data(self):
    self.DUKR.write(0xae)
    self.DUKR.write(0x56)
 
  def block_write(self, addr, block):
    self.CR2.write(0x01)
    self.NCR2.write(0xfe)

    if len (block)<64:
      b=bytearray (64)
      b[:len(block)]=block [:]
      block=b
    
    for i,b in enumerate (block):
      self.mem8.bwrite (addr+i, b)

    time.sleep_ms(100)

  def poll (self):
    return self.IAPSR.read() & 4

  def word_write (self, addr, w):
    self.CR2.write(0x40)
    self.NCR2.write(0xbf)
   
    self.mem8.bwrite(addr, w.to_bytes(4,"big"))

    time.sleep_ms(100)

  def erase_block (self, addr):
    self.CR2.write(0x20)
    self.NCR2.write(0xdf)
   
    self.mem8.bwrite(addr, bytearray (4))

    time.sleep_ms(100)
  
  def byte_write (self, addr, b):
    self.mem8.bwrite(addr,b)

    time.sleep_ms(100)
  
  def option_write (self, block):
    addr = 0x4800
    
    self.CR2.write(0x80)
    self.NCR2.write(0x7f)

    for i,b in enumerate (block):
      self.byte_write (addr+i, b)
      time.sleep_ms(100)
   
  def option_status (self):
    v = self.read (0x4800, 11)
    return v


  def read (self, addr, l):
    rv = self.mem8.read(addr,l)
    return rv.hex()
