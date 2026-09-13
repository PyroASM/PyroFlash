
from PyroFlash.Core.BaseFlasher import *

class Flasher (BaseFlasher):
  ACK=0x79
  NACK=0x1f

  tsz = 256
  psz = None
  wdelay = 100

  addr = 0x800_0000

  id = None

  flash_sz_offset = {
    0x0410: 0x1fff_f7e0,
    0x0431: 0x1fff_7a22,
  }

  #reusing last value to the end 
  pages = {
    0x410: [1],
    0x431: [16,16,16,16,64,128,128,128],
  }

  def getPage (self, addr):
    addr -= self.addr
    plist = self.pages[self.id]
    i= 0
    for psz in plist:
     psz*=1024
     if addr<psz: return i,psz
     addr -= psz
     i+= 1

    #reusing last psz value for rest
    n,r = divmod (addr,psz)
    return i+n,psz
  def __init__(self, comm, *args, **kwargs):
    
    if type(comm) is int:
      from machine import UART
      comm = UART(comm)

    self.comm = comm

    kw = {"baudrate":250000, "stop":1, "bits":8, "parity":0, "timeout": 100, "rxbuf":1024}
    kw.update (kwargs)
    
    self.comm.init(**kw)

    self.checksum = 0

    super ().__init__()

  def start(self):
    for i in range (5):
      self.writechar(0x7f)
      time.sleep_ms (100)

      any = self.comm.any()
      if any == 0:
        print ("Retry:", i, "no ans")
        continue 
      elif any > 1:
        self.comm.read (any - 1)

      ans = self.readchar()

      print ("Retry:", i)
      print ("ans:",hex(ans))
      print ("bytes skipped:", any-1)
      if ans == self.ACK:
        print ("Connected")
        break 
      elif ans == self.NACK:
        print ("Already connected")
        break
    else:
      raise Exception ("Connection failed")

    self.GET()
    self.GET_ID()

    #if self.dbg : return 

    #if self.id == 0x431:
    #  self.WM(0xffff_0000,"03") #flash voltage settings 

 
  def writechar (self, data):
    data=data.to_bytes(1)
    self.comm.write(data)

  def write (self, data, send_checksum = False):
    data=toBytes(data)
    
    self.comm.write(data)
    
    for x in data:
      self.checksum ^= x
    if send_checksum:
      self.writechar(self.checksum)
      self.checksum=0
  
  
  def read (self, c):
    while self.comm.any()<c:
      pass
    return self.comm.read(c)
  
  def readchar (self):
   for i in range (10):
    rv = self.comm.read(1)
    if rv is None:
      time.sleep_ms (1)
    else:
      return rv [0]

   raise Exception ("no answer")

  def ans(self, e = False, req=ACK):
    ans=self.readchar()
    if ans==req:
      return True
    elif ans==self.NACK:
      if e:
        raise Exception ("Bad answer: NACK")
      else:
        print ("Bad answer: NACK")
      return False 
    else:
      if e:
        raise Exception ("Bad answer: " + hex(ans))
      else:
        print ("Bad answer: " + hex(ans))
      return False

  
  def write_cmd(self, cmd, ans=True):
    if self.comm.any():
      print ("write_cmd WARNING: UART buffer is not empty:",self.comm.read().hex())

    self.writechar(cmd)
    self.writechar(0xff^cmd)
    if ans:
      self.ans(True)


      
  def WM (self, addr, data):
    if super ().WM(addr, data): return 

    self.write_cmd(0x31)
    
    self.write(addr.to_bytes(4,"big"), True)
    self.ans(True)
    
    self.writechar(len(data)-1)
    self.write(data, True)
    self.ans(True)
    time.sleep_ms (self.wdelay)
    
  def RM(self, addr, len=256):
    self.write_cmd(0x11)

    self.write(addr.to_bytes(4,"big"), True)
    self.ans(True)
    
    self.write_cmd(len-1, ans=False)  # send len and ~len
    self.ans(True)
    
    data=self.read(len)
    return data
    
  def EM(self, addr=None):
    self.write_cmd(0x43)
    if addr is None:
       # erase all
      self.write ([0xff], True)
    else:
       # erase one page at a time 
      page, psz = self.getPage(addr)
      self.write ([0, page], True)
    time.sleep_ms (self.wdelay)
    self.ans(False)

  def EEM (self, addr=None):
    self.write_cmd(0x44)
    if addr is None:
      # erase all
      self.write ([0xff,0xff], True)
    else:
      # erase one page at a time 
      page, psz = self.getPage(addr)
      self.write ([0, 0, page>>8, page&0xff], True)
    time.sleep_ms (self.wdelay)
    self.ans(False)

  CM = EM  # using EM by default, autodetect on GET cmd

  def WP (self, page):
    self.write_cmd(0x63)
    
    self.write ([0, page], True)
    time.sleep_ms (self.wdelay)
    self.ans(True)

  def WU (self, page=None):
    self.write_cmd(0x73)
    time.sleep_ms (self.wdelay)
    self.ans(True)
    time.sleep_ms (self.wdelay)
    self.ans(True)

  def RP (self, page=None):
    self.write_cmd(0x82)
    time.sleep_ms (self.wdelay)
    self.ans(True)
    time.sleep_ms (self.wdelay)
    self.ans(True)
  
  def RU (self, page=None):
    self.write_cmd(0x92)
    time.sleep_ms (self.wdelay)
    self.ans(True)
    time.sleep_ms (self.wdelay)
    self.ans(True)

  def GO (self, addr):
    self.write_cmd(0x21)
    
    self.write (addr.to_bytes(4,"big"), True)
    self.ans ()

  def run (self):
    data = self.RM (self.addr + 4,4)  # read reset vector 

    addr = int.from_bytes(data[0:4], "little")
    print ("Starting from", hex(addr))

    self.GO (addr)
  
  def GET (self):
    self.write_cmd (0x00)

    len=self.read(1)[0]+1
    data=self.read(len)

    i = 0
    cmd = {
       0:"GET",
       1:"GET VER",
       2:"GET ID",
       0x11: "READ MEMORY",
       0x21: "GO",
       0x31: "WRITE MEMORY",
       0x43: "ERASE",
       0x44: "EXT. ERASE",
       0x63: "WRITE PROTECT",
       0x73: "WRITE UNPROTECT",
       0x82: "READOUT PROTECT",
       0x92: "READOUT UNPROTECT"
    }
    
    for d in data:
      if i == 0:
        print ("ver:", hex (d))
      elif d in cmd:
        print ("cmd:", hex (d), cmd [d])
      else:
        print ("cmd:", hex (d), "(unknown)")
      i += 1

    if 0x44 in data:
      self.CM = self.EEM
      print ("Using extended erase cmd")

    self.ans()

  def GET_ID (self):
    self.write_cmd (0x02)

    len=self.readchar() + 1
    data=self.read(len)

    self.id = int.from_bytes(data[0:2], "big")

    print ("id:",hex(self.id))
    if len > 2:
     print ("Extra data got", data.hex())

    self.ans()

  def read_flash_size(self):
   if self.id in self.flash_sz_offset:

    offs = self.flash_sz_offset[self.id]
    offsH = offs & 0xffff_ff00
    ln = offs-offsH+2
    rv = self.read_memory(offsH,ln)
    rv = int.from_bytes(rv[-2:], "little")
    return rv*1024

   else:
    print ("Unknown id")
    return 0

STM32 = Flasher 