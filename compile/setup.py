#!/usr/bin/env python
# coding=utf-8
import asyncio
import compileall
import concurrent.futures
import os
import re
import shutil
import sysconfig
import time
from distutils.core import Extension, setup
from pathlib import Path

from Cython.Build import build_ext, cythonize
from Cython.Compiler import Options
from utils.patchlog import patch_log

# from Cython.Build.Dependencies import extended_iglob

# 1. 使用Cython编译的对象，不能同时使用静态装饰器和其他装饰器。

# 2. 编译后so不能重命名，使用Nuitka编译后也不能重命名----链接库的名字当然不能随便改。

# 3. 某py文件在某个版本后添加到exclude_so，需清理已有的so.

# 4. 关于patch_log.
#    编译so后，模块logging格式中的文件名和行号变为调用文件的: %(filename)s %(lineno)d；Cython和Nuitka都是如此。
#    可以将%(filename)s 从log格式中移除，而把原文件名作为消息内容，即patch_log；
#    如果仅关注异常，format_exc的文件名和行号在Cython和Nuitka都正常，前者显示出错语句，后者不显示；format_stack后者行号正常。
#    https://cython.readthedocs.io/en/latest/src/userguide/limitations.html#stack-frames
#    patch_log修改代码文件，故应把源码复制到新文件夹后在新文件夹编译。

# 5. 同一文件Nuitka编译出来435KB，Cython编译出来38KB；后者不支持dataclass装饰器；魔术变量__file__在两者中均正常。


so_sources = {"source", "core", "message", "utils"}  # 编译为so的源码目录
pyc_sources = set()  # 编译为pyc的源码目录

build_temp = "/tmp"  # gcc 编译时 创建，build_temp / build_dir : 存放用于链接的目标文件o文件，若build_dir是相对路径则可能创建/tmp/../buildc, 在 / 下创建/buildc
build_dir = "/tmp/buildc"  # 编译时生成的C文件目录，Cython 创建
build_lib = "/tmp/release"  # 编译的so输出目录，gcc 链接时 创建

# 不编译so的,递归匹配、路径匹配，由Cython调用glob模块实现
exclude_so = [
    "**/{nodevicetoverify,haserrortofix}/*.py",
    "core/example*.py",
    "**/__init__.py",
    "utils/progress.py",
]
# 不编译pyc的,路径中关键字匹配，由compileall调用re.search实现
exclude_pyc = {"/progress.py", "__init__.py"}
# 直接删除的文件，相对路径
exclude_rc = {
    "test",
    "setup.py",
    ".git",
    "source/dscanservice/depot/haserrortofix",
    "source/dscanservice/depot/nodevicetoverify",
}


class BuildExtWithoutPlatformSuffix(build_ext):
    def get_ext_filename(self, ext_name):
        filename = super().get_ext_filename(ext_name)
        return get_ext_filename_without_platform_suffix(filename)


def get_ext_filename_without_platform_suffix(filename):
    """原build_ext编译出的文件带cpython-37m-x86_64-linux-gnu后缀，此函数移除PEP 3147后缀"""
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


async def make_ext(file):
    """见说明4"""

    stinfo = os.stat(file)
    atime, mtime = stinfo.st_atime, stinfo.st_mtime
    cfile = Path(build_dir) / file.with_suffix(".c")
    if cfile.exists():
        cstinfo = os.stat(cfile)
        catime, cmtime = cstinfo.st_atime, cstinfo.st_mtime
    else:
        cmtime = 0
    if mtime > cmtime:
        await loop.run_in_executor(executor, patch_log, str(file))
    extensions.append(
        Extension(
            str(file.with_suffix("")).replace("/", "."),
            [str(file)],
            extra_compile_args=["-Os", "-g0"],
            extra_link_args=["-Wl,--strip-all"],
        )
    )


async def make():
    """使用多进程（文件操作）的协程生成协程任务"""

    global loop, executor
    loop = asyncio.get_running_loop()
    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        futures = map(make_ext, (f for folder in so_sources for f in Path(folder).rglob("*.py")))
        return await asyncio.gather(*futures)


start = time.time()
# 不使用增量编译。若使用增量编译，注释下三行；
shutil.rmtree(Path(build_temp) / build_dir, ignore_errors=True)
shutil.rmtree(Path(build_dir), ignore_errors=True)
shutil.rmtree(Path(build_lib), ignore_errors=True)
for f in Path(".").rglob("__pycache__"):
    shutil.rmtree(f, ignore_errors=True)
for f in Path(".").rglob("*.pyc"):
    if f.with_suffix(".py").exists():
        f.unlink()
for f in [Path(".") / x for x in exclude_rc]:
    if f.is_file():
        f.unlink()
    elif f.is_dir():
        shutil.rmtree(f, ignore_errors=True)

extensions = []
asyncio.run(make())
del loop, executor

# 配置编译, 所有指令见 Cython.Compiler.Options
Options.docstrings = False
Options.fast_fail = True

# 编译指令，Cython.Compiler.Options._directive_defaults
# annotation_typing：忽略类型标注。
compiler_directives = {
    "optimize.unpack_method_calls": False,
    "warn.unreachable": False,
    "emit_code_comments": False,
    "annotation_typing": False,
}

# nthreads: 基于多进程的并行任务，cpu核数*1.5
# language_level: python大版本号
# script_args: 来源于python3 setup.py build_ext --build-temp=/tmp --build-lib=../release
# --inplace 忽略build-lib和build-temp，在源代码目录创建build目录，并在代码的相同位置生成so
# build_dir非None且强制编译force=False时，下次编译对比py源码与build_dir中对应c文件的时间戳，增量编译
setup(  # name = 'scan_abc',
    cmdclass={"build_ext": BuildExtWithoutPlatformSuffix},
    ext_modules=cythonize(
        extensions,
        exclude=exclude_so,
        nthreads=6,
        force=True,
        quiet=False,
        build_dir=build_dir,
        language_level=3,
        compiler_directives=compiler_directives,
    ),
    script_args=f"build_ext --build-temp={build_temp} --build-lib={build_lib}".split(),
)

# 挑选编译完成的so
for folder in so_sources:
    for f in (Path(build_lib) / folder).rglob("*.so"):
        py_file = f.with_suffix(".py").relative_to(build_lib)
        dst_parent = f.relative_to(build_lib).parent
        if py_file.exists():
            py_file.unlink()
            shutil.copy(str(f), str(dst_parent))
        else:
            f.unlink()

exp = re.compile(r"{}".format("|".join(exclude_pyc)))
# 生成pyc并挑选
for folder in so_sources | pyc_sources:
    compileall.compile_dir(folder, force=True, rx=exp, legacy=True, quiet=1)
    for f in Path(folder).rglob("*.pyc"):
        py_file = f.with_suffix(".py")
        if py_file.exists():
            py_file.unlink()

print("用时", time.time() - start, "秒")
with open("__init__.py", "w") as f:
    f.write(f'rc_date="{time.strftime("%Y-%m-%dT%H:%M:%S")}"\n')
