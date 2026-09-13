
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
  def __init__(self, comm, *args, type=0, **kw):
    self.comm = comm
    self.type = type 
    super ().__init__(*args, autoclear=False, **kw)

  def start(self):
    self.SWIM = SWIM(self.comm,dbg=self.dbg)

    self.SWIM.start(type=self.type, dbg=self.dbg)

    self.dm = DM(comm=self.SWIM)
    self.dm.unlock()
    self.dm.stall_cpu()
    self.dm.print_regs()

    self.Flash= Flash (comm=self.SWIM)
    print (self.Flash.option_status())

    self.Flash.unlock_flash()
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
    

STM8 = Flasher 