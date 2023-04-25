import json

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set(style="white", palette="muted", color_codes=True, font="simhei", font_scale=1.0)
diy = {
    # 'font.sans-serif':'宋体', # 字体
    # 'axes.unicode_minus': False,  # 正常显示负号
    "axes.titlecolor": "#3B3B39",  # 标题
    "lines.markersize": 3.0,  # marker 大小
    # 'axes.titlesize': 24.0, # 无效
    # 'axes.labelsize': 36, # 同时修改了标题，弃用
    "axes.linewidth": 0.25,  # 坐标轴线宽
    "xtick.major.pad": -5.0,  # 坐标轴刻度与轴的距离
    "ytick.major.pad": -5.0,
    # 'xtick.major.size': 0.0, # 实际测试与pad一个含义
    # 'ytick.major.size': 0.0,
    "xtick.color": "#2F4F4F",  # 坐标轴刻度颜色
    "ytick.color": "#2F4F4F",
    "xtick.labelsize": 8,  # 坐标轴刻度文本
    "ytick.labelsize": 8,
    # 'xtick.bottom': True, # 是否显示刻度线
    # 'xtick.top': False,
    # 'ytick.left': True,
    # 'ytick.right': False
}
plt.rcParams.update(diy)
# for tmp in p.axes:
#     for ax in tmp:
#         ax.title.set_color('#0D246F')
#         ax_x = ax.spines['bottom']  # type: Spine
#         ax_y = ax.spines['left']  # type: Spine
#         ax_x.set_color('#0D246F')
#         ax_x.set_linewidth(0.5)
#         ax.tick_params(axis='both', pad=-5.02)
# f, ax = plt.subplots()


with open(r"C:\Users\sharp\Downloads\SSRSpeed-2.6.4\results\2020-04-13-11-48-24.json") as f:
    j = json.load(f)

data = pd.DataFrame()
for host in j:
    df = pd.DataFrame(host["rawSocketSpeed"], columns=["速度"])
    df["速度"] = df["速度"].map(lambda x: x / 1024)
    df["名称"] = host["remarks"]
    df["时间"] = range(len(df))
    data = pd.concat([data, df], ignore_index=True)

x, y = "时间", "速度"
# df1 = pd.DataFrame([(1, 30), (2, 50), (3, 10), (4, 500)], columns=[x, y])
# df1.insert(0, '名称', '深港3')
# df2 = pd.DataFrame([(1, 100), (2, 300), (3, 150), (4, 200), (5, 300)], columns=[x, y])
# df2.insert(0, '名称', '沪港4')
# data = pd.concat([df1, df2], ignore_index=True)

# p = sns.lineplot(x=x, y=y, data=data,palette="muted",color='m', lw=0.5, marker="o",hue='名称')
p = sns.FacetGrid(data, col="名称", col_wrap=5)
p.map(sns.lineplot, x, y, lw=0.75, marker="o")

# p.set(title="xxxx") #单图时使用
p.set_titles("{col_name}", size=12, fontfamily="lisu")
# p.set_xlabels(fontsize=6,fontfamily='simhei',color='green')
p.set_xlabels(fontsize=6)
p.set_ylabels(fontsize=6)
p.savefig("aaa.png", dpi=200)
