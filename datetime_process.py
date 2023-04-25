import time
from datetime import datetime, timedelta, timezone

# 当构造或返回时间对象时，需指定时区。其他情况不需要
bj = timezone(timedelta(hours=+8))
t = 123
d = datetime(2013, 10, 10, 23, 40, tzinfo=bj)
s = "2013-10-10 23:40:00"

# 当前时间戳
time.time()
datetime.now().timestamp()

# 当前时间对象
time.localtime(time.time() + 8 * 60 * 60)  # 根据实际情况判定
datetime.now(tz=bj)

# 当前时间字符串
time.asctime()  # 'Sun Sep 26 09:07:51 2021'
time.strftime("%Y-%m-%d %H:%M:%S")
datetime.now(tz=bj).strftime("%Y-%m-%d %H:%M:%S")

# 时间戳 -> 对象 -> 字符串
time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
datetime.fromtimestamp(t, tz=bj).strftime("%Y-%m-%d %H:%M:%S")

# 字符串  -> 对象 -> 时间戳
pass

# 时间戳 -> 对象
time.localtime(time.time() + 8 * 60 * 60)  # 根据实际情况判定
datetime.fromtimestamp(t, tz=bj)

# 对象-> 时间戳
struct_time = time.strptime(s, "%Y-%m-%d %H:%M:%S")
time.mktime(struct_time)
d.timestamp()

# 字符串 -> 对象
time.strptime(s, "%Y-%m-%d %H:%M:%S")
datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

# 对象 -> 字符串
time.strftime("%Y-%m-%d %H:%M:%S")
d.strftime("%Y-%m-%d %H:%M:%S")
