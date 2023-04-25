import dask
import pandas as pd
from dask import dataframe as dd
from distributed import Client, LocalCluster
from loguru import logger


pk = "ID1"
src = "S21"
r = "ID2"
dest = "xxx"
delimiter = "&&&"
base_dir = "/home/credit_index/data/app"


def map_func(row, cache):
    if pd.isna(row):
        return 0
    s = [float(cache.get(x, 0)) for x in row.split(delimiter)]
    return sum(s)


def func_part(df: pd.DataFrame, cache):
    return df[r].map(lambda x: map_func(x, cache))


if __name__ == "__main__":
    client = Client(LocalCluster(n_workers=30, threads_per_worker=1))

    df = dd.read_parquet(f"{base_dir}/testall", calculate_divisions=True)
    df2 = dd.read_parquet(f"{base_dir}/testid2", calculate_divisions=True)

    logger.info("build cache")
    cache = (
        df[[pk, src]]
        .dropna(how="any")
        .drop_duplicates(subset=[pk])
        .compute()
        .set_index(pk, drop=True)[src]
    )
    logger.info(f"cache size: {len(cache)}")

    logger.info("put cache to memory")
    cache = dask.delayed(cache)
    # cache = client.scatter(cache)

    logger.info("compute df")
    rst = df2.map_partitions(func_part, cache, meta=(None, "float32"))
    rst = rst.compute()
    logger.info((rst > 0).sum())

    logger.info("finish and clean")
    del cache
    client.close(10)
