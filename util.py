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


