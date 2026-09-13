
import time
from .util import *

class BaseFlasher:
  wsz = None
  tsz = None 
  psz = None 
  wdelay = 100 
  erased_value = 0xff #option for STM8 (erased=0)
  autoclear = True
  pad_block=False
  id = None
  pages = None
  def __init__(self):
    self.start()
    self.print_flash_size()

  def start(self):
    pass

  def read_flash_size (self):
    pass

  def getPage(self,addr):
    addr -= self.addr
    return addr//self.psz, self.psz

  def print_flash_size (self):
    rv = self.read_flash_size()
    if rv:
      print ("Flash size:",rv//1024,"KB")
    else:
      print ("Flash size unknown")

  def is_erased (self, data):
    for b in data:
      if b != self.erased_value: return False
    return True

  def WM (self, addr, data):
    if self.is_erased(data):
      print (hex(addr), wBit(len (data)), "skip "+hex(self.erased_value))
      return True
    print (hex(addr), wBit(len (data)))
    return False

  
  

  
  def verify_memory(self, addr, data):
    rdata = self.read_memory (addr, len (data))
    res = rdata == data
    if res is False and self.is_erased(rdata):
      res = None
    return res
   
  def read_memory (self, addr, sz):
    rv = bytearray (sz)

    bsz = self.tsz

    bcnt, rest = divmod(sz, bsz)

    for i in range (bcnt):
      o=bsz*i
      rv[o: o+bsz] = self.RM (addr + o, bsz)

    if rest:
      rv[-rest:] = self.RM (addr + bsz*bcnt, rest)

    return rv
    
    

  def vcw (self, addr, data, clear=False):
   #Verify Clear Write 
   res = self.verify_memory (addr, data)
   if res is True:
     print (hex (addr), wBit(len (data)), "same")
   else:
     if res is False:
      if clear:
        self.CM (addr)
      elif self.autoclear:
        print ("Flash", self.read_memory (addr, len (data)))
        print ("data", data)
        raise Exception (str(hex(addr))+" is not erased")

     self.write_memory(addr, data)
  
  def vcw_memory(self, addr, data, clear=False):
     data = toBytes (data)
     
     if self.pages is not None: #case for f411
      pagen, psz = self.getPage(addr)
      pages = self.pages[self.id]

      bsz = self.psz
     
      if pagen < len(pages):
      #slice over variable sized pages (f411)
       for psz in pages [pagen:]:
        bsz*=1024
        if len(data) >= bsz:
         self.vcw (addr, data[:bsz], clear=clear)
         addr+=bsz
         data= data[bsz:]
        elif len(data)==0: return
        else:
         self.vcw (addr, data, clear=clear)
         return
       if len(data)==0: return
       
     slice (data, self.psz, lambda po, page :
     self.vcw (addr+po, page, clear=clear))
     

  def write_memory(self, addr, data):
     data = toBytes (data)
     
     sz = min(self.psz,self.tsz)

     if self.pad_block:
      data = pad(data, sz, self.erased_value)

     slice (data, sz, lambda o, d : self.WM (addr+o,d))

  





  def flash (self, file=None, addr=None):
    if type (file) is int:
      file, addr = addr, file

    if type (file) is str:
      file=open(file, "rb")
    elif file is None:
      file=RecievedFile()
      file.recv()  # if ihex retrive addr
      if file.enc == "ihex":
        addr = file.addr

    if addr is None:
      addr = self.addr  # default base addr for this MCU 

    if hasattr (file, "read"):
     while True:
      page, self.psz=self.getPage(addr)
     
      bsz = self.psz
      d = file.read (bsz)
      if len(d) == 0: break 
      self.vcw_memory (addr, d, clear=self.autoclear)
      addr += bsz

    elif type (file) in (bytearray, bytes, memoryview):
     if type (file) is not memoryview: file=memoryview (file)
     o = 0
     while True:
      if o >= len(file):
        break

      page, self.psz=self.getPage(addr)
     
      bsz = self.psz
      if o+bsz <= len(file):
       d = file [o:o+bsz]
      elif o < len(file):
       d = file [o:]
      else:
       raise Exception ("flash offset error")
      
      self.vcw_memory (addr, d, clear=self.autoclear)
      addr += bsz
      o += bsz

    else:
     raise Exception ("Can't flash object of type: "+str(type(file)) )

    return

    


  