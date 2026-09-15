
from PyroFlash.Core.BaseFlasher import *

from PyroFlash.machine_stm8 import DM, Flash, SWIM

class Flasher (BaseFlasher):
  tsz = 255
  psz = 64
  wdelay = 100
  addr = 0x8000
  kw={}
  erased_value = 0
  pad_block=True
  autoclear=False # stm8 clears blocks that are going to flash 
  def __init__(self, comm, *args, type=0, **kw):
    self.SWIM = SWIM.SWIM(comm, **kw)
    self.type = type 
    super ().__init__(*args)

  def start(self):
    self.SWIM.start()

    self.dm = DM.DM(comm=self.SWIM)
    self.dm.unlock()
    self.dm.stall_cpu()
    self.dm.print_regs()

    self.Flash= Flash.Flash (comm=self.SWIM)
    print ("Options:", self.Flash.option_status())

    self.Flash.unlock_flash()
    print ("Flash unlocked, status:")
    self.Flash.print_status()

  def WM (self, addr, data):
    if super ().WM(addr, data): return

    self.Flash.block_write (addr, data)
    
  def RM(self, addr, sz=255):
    return self.SWIM.read(addr,sz)
    
  def CM(self, addr=None):
    self.Flash.erase_block(addr)

  def run(self):
    self.SWIM.swim_rst()

  def RU (self):
    self.Flash.rop_disable()
    

STM8 = Flasher 