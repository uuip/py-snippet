# coding=utf-8
#
# 编译为二进制, 不指定standalone或者onefile模式，生成的exe的pythonhome为固定值, onefile模式单文件太大
#python -m nuitka  program.py
python -m nuitka --enable-plugin=pyside6 --enable-plugin=numpy --windows-disable-console --windows-icon-from-ico=app.ico --include-data-file=app.ico= --standalone  main.py

# 编译为扩展，不如cython编译的体积小
python -m nuitka  --module main_ui.py
