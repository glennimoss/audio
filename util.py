import array
from itertools import islice
from functools import partial

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


_int16 = lambda f: int(f * 32767)
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
