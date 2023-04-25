import lmdb
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
shm = "/dev/shm"


def map_func(row, txn):
    if pd.isna(row):
        return 0
    s = [float(txn.get(x.encode(), 0)) for x in row.split(delimiter)]
    return sum(s)


def func_part(df: pd.DataFrame):
    env = lmdb.open(f"{shm}/lmdb_data", readonly=True, create=False)
    with env.begin() as txn:
        return df[r].map(lambda x: map_func(x, txn))


if __name__ == "__main__":
    client = Client(LocalCluster(n_workers=30, threads_per_worker=1))

    df = dd.read_parquet(f"{base_dir}/testall", calculate_divisions=True)
    df2 = dd.read_parquet(f"{base_dir}/testid2", calculate_divisions=True)

    logger.info("build cache")
    df3 = df[[pk, src]].dropna(how="any").drop_duplicates(subset=[pk]).compute()
    cache = {str(key).encode(): str(value).encode() for key, value in df3.itertuples(index=False)}
    del df3
    logger.info(f"cache size: {len(cache)}")

    logger.info("put cache to memory")
    env = lmdb.open(f"{shm}/lmdb_data", map_size=5 * 1024**3)
    txn = env.begin(write=True)
    for key, value in cache.items():
        txn.put(key, value)
    txn.commit()
    del cache

    logger.info("compute df")
    rst = df2.map_partitions(func_part, meta=(None, "float32"))
    rst = rst.compute()
    logger.info((rst > 0).sum())

    logger.info("finish and clean")
    with env.begin(write=True) as txn:
        txn.drop(env.open_db())
    client.close(10)
