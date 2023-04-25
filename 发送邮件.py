# python3
# coding=utf8

import base64
import mimetypes
import smtplib
import traceback
from email.headerregistry import Address
from email.message import EmailMessage
from email.utils import localtime

smtp_server = "smtp.qq.com"
smtp_port = 465
account = "xianzaisy@qq.com"
password = "dfsajhsyrnzdcagi"
account_name = "octa"


def convertToHtml(record):
    """QQ邮箱过滤了<style>标签中的css，所以css使用行内样式"""
    html_start = (
        '<!DOCTYPE html>\n<html>\n<head><meta http-equiv="Content-Type" content="text/html;'
        'charset=utf8">\n</head><body>'
    )
    html_end = "</body></html>"
    body_css_part1 = '<div style="font-size: 12pt;font-family: 华文行楷;line-height: 1.5;">'
    body_div_part2 = "</div>"

    top_text = f"<div><br><br></div><div>TTTTTTTTTTTtt</div><div><br></div>"
    bottom_text = "<div><br></div><div><span>BBBBBBBBBBBBBBB</span></div><div><br></div>"

    table_css = (
        "border-collapse: collapse; border: 1px solid; margin-left:5%;font-size: "
        "11pt;font-family: 微软雅黑;"
    )
    cell_css = "width:80px;height: 40px;border: 1px solid;text-align: center; padding: 3px;"

    table = f'<table style="{table_css}">\n'
    table += "<thead><tr>\n"
    for key in record:
        table += f'<th style="{cell_css}">{key}</th>\n'
    table += "</tr></thead>\n<tbody><tr>\n"
    for key in record:
        table += f'<td style="{cell_css}">{record[key]}</td>\n'
    table += "</tr></tbody>\n</table>"
    # df = pandas.DataFrame(record, index = [0])
    # df.to_html(index = False, border = 1, classes = 'gztable')
    return "\n".join(
        [
            html_start,
            body_css_part1,
            top_text,
            table,
            bottom_text,
            body_div_part2,
            html_end,
        ]
    )


def get_type(path):
    ctype, encoding = mimetypes.guess_type(path)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    return ctype.split("/", 1)


def dd_b64(headstr):
    """对邮件header及附件的文件名进行两次base64编码，防止outlook中乱码。email库源码中先对邮件进行一次base64解码然后组装邮件，所以两次编码"""
    headstr = "=?utf-8?b?" + base64.b64encode(headstr.encode("UTF-8")).decode() + "?="
    headstr = "=?utf-8?b?" + base64.b64encode(headstr.encode("UTF-8")).decode() + "?="
    return headstr


def make_msg(to_name, to_addrs, verify_code):
    msg = EmailMessage()
    msg["From"] = Address(dd_b64(account_name), addr_spec=account)  # 省略addr_spec会出现 由 xxx 代发
    msg["To"] = Address(dd_b64(to_name), addr_spec=to_addrs)
    msg["Subject"] = "Signup Verify Code"
    msg["Date"] = localtime()

    # html_table = html_table.replace('</body>', f'<img src="cid:{msg_cid[1:-1]}" width="300"/></body>')
    # msg.add_alternative(html_table, subtype='html')
    msg.set_content(verify_code)

    return msg


def send_mail(to_addrs, verify_code):
    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(account, password)
    except:
        print("登陆邮件服务器失败")
        return

    msg = make_msg(to_addrs, to_addrs, verify_code)
    try:
        server.send_message(msg)
    except:
        traceback.print_exc()
    finally:
        server.quit()
