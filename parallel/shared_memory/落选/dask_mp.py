import os
import sys
from multiprocessing import Manager

import pandas as pd
import psutil
from dask import dataframe as dd
from distributed import Client, LocalCluster
from loguru import logger

pk = "ID1"
src = "F13"
r = "ID2"
dest = "xxx"
delimiter = "&&&"
agg_func = "sum"
base_dir = "/home/credit_index/data/app"


def mp_func(row, cache):
    if pd.isna(row):
        return 0
    rel = row.split(delimiter)
    if not rel:
        return 0
    s = [float(cache.get(x, 0)) for x in rel]
    return sum(s)


def func_part(df: pd.DataFrame, cache):
    mem1 = psutil.Process().memory_info().rss
    cache = cache.dt
    mem2 = psutil.Process().memory_info().rss
    logger.info(f"{os.getpid()=} use memory: {(mem2 - mem1) / 1024 ** 2} MB")
    return df[r].map(lambda x: mp_func(x, cache))


if __name__ == "__main__":
    client = Client(LocalCluster(n_workers=30, threads_per_worker=1))

    df = dd.read_parquet(f"{base_dir}/testall", calculate_divisions=True)
    df2 = dd.read_parquet(f"{base_dir}/testid2", calculate_divisions=True)

    logger.info("build cache")
    cache = df[[pk, src]].dropna(how="any").drop_duplicates(subset=[pk]).compute()
    cache = {key: value for key, value in cache.itertuples(index=False)}
    logger.info(f"cache size: {len(cache)}; memory usage: {sys.getsizeof(cache) // 1024 ** 2}")

    logger.info("put cache to memory")
    with Manager() as shm:
        ns = shm.Namespace()
        ns.dt = cache

        logger.info("compute df")
        rst = df2.map_partitions(func_part, ns, meta=(None, "float32"))
        rst = rst.compute()
        logger.info((rst > 0).sum())

    logger.info("finish and clean")
    client.close(10)
