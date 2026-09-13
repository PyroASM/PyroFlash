
def __getattr__(name):
  module = __import__(name+"_flash", globals(), locals(), [name], 1)
  value = getattr(module, name)
  globals()[name] = value
    
  return value