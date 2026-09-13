
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


def decode_ihex_line (line):
    line = line.strip()

    if line== "":
       return

    if line[0] != ":":
      raise Exception ("Line doesn't start with ':' "+ str(line))
    
    checksum = 0
    packet = bytearray.fromhex(line[1:])
    for x in packet:
      checksum += x
    checksum %= 256
    if checksum != 0:
      raise Exception ("Invalid checksum: " +hex(checksum))
    
    length = packet [0]
    offset = int.from_bytes(packet [1:3], "big")
    cmd = packet [3]
    
    data = packet [4:-1]
    
    if length != len(data):
      raise Exception ("Invalid data length")
    
    if cmd==0:
      return offset, data
    elif cmd==1:
      return None, None
    elif cmd==4:
      base_addr = int.from_bytes(data, "big") << 16
      return None, base_addr
    else:
      raise Exception ("Unknown cmd", hex(cmd))
  
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






import select, time, binascii
from sys import stdin
from micropython import RingIO

class RecievedFile:
  def __init__(self):
    try:
      import pyb
      usb = pyb.USB_VCP()
      usb.init(flow=pyb.USB_VCP.RTS | pyb.USB_VCP.CTS)
    except:
      pass


    self.p = select.poll()
    self.p.register(stdin, select.POLLIN)

    self.addr = None
    self.enc=None

    self.fifo = RingIO(1023)

    self.buffer = bytearray(4)
    self.bidx= 0

    self.line = ""

    self.flush_stdin()

    self.started = False

    print("File uploader is waiting for ihex or base64 data")


  def flush_stdin (self):
    for i in range (10):
      t = self.p.poll(1)
      if len(t) == 0:
        break
      b = stdin.read(1)

  def poll (self):
    t = self.p.poll(1000)
    if len(t) == 0:
      return False
    return True

  def detect_encoding(self):
    b = stdin.read(1)
    if b == ":":
      self.enc = "ihex"
      self.line = b
    else:
      self.enc = "base64"
      self.put_byte_b64(b)

    print (self.enc, "detected")


  def recv(self):
    if self.started:
      if not self.poll():
        return False 
    else:
      self.detect_encoding()

    self.started = True
    
    if self.enc == "base64":
      for i in range (self.bidx, 4):
        b = stdin.read(1)

        if not b:
          break

        self.put_byte_b64 (b)

        if not self.poll():
           break
    else:
      line = stdin.readline()
      if self.line:
        line = self.line + line
        self.line = ""
      offs, data = decode_ihex_line (line)
      if offs is None:
       if data is None:
        print ("ihex last cmd (2) received")
        return False
       else:
        self.base_addr = data
        return self.recv()  # we need to return some data after addr stage 
      elif data is not None:
        self.fifo.write(data)

    return True

  def put_byte_b64 (self, b):
     self.buffer[self.bidx] = ord(b)
     self.bidx += 1
     if self.bidx == 4:
       dst=binascii.a2b_base64(self.buffer)
       self.fifo.write(dst)
       self.bidx = 0
     
  def read (self, bsz=None):
    rv = bytearray (bsz)
    for k in range (bsz):
      if not self.fifo.any():
        any =  self.recv()
        if not any:
          return rv[0:k]
      rv[k] = self.fifo.read(1)[0]
    return rv

  
  
