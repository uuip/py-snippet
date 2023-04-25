import os

import pandas as pd
import ray
from dask import dataframe as dd
from ray import data as rd
from ray.data import aggregate as agg
from ray.util.dask import enable_dask_on_ray, disable_dask_on_ray

cpu = os.cpu_count()
if cpu >= 16:
    cpu -= 4
cpu = min(25, cpu)


def usage():
    ds = ray.data.from_dask(df)
    ds.write_parquet("file")

    # 返回共享内存id
    ds.get_internal_block_refs()
    ds.lazy()

    ds = ds.map_batches
    ds = ds.add_column
    ds = ds.drop_columns
    ds.groupby("id").mean("M11")
    ds.groupby("id").aggregate(agg.Count())

    ds.num_blocks()
    ds = ds.repartition(200)


def map_fn(batch: pd.DataFrame):
    rst = batch.apply(len, axis=1)
    return list(rst)


if __name__ == "__main__":
    ray.init(num_cpus=cpu, _temp_dir="/home/credit_index/data/app/temp")
    print(ray.nodes(), ray.cluster_resources())
    enable_dask_on_ray()

    # 每个csv一个分区，完整加载到内存;
    # ds: rd.Dataset = ray.data.read_csv
    ds: rd.Dataset = ray.data.read_parquet("/home/credit_index/data/app/F2指标打分_default/data.pq")

    s = ds.add_column("xxx", map_fn)
    df: dd.DataFrame = ds.to_dask()
    df.loc[5000:5050, ["xxx"]].compute()
    print(df.npartitions)

    disable_dask_on_ray()()
    ray.shutdown()
