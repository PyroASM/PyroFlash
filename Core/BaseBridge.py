
class BaseBridge:
  def __init__(self, bsz=None, dbg=0):
    self.bsz = bsz
    self.dbg=dbg
  
  def write (self, addr, data, bsz=None):
    sz = len(data)
    bsz = bsz or self.bsz

    bcnt, rest = divmod(sz, bsz)

    for i in range (bcnt):
      o=bsz*i
      b=data[o:o+bsz]
      self.bwrite(addr+o, b)

    if rest:
      b=data[-rest:]
      self.bwrite(addr+bcnt*bsz, b)
    
  def read (self, addr, sz, bsz=None):
    rv = bytearray (sz)

    bsz = bsz or self.bsz

    bcnt, rest = divmod(sz, bsz)

    for i in range (bcnt):
      o=bsz*i
      rv[o: o+bsz] = self.bread (addr + o, bsz)

    if rest:
      rv[-rest:] = self.bread (addr + bsz*bcnt, rest)

    return rv
    
  def __getitem__(self, k):
    return self.bread(k, 1)[0]

  def __setitem__(self, k, v):
    self.bwrite(k, v.to_bytes(1))





class Val:
  def __init__ (self, addr, sz = 1, mem8=None):
    self.addr = addr
    self.sz = sz
    self.mem8 = mem8

  def readInt (self, addr, n):
     rv = 0
     for i in range (n):
        rv = rv << 8
        rv |= self.mem8[addr+i]
     return rv

  def writeInt (self, addr, n, v, lsFirst=False):
     r = range (n)
     if lsFirst:
        r = reversed (r)
     for i in r:
        j = n - 1 - i
        self.mem8[addr+i]= v >> j

  def bset (self, bit, val=1):
     t = self.mem8[self.addr]
     t &= ~(1<<bit)
     val &= 1
     t |= val << bit
     t &= 0xff
     self.mem8[self.addr]= t

  def bres (self, bit, val=0):
     t = self.mem8[self.addr]
     t &= ~(1<<bit)
     val &= 1
     t |= val << bit
     t &= 0xff
     self.mem8[self.addr]= t


  def write (self, src):
    self.writeInt (self.addr, self.sz, src)
    
  def read (self):
    return self.readInt (self.addr, self.sz)

  def __str__(self):
    return hex(self.read())




class RemotePerif:
  mem8 = None
  def __init__(self,mem8=None):
    if mem8:
      self.mem8 = mem8

    if self.mem8 is None:
       raise Exception ("Any RemotePerif needs SWIM object to be created first")

  def defregs (self, s=None, b=None):
   base = b or self.base

   s = s.replace("  ", " ")
   o = -1
   for n in s.split(" "):
    o += 1
    if n == ".":
      reg = None
    elif n == "*":
      reg.sz += 1
    else:
      reg = Val (base+o, mem8=self.mem8)
      setattr (self, n, reg)

  