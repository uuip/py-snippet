import inspect
import pkgutil
from importlib import import_module


def load_module(paths, prefix):
    for i, modname, ispkg in pkgutil.walk_packages(paths, prefix):
        try:
            m = import_module(modname)
            for name, obj in inspect.getmembers(
                m, lambda obj: inspect.isclass(obj) and hasattr(obj, "process")
            ):
                yield obj
        except Exception:
            print("WARNING: unable to import %s" % modname)
