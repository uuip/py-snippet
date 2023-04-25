# coding=utf-8

import pefile

########################################################################


def getversion(filename):
    pe = pefile.PE(filename, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
    )
    FileVersionMS = pe.VS_FIXEDFILEINFO.FileVersionMS
    FileVersionLS = pe.VS_FIXEDFILEINFO.FileVersionLS
    FileVersion = (
        FileVersionMS >> 16,
        FileVersionMS & 0xFFFF,
        FileVersionLS >> 16,
        FileVersionLS & 0xFFFF,
    )
    locver = ".".join(str(x) for x in FileVersion)
    return str(locver)


from win32com.client import Dispatch

parser = Dispatch("Scripting.FileSystemObject")
version = parser.GetFileVersion(filename)

from win32api import GetFileVersionInfo, LOWORD, HIWORD


def get_version_number(filename):
    try:
        info = GetFileVersionInfo(filename, "\\")
        ms = info["FileVersionMS"]
        ls = info["FileVersionLS"]
        return HIWORD(ms), LOWORD(ms), HIWORD(ls), LOWORD(ls)
    except:
        return "Unknown version"
