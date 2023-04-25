import vaex
from vaex import dataframe as vd
from vaex.arrow.dataset import open_parquet  # noqa

# open按照文件名后缀来区分不同格式
df: vd.DataFrameLocal = vaex.open(".../testkw.csv")


def read_pq():
    ds = open_parquet(".../data.pq")
    df: vd.DataFrameLocal = vaex.from_dataset(ds)
    return df


def test_apply(*arg):
    return len(arg[0])


columns = df.get_column_names()
df["xxx"] = df.apply(test_apply, arguments=[df[k] for k in columns])
df2 = df.groupby("id", agg=vaex.agg.mean("M11"))

x: vaex.Expression = df["xxx"]
print(x.to_pandas_series())
