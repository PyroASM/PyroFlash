from ..BaseBridge import *

class DM (RemotePerif):
  RAM = 0
  ROM = 1
  FLASH = 2
  def __init__ (self,*args, comm=None):
     super ().__init__(comm, *args)
     self.base = 0x7f00
     self.mode= 1
     self.defregs (b=0x7f00, s="A PC * * X * Y * SP * CC")
     self.defregs (b=0x7f80, s="SWIM_CSR")
     self.defregs (b=0x7f90, s="BKR1 * * BKR2 * * CR1 CR2 CSR1 CSR2 ENFCTR")

  def unlock(self):
    self.SWIM_CSR.write (0x25)#dm srst prior
    print ("got access with SWIM_CSR status", hex(self.SWIM_CSR.read()))

  def remap_ivt (self, dst):
     if dst == self.RAM:
        self.CR2.write (1)
     elif dst == self.ROM:
        self.CR2.write (4)
     else:
        self.CR2.write (0)

  def stall_cpu (self, val=1):
    self.CSR2.bset(3, val)

  def flush_cpu (self):
    self.CSR2.bset(0)
  
  def int_lvl (self, v):
    self.CC.bset(3, v)
  
  def run (self, addr):
     self.stall_cpu (1)
     self.PC.write (addr)
     self.flush_cpu()
     self.stall_cpu (0)
   
  def reset (self):
     self.stall_cpu (1)
     self.PC.write (0)
     self.flush_cpu()
  
  def print_regs (self):
     print ("A: ", str(self.A))
     print ("PC:", str (self.PC))
     print ("X: ", self.X)
     print ("Y: ", self.Y)
     print ("SP:", self.SP)
     
     v = self.CC.read ()
     
     rv = ""
     rv += " I1="+str((v>>5)&1)
     rv += " I0="+str((v>>3)&1)
     rv += " "
     rv += " V="+str((v>>7)&1)
     rv += " H="+str((v>>4)&1)
     rv += " "
     rv += " N="+str((v>>2)&1)
     rv += " Z="+str((v>>1)&1)
     rv += " C="+str((v>>0)&1)
     print (rv)
     
     print ("----")

