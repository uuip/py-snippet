import pandas as pd
import ray
from dask import dataframe as dd
from loguru import logger
from ray.util.dask import enable_dask_on_ray, disable_dask_on_ray

# https://discuss.ray.io/t/core-how-to-share-memory-with-non-numpy-object/1295
# https://stackoverflow.com/questions/73823186
# Ray supports zero-copy-read for numpy (for float or integer types) array.
# Other data structures will be copied when they are ray.get by workers.
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
    return df[r].map(lambda x: mp_func(x, cache[src]))


if __name__ == "__main__":
    ray.init(num_cpus=30)  # _temp_dir="/tmp", _plasma_directory="/tmp"
    enable_dask_on_ray()

    df = dd.read_parquet(f"{base_dir}/testall", calculate_divisions=True)
    df2 = dd.read_parquet(f"{base_dir}/testid2", calculate_divisions=True)

    logger.info("build cache")
    cache: dd.Series = (
        df.loc[df[src].notnull(), [pk, src]]
        .drop_duplicates(subset=[pk])
        .set_index(pk, drop=True)
        .compute()
    )

    logger.info("put cache to memory")
    cache = ray.put(cache)

    logger.info("compute df")
    df[dest] = df2.map_partitions(func_part, cache, meta=(None, "float32"))
    s = df.compute()[[pk, dest]]
    logger.info(len(s[s[dest] > 0]))

    logger.info("finish and clean")
    disable_dask_on_ray()
