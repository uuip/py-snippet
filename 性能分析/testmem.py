import os
import time

p = os.getenv("PATH")
os.environ["PATH"] = p + ";" + r"C:\Users\sharp\Downloads\Graphviz\bin"
import objgraph

from pympler import muppy, summary

sum1 = summary.summarize(muppy.get_objects())


summary.print_(summary.get_diff(sum1, summary.summarize(muppy.get_objects())), limit=3)
for x in [ao for ao in delta if isinstance(ao, bytearray)]:
    # print(x.decode().strip().replace('\r\n', ';').replace('\n', ';'), end='')
    if x.decode().strip().replace("\r\n", ";").startswith("$0"):
        print(bytearray(b"$0\r\n\r\n"))
input("pause")


# for x in [ao for ao in aos if isinstance(ao, CaseInsensitiveDict)]:
#     cb = refbrowser.ConsoleBrowser(x, maxdepth=5)
#     cb.print_tree()
#     break

start = {}
flag = set()

if "chain_info_callback" not in flag:
    objgraph.growth(limit=10, peak_stats=start)
else:
    objgraph.show_most_common_types(limit=30)
    newobjs = objgraph.get_new_ids()
    for cname in [
        "Encoder",
        "Connection",
        "Redis",
        "HiredisParser",
        "socket",
        "WeakKeyDictionary",
    ]:
        for x in objgraph.at_addrs(newobjs.get(cname, [])):
            objgraph.show_chain(
                objgraph.find_backref_chain(x, objgraph.is_proper_module),
                filename=f"images/{cname}_{int(time.time())}.png",
            )
            break
