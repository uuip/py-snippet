from collections import defaultdict

import xlwings as xw
from 制作表格.device_type import Type
from 制作表格.device_vendor import Manufacturer

sht = xlwings.sheets.active

for i, v in enumerate(sht["a1:a8"].value):
    if v:
        sht["b" + str(i + 1)].value = "前方单元格非空"


def en2cn(dev_type, en_name):
    if not en_name:
        return
    for x in dev_type.__dict__.values():
        if type(x) is dict and x.get("name", "").lower() == en_name.lower():
            return x.get("namecn", en_name)
    return en_name


def hanyu(item: str):
    if item.startswith("相同特征的"):
        return 1
    else:
        return 0


sh = xw.sheets.active
r = defaultdict(lambda: defaultdict(set))

for x in sh.used_range.rows:  # type:xw.RangeRows
    if not all(x[0:2].value):
        print(x, "error")
        continue
    if x[1].value.startswith(x[0].value):
        fname = x[1].value
    else:
        fname = f"{x[0].value}/{x[1].value}"
    vendor = en2cn(Manufacturer, x[2].value)
    product = en2cn(Type, x[4].value)
    r[fname][vendor].add(product)

for k, v in r.items():
    line = []
    for kk, vv in v.items():
        if vv == {None}:
            desc = f"{kk}的产品"
        else:
            vv = vv - {None}
            if kk:
                desc = f'{kk}的{"、".join(vv)}'
            else:
                desc = f'相同特征的{"、".join(vv)}'
        line.append(desc)
    line.sort(key=hanyu)
    print(f"{'，'.join(line)}\t{k}")
