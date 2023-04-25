#!/usr/bin/env python
# coding=utf-8
import os
import shutil
import sysconfig
from pathlib import Path

from Cython.Build import build_ext, cythonize
from Cython.Compiler import Options
from setuptools import Extension, setup

so_sources = {"pocs"}
# exclude_so = ['**/{nodevicetoverify,errortofix}/*.py', '**/__init__.py']
exclude_so = []


class NewBuildExt(build_ext):
    def get_ext_filename(self, ext_name):
        """原build_ext编译出的文件带cpython-37m-x86_64-linux-gnu后缀，此函数移除PEP 3149后缀"""
        filename = super().get_ext_filename(ext_name)
        name, ext = os.path.splitext(filename)
        ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
        if ext_suffix == ext:
            return filename
        ext_suffix = ext_suffix.replace(ext, "")
        idx = name.find(ext_suffix)
        if idx == -1:
            return filename
        else:
            return name[:idx] + ext

    def get_export_symbols(self, ext):
        # return []
        names = ext.name.split(".")
        if names[-1] != "__init__":
            initfunc_name = "PyInit_" + names[-1]
        else:
            initfunc_name = "PyInit_" + names[-2]
        if initfunc_name not in ext.export_symbols:
            ext.export_symbols.append(initfunc_name)
        return ext.export_symbols


Options.docstrings = False
Options.fast_fail = True
compiler_directives = {
    "optimize.unpack_method_calls": False,
    "warn.unreachable": False,
    "emit_code_comments": False,
    "annotation_typing": False,
}
extensions = []
for f in Path(".").rglob("__pycache__"):
    shutil.rmtree(f, ignore_errors=True)
for folder in so_sources:
    for file in Path(folder).rglob("*.py"):
        extensions.append(
            Extension(
                str(file.with_suffix("")).replace(os.sep, "."),
                [str(file)],
                extra_compile_args=["-Os", "-g0"] if os.name == "posix" else ["/GS-"],
                extra_link_args=["-Wl,--strip-all"]
                if os.name == "posix"
                else ["/subsystem:console"],
            )
        )

if __name__ == "__main__":
    setup(
        cmdclass={"build_ext": NewBuildExt},
        ext_modules=cythonize(
            extensions,
            exclude=exclude_so,
            nthreads=6,
            force=True,
            quiet=False,
            build_dir="build",
            language_level="3str",
            compiler_directives=compiler_directives,
        ),
        script_args=f"build_ext --inplace".split(),
    )
