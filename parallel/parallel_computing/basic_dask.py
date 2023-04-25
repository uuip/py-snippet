import os

import pandas as pd
from dask import dataframe as dd
from distributed import Client, LocalCluster

from dask_pandas.dask_util import reindex

cpu = os.cpu_count()
if cpu >= 16:
    cpu -= 4
cpu = min(25, cpu)


if __name__ == "__main__":
    client = Client(
        LocalCluster(
            n_workers=cpu,
            threads_per_worker=1,
            memory_limit=None,
            scheduler_port=7777,
            dashboard_address=":8787",
        )
    )
    df: dd.DataFrame = dd.read_parquet("d:/testdata_5w.pq")
    # df: dd.DataFrame = dd.read_csv("/home/credit_index/data/app/testkw.csv")

    print(f"{df.npartitions=}")
    df = reindex(df)
    # df["xxx"] = df.apply(len, axis=1, meta=(None, int))
    df["xxx"] = pd.Series(range(50000000))
    print(df.loc[5000:5050, ["xxx"]].compute())
