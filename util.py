import array
from itertools import islice
from functools import partial, wraps

class classproperty (object):

  def __init__ (self, getter, instance_getter=None):
    self._getter = getter
    self._instance_getter = instance_getter

  def instance (self, func):
    self._instance_getter = func
    return self

  def __get__ (self, obj, class_):
    if obj is None or self._instance_getter is None:
      return self._getter(class_)
    return self._instance_getter(obj)

class cimethod:

  def __init__ (self, func, instance_func=None):
    self._func = func
    self.instance(instance_func)

  def instance (self, func):
    self._instance_func = func
    return self

  def __get__ (self, obj, class_):
    if obj is None or self._instance_func is None:
      func = self._func
    else:
      func = self._instance_func
    return partial(func, obj or class_)

  def __call__ (self, obj, *args, **kwargs):
    import pdb;pdb.set_trace()
    if isinstance(obj, type) or self._instance_func is None:
      func = self._func
    else:
      func = self._instance_func
    return func(obj, *args, **kwargs)


clamp = lambda x,l,h: min(max(l,x), h)
def _int16 (f):
  v = int(f * 32767)
  return v if -32767 <= v <= 32767 else clamp(v, -32767, 32767)

def chunk(iter, size):
  a = array.array('h', (0 for x in range(size)))

  while True:

    i = -1
    for i, samp in enumerate(islice(iter, size)):
      a[i] = _int16(samp)

    if i == -1:
      break

    if i < size -1:
      for i in range(i+1, size):
        a[i] = 0

    yield a

def byte_array (iter):
  return array.array('h', (_int16(s) for s in iter))


class NamedDescriptor:
  def __get__ (self, instance, owner):
    return getattr(instance, self.varname)

  def __set__ (self, instance, value):
    setattr(instance, self.varname, value)

class NamedMeta (type):
  def __new__ (cls, name, bases, namespace):
    for varname, var in namespace.items():
      if isinstance(var, NamedDescriptor):
        var.varname = '_' + varname
    return type.__new__(cls, name, bases, namespace)

def configable (func):
  @wraps(func)
  def fn (*args, **kwargs):
    if not args:
      return partial(func, **kwargs)
    return func(*args, **kwargs)
  return fn
