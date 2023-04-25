import numpy as np
import pandas as pd

df = pd.DataFrame()

df.groupby("group_by")["field"].mean()
df.groupby("id")["M11"].transform("mean", meta=(None, float))
df.groupby("id").count()["M11"]

df.drop_duplicates(subset=["key"]).rename(columns={"field": "column_toadd"})
df[["id", "D11"]].merge(df[["id", "M11"]], how="left", on="id")
df[["id", "M11"]].join(df["D11"])

df[df["t1"].astype(int).isin([2020, 2021, 2022])]
df.replace(np.nan, None)

# 比iteritems,values效率高
for row in df.itertuples(index=False):
    ...


# itertuples是value，items是迭代为Series
def which_column_maybe_null():
    # 只是示例，若只看na，df.isna().any()
    maybenull = []
    for col, s in df.items():
        if s.isna().any():
            maybenull.append(col)
        if s.nunique(dropna=True) <= 2:
            print(col, s.unique().tolist())


# 取消科学计数法
np.set_printoptions(suppress=True)

# # 设置pd的显示格式，但不包含数据内部格式
pd.set_option('display.float_format', '{:.0f}'.format)

# 使用decimal
df['r'] = (df['m'].apply(Decimal) * df['n'].apply(Decimal)).apply(lambda x: x.to_integral_value(rounding=ROUND_HALF_UP))



# 修改、添加列
df["s1"] = (
    df["s1"]
    .round(2)
    .astype(object)
    .apply(lambda n: int(n) if n.is_integer() else n, convert_dtype=False)
)
# 添加空列
df["owner"] = pd.Series(dtype=str)

df.rename(columns={"token_int": "token_id"}, inplace=True)
df["owner"].replace(np.nan, None, inplace=True)

# 附加行
row = pd.DataFrame([{"token_id": 111, "owner": "fff"}])
df = pd.concat([df, row], ignore_index=True)

# 附加行2
# df.loc[len(df.index)] = row

df[df.isna().any(axis=1)]
df[df.token_id == 2377]
df.query("token_id==2377")

# 单元格赋值
for i, x in df.iterrows():
    df.at[i, "owner"] = 123

for k, v in df.T.to_dict().items():
    print(k, v)

df.to_csv("a.csv", index=True, header=False, float_format="%.0f")
df.to_excel(r"C:\Users\sharp\Downloads\ship_farm.xlsx", index=False)


from rich import get_console, box
from rich.align import Align
from rich.table import Table
def show(df: pd.DataFrame):
    table = Table(box=box.ASCII)
    table.add_column("index")
    for x in df.columns:
        table.add_column(x, min_width=len(x), max_width=16, justify="center")
    for x in df.itertuples():
        table.add_row(*map(lambda cell: Align(str(cell), align="right"), x))
    get_console().print(table)


def series_show(s: pd.Series):
    table = Table(box=box.ASCII)
    table.add_column("index")
    name = s.name or "value"
    table.add_column(name, min_width=len(name), max_width=16, justify="center")
    for x in s.items():
        table.add_row(*map(lambda cell: Align(str(cell), align="right"), x))
    get_console().print(table)


pd.DataFrame.show = show
pd.Series.show = series_show
s=pd.Series()
