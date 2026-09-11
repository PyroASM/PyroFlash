
import time

def slice (s, l, cb):
   n, r = divmod (len (s),l)

   for i in range (n):
     cb (l*i, s [l*i:l*(i+1)])
   if r > 0:
     cb (l*n, s [l*n:])


def bhex (v, l):
     v &= (1 << l*4)-1
     v = hex (v)[2:]
     while len (v) < l:
       v = "0"+v
     return v

def cleanhex(data):
  if type (data) is not str:
     data = data.hex()
  else:
   data = data.replace(" ","")
   data = data.replace("_","")
   data = data.replace ("\n","")
   data = data.replace ("\r","")
   
  return data

def toBytes(data):
    if isinstance (data, list):
      return bytearray(data)
    elif isinstance (data, str):
      data = cleanhex (data)
      return bytearray.fromhex (data)
    elif type (data) in (bytearray, bytes, memoryview):
      return data
    else:
      return bytearray([data])
  
def wBit (n, rnd=0):
  if n <= 1024:
    return str (n)+"B"
  elif n <= 2**20:
    n=round (n/(2**10),rnd)
    return str (n)+"K"
  elif n <= 2**30:
    n=round (n/(2**20),rnd)
    return str (n)+"M"
  elif n <= 2**40:
    n=round (n/(2**30),rnd)
    return str (n)+"G"
  elif n <= 2**50:
    n=round (n/(2**40),rnd)
    return str (n)+"T"
  else:
    return str(n)

def pad (b, sz, v=0xff):
  if len (b)==sz: return b
  if len (b)>sz: raise Exception ("pad error", len(b), sz)
  rv = bytearray (sz)
  rv[:len(b)]=b[:]
  for i in range (len(b),sz):
    rv[i]=v

  return rv


class BaseFlasher:
  wsz = None
  tsz = None 
  psz = None 
  wdelay = 100 
  erased_value = 0xff #option for STM8 (erased=0)
  pad_block=False
  id = None
  pages = None
  def __init__(self, dbg=0, log=print, psz=None, autoclear=True, **kwargs):
    if psz is not None:
      self.psz = psz
    self.autoclear = autoclear

    self.ch=0
    self.dbg=dbg
    self.base_addr=0

    self.start()

    self.print_flash_size()

  def log(self, *args):
   if self.dbg: print (*args)
    
  def start(self):
    pass

  def read_flash_size (self):
    pass

  def getPage(self,addr):
    addr -= self.flash_addr
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

  def writechar(self, data):
    data=toBytes(data)
    self.uart.write(data)
  
  def read(self, c):
    while self.uart.any()<c:
      pass
    return self.uart.read(c)
  
  def readchar(self):
   for i in range (10):
    rv = self.uart.read(1)
    if rv is None:
      time.sleep_ms (1)
    else:
      return rv [0]

   raise Exception ("no answer")

  def write (self, data):
    data=toBytes(data)
    self.uart.write(data)
    return len(data)
  
  def parse_SimpleVersion(self, line, write=True):
    if line== "":
       return

    if line[0] != ":":
      self.log ("Line doesn't start with ':'")
    
    ch=0
    for x in unhexlify (line[1:]):
      ch += x
    if (ch % 256)!= 0:
      self.log ("Invalid checksum")
    
    l=int(line[1:3],16)
    addr=int (line[3:7],16)
    cmd=line[7:9]
    
    data=line[9:-2]
    
    if l!=len(data)//2:
      self.log ("Invalid data length")
    
    if cmd=="00":
      if write:
        self.log ("writing " + hex(l) + " bytes at address " + hex(self.base_addr + addr))
        self.WM(self.base_addr+addr, data)
      return data
    elif cmd=="01":
      self.log ("Last line received")
      return False
    elif cmd=="04":
      self.base_addr=int(data[0:4],16) << 16
      self.log ("New base address got: " + hex(self.base_addr))
      return None
    else:
      print ("Unknown cmd", hex(cmd))
  
  bAddr = 0
  bData = ""
  def bWrite (self):
    if self.bData == "":
      return 
    self.vcw(self.base_addr+self.bAddr, self.bData)
    self.bData = ""

  def parseBlock(self, line):
    if line== "":
       return

    if line[0] != ":":
      self.log ("Line doesn't start with ':'")
    
    ch=0
    for x in unhexlify (line[1:]):
      ch += x
    if (ch % 256)!= 0:
      self.log ("Invalid checksum")
    
    l=int(line[1:3],16)
    addr=int (line[3:7],16)
    cmd=line[7:9]
    
    data=line[9:-2]
    
    if l!=len(data)//2:
      self.log ("Invalid data length")
    
    if cmd=="00":
      if self.bAddr != addr & 0xff00:
        self.bWrite()
        if addr % 0x100 == 0:
         self.bAddr = addr
         self.bData += data
         return data
      elif len (self.bData)//2 == addr % 0x100 and len (self.bData)//2 + len (data)//2 <= 256:
        self.bData += data
        return data
      else:
        self.bWrite()
        print ("Unaligned block, writing rest separately")
      self.vcw_memory(self.base_addr+addr, data)
      return data
    elif cmd=="01":
      self.bWrite()
      self.log ("Last line received")
      return False
    elif cmd=="04":
      self.bWrite()
      self.base_addr=int(data[0:4],16) << 16
      self.log ("New base address got: " + hex(self.base_addr))
      return None
    else:
      print ("Unknown cmd", cmd)

  def write_ihex(self, fname):
    f=open(fname)
    for line in f:
      data=self.parseBlock(line.strip())
    
    f.close()

  
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

  





  def flash (self, addr, file=None):
    if type (file) is str:
      file=open(file, "rb")
    elif file is None:
      file=RecievedFile()

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
     else: raise Exception ("Can't flash object of type: "+str(type(file)) )

     return

    


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





from sys import stdin
import select, time

import binascii

from micropython import RingIO

class RecievedFile:
  def __init__(self):
    self.p = select.poll()
    self.p.register(stdin, select.POLLIN)

    self.name=None
    #name = "/spiflash/out.txt"
    self.enc=True

    self.fifo = RingIO(16)

    self.buffer = bytearray(4)

    for i in range (10):
      t = self.p.poll(1)
      if len(t) == 0:
        break
      b = stdin.read(1)

    self.started = False 

    print("Base64 file uploader is waiting for data")

  def recv(self):
      if self.started:
        t = self.p.poll(1000)
        if len(t) == 0:
           return False
      self.started = True
      
      for i in range (4):
        b = stdin.read(1)

        if not b:
          break

        self.buffer[i] = ord(b)

        t = self.p.poll(1000)
        if len(t) == 0:
           break

      dst=binascii.a2b_base64(self.buffer)
      self.fifo.write(dst)
      return True 

  def read (self, bsz=None):
    rv = bytearray (bsz)
    for k in range (bsz):
      if not self.fifo.any():
        any =  self.recv()
        if not any:
          return rv[0:k]
      rv[k] = self.fifo.read(1)[0]
    return rv







