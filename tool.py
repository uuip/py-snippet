#!/usr/bin/env python
# -*- coding:utf-8 -*-
import codecs
import re
from decimal import Decimal, ROUND_HALF_UP
from html import unescape

from urllib.parse import unquote


def down4up5(num, prec=0):
    # round四舍五入不准
    return Decimal(str(num)).quantize(Decimal("0.{}".format("0" * prec)), rounding=ROUND_HALF_UP)


# 检查None及空对象
a = [None, "", None, "444"]
a = list(map(lambda x: "" if not x else x, a))
print(a)
# 移除None及空对象
a = list(filter(None, a))
print(a)


def _sub_getitem(self, k):
    try:
        # sub.__class__.__bases__[0]
        real_val = self.__class__.mro()[-2].__getitem__(self, k)
        val = "" if real_val is None else real_val
    except Exception:
        val = ""
        real_val = None
    # isinstance(Avoid,dict)也是true，会一直递归死
    if type(val) in (dict, list, str, tuple):
        val = type("Avoid", (type(val),), {"__getitem__": _sub_getitem, "pop": _sub_pop})(val)
        # 重新赋值当前字典键为返回值，当对其赋值时可回溯
        if all([real_val is not None, isinstance(self, (dict, list)), type(k) is not slice]):
            self[k] = val
    return val


def _sub_pop(self, k=-1):
    try:
        val = self.__class__.mro()[-2].pop(self, k)
        val = "" if val is None else val
    except Exception:
        val = ""
    if type(val) in (dict, list, str, tuple):
        val = type("Avoid", (type(val),), {"__getitem__": _sub_getitem, "pop": _sub_pop})(val)
    return val


class DefaultDict(dict):
    """Key不存在时不会报错，返回空字符串，主要是为了取值。官方库的defaultdict处理嵌套字典时太伤神。"""

    def __getitem__(self, k):
        return _sub_getitem(self, k)

    def pop(self, k):
        return _sub_pop(self, k)


class DefaultDictRec(dict):
    """记录访问过的Key"""

    def __init__(self, d: dict):
        super().__init__(d)
        self.r = d.copy()
        self.read = set()

    def __getitem__(self, k):
        self.read.add(k)
        return _sub_getitem(self, k)

    def pop(self, k):
        return _sub_pop(self, k)

    def remains(self):
        for x in self.read:
            if x in self.r:
                self.r.pop(x)
        return self.r


def merge(d1, d2):
    """把字典2合并到字典1，字典1的内容更新或者增加，应用于嵌套字典不能用update的情况"""

    for k in d2:
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
            merge(d1[k], d2[k])
        else:
            d1[k] = d2[k]


charRE = re.compile(r'<\s*meta[^>]+charset\s*=\s*[\'"]?([^\'">]*?)[ /;\'"]'.encode(), re.I)


def decode_content(content: bytes, is_html=False, fallback=False):
    """对字节解码"""

    # UnicodeDammit在cchrdet和chrdet都存在时取前者，前者性能好但准确率不如后者。
    # UnicodeDammit判断文件的bom时有问题,utf8+bom应当返回utf_8_sig，实际返回了utf8
    def codinglist(content=content, is_html=is_html):
        # ISO-8859-1 (Latin-1) 与 Windows-1252 (CP1252)不同在于128-159 (0x80-0x9F).
        bom_map = {
            codecs.BOM_UTF8: "utf_8_sig",
            codecs.BOM_UTF16_BE: "utf_16_be",
            codecs.BOM_UTF16_LE: "utf_16_le",
        }
        bom = bom_map.get(content[:2]) or bom_map.get(content[:3])
        if bom:
            yield bom
        if is_html:
            se_charset = charRE.search(content)
            if se_charset:
                html_code = se_charset.groups()[0].decode(errors="ignore").strip()
                if html_code:
                    yield html_code
        yield "utf-8"
        yield "gb18030"
        for m in ["cchardet", "chardet"]:
            import sys

            try:
                __import__(m)
            except Exception:
                continue
            else:
                cc_code = sys.modules[m].detect(content)["encoding"]
                if cc_code:
                    yield cc_code
        if fallback:
            yield "latin-1"

    if type(content) is not bytes:
        return content

    for c in codinglist(content, is_html):
        try:
            dst = content.decode(c)
            if is_html:
                try:
                    dst = unquote(unescape(dst))
                    # \u1234格式：
                    # dst=dst.encode('utf8').decode('unicode-escape')
                except Exception:
                    pass
            return dst
        except Exception:
            continue

    return content.hex()  # 'latin_1'虽不出错，但乱码，不如只用16进制表示好看
