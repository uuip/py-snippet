import sys
from importlib.abc import SourceLoader, MetaPathFinder, Loader
from importlib.machinery import ModuleSpec
from pathlib import Path


class HookFinder(MetaPathFinder):
    def find_spec(self, full_name, paths, target=None):
        if full_name == "requests.adapters":
            filename = Path(paths[0]) / "adapters.py"
            loader = HookLoader()
            loader.__int__(filename)
            return ModuleSpec(full_name, loader, origin=paths)

            # from importlib.util import spec_from_file_location
            # loader = HookSourceLoader(full_name,str(filename))
            # return spec_from_file_location(full_name,filename,loader=loader)


class HookLoader(Loader):
    def __int__(self, filename):
        self.filename = filename

    def exec_module(self, module):
        with open(self.filename) as f:
            data = f.read()
        # data = data.replace('DEFAULT_POOLSIZE = 10', 'DEFAULT_POOLSIZE = 2')
        exec(data, vars(module))
        module.DEFAULT_POOLSIZE = 2


class HookSourceLoader(SourceLoader):
    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path

    def get_filename(self, fullname):
        return self.path

    def get_data(self, filename):
        with open(filename) as f:
            data = f.read()
        if self.fullname == "requests.adapters":
            data = data.replace("DEFAULT_POOLSIZE = 10", "DEFAULT_POOLSIZE = 3")
        return data


def install_hook():
    sys.meta_path.insert(0, HookFinder())
