from dask import dataframe as dd

from dask_pandas.dask_util import reindex
from dask_pandas.dataset_util import headers, dt

pk = "ID1"
src = "S21"
r = "ID2"
dest = "xxx"
delimiter = "&&&"
base_dir = "/home/credit_index/data/app"

df = dd.read_csv(f"{base_dir}/50w2022.csv", blocksize="150MiB", names=headers, dtype=dt)
df = reindex(df)

df.drop(r, axis=1).to_parquet(f"{base_dir}/testall", compression=None, write_metadata_file=True)
df[[pk, r]].to_parquet(f"{base_dir}/testid2", compression=None, write_metadata_file=True)
