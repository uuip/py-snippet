#!python3
# coding=utf8
import ipaddress
import re
from ipaddress import IPv4Address, IPv4Network

error_list = []
reg1 = r"^(\d{1,3}\.){3}\d{1,3}$"  # 1.2.4.8
reg2 = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"  # 1.2.4.0/24
reg3 = r"^(\d{1,3}\.){3}\d{1,3}\-\d{1,3}$"  # 10.1.2.40-41
reg4 = r"^(\d{1,3}\.){3}\d{1,3}\-(\d{1,3}\.){3}\d{1,3}$"  # 120.192.20.0-120.192.21.255


# 10.156.224.1-225.254 这种格式数量不多,手工转换为reg4
def reslove(ip):
    # 分析单独的ip行
    netlist = set()
    ip_ = ip.strip()
    ip = ip.replace(" ", "").replace("--", "-").strip()
    if not ip:
        return netlist
    if re.fullmatch(reg1, ip):
        try:
            netlist.add(IPv4Address(ip))
        except ipaddress.AddressValueError:
            print(ip_, "错误的IPv4Address格式")
            error_list.append(ip_)
    elif re.fullmatch(reg2, ip):
        try:
            netlist.add(IPv4Network(ip, strict=False))
        except ipaddress.NetmaskValueError:
            newip = ip.replace("/", "-")
            print(ip_, "掩码格式错误,可能是连字符- 以", newip, "重试")
            netlist.update(reslove(newip))
    elif re.fullmatch(reg3, ip):
        ip1, ip2_end = ip.split("-")
        ip2 = ".".join(ip1.split(".")[:-1]) + "." + ip2_end
        netlist.update(reslove(ip1 + "-" + ip2))
    elif re.fullmatch(reg4, ip):
        try:
            ip1, ip2 = map(IPv4Address, ip.split("-"))
        except:
            print(ip_, "错误的IP范围格式")
            error_list.append(ip_)
        if ip1 <= ip2:
            if str(ip1).endswith(".1"):
                ip1 -= 1
            if str(ip2).endswith(".254"):
                ip2 += 1
            netlist.update(ipaddress.summarize_address_range(ip1, ip2))
        else:
            print(ip_, "结束地址小于起始地址")
            error_list.append(ip_)
    else:
        print(ip_, "不支持的IP格式")
        error_list.append(ip_)
    return netlist


def resolve_file(file_in):
    file_out = file_in + "_result.txt"
    file_error = file_in + "_error.txt"
    with open(file_in, encoding="utf8") as file:
        list4merge = []
        result = []
        count = 0
        for ip in file:
            list4merge.extend(reslove(ip))
        merged_net = ipaddress.collapse_addresses(list4merge)
        for x in merged_net:
            if x.prefixlen < 24:
                for y in x.subnets(new_prefix=24):
                    result.append(str(y))
            else:
                result.append(str(x))
            count += x.num_addresses
        print("共计IP数:", count)

    with open(file_out, "w+", encoding="utf8") as file:
        file.writelines([x + "\n" for x in result])

    if len(error_list) > 0:
        with open(file_error, "w+", encoding="utf8") as file:
            file.writelines([x + "\n" for x in error_list])


if __name__ == "__main__":
    file_in = r"D:\IP数据\全国ip\all3\beijing.txt"
    resolve_file(file_in)
