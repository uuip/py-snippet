import logging
import platform
from itertools import accumulate

import dask
import numpy as np  # noqa
import pandas as pd  # noqa
from dask import dataframe as dd, array as da
from distributed import Client, LocalCluster
from loguru import logger
from pyarrow import csv, Table

from dataset_util import headers, dt


def set_scheduler():
    """设置dask多进程后端。
    dask调度器要在__main__中初始化，django management满足。

    dask默认多线程： concurrent.futures.ThreadPoolExecutor
    1. LocalCluster
    # 主进程（__main__中初始化）
    >>> client = Client("127.0.0.1:7777") #使用默认参数配置资源
    >>> client = Client(LocalCluster(n_workers=20, threads_per_worker=1))
    # 其他进程连接 scheduler
    >>> client = Client("127.0.0.1:7777")

    2. loky: ProcessPoolExecutor加强版，可配置executer空闲xx时间后退出
    >>> from loky import get_reusable_executor

    >>> dask.config.set(scheduler=get_reusable_executor())

    3. concurrent.futures.ProcessPoolExecutor
    >>> dask.config.set(scheduler="processes")
    """
    # 在父进程重启，在worker进程重启会出差
    client.restart()


def pandas_io():
    df: pd.DataFrame = pd.DataFrame.from_dict(...)
    df: pd.DataFrame = pd.read_csv(...)
    df: pd.DataFrame = pd.read_parquet(...)
    df.to_csv(..., index=False)  # 不建议使用
    # pandas要在输出时指定row_group_size划分好分区；pandas输出到一个文件，dask则是每个分区一个文件
    df.to_parquet(..., compression=None, row_group_size=50_0000)


def dask_io():
    df: dd.DataFrame = dd.read_csv(..., blocksize="150MiB", names=headers, dtype=dt)
    df: dd.DataFrame = dd.from_pandas(..., npartitions=120)
    df: dd.DataFrame = dd.from_pandas(..., chunksize=50_0000)
    # write_metadata 后 可以在读取时calculate_divisions
    # split_row_groups 若读取的是一个文件且这个文件包含分区信息，合并还是分区。
    df: dd.DataFrame = dd.read_parquet(..., calculate_divisions=True, split_row_groups=True)
    df.to_csv(..., single_file=True, index=False)  # 不建议使用
    # pandas的默认索引名是level_0，dask是index
    # 正确处理索引、分区才能使dask准确读pandas导出的pq文件，不如都转换为dask_df后再导出
    df.to_parquet(..., compression=None, write_metadata_file=True)


def write_csv():
    """pyarrow csv模块快速写csv"""
    csv.write_csv(Table.from_pandas(...), output_file=...)


def reindex(df: dd.DataFrame, divisions=None) -> dd.DataFrame:
    """设置dask dataframe的索引为单调递增。
    dask df在读取csv后的默认索引是每个分区0-x，在分区内单调。
    """

    chunks = df.map_partitions(len, meta=(None, int)).compute().to_list()
    # 不能连续reindex，除非使用其他name
    name = ({"idx", "idx2"} - {df.index.name}).pop()
    df[name] = da.arange(sum(chunks), chunks=chunks)
    #  set_index().persist()会使divisions即时更新，不加persist则在用到时计算
    #  Jupyter 里用 persist 会好点；程序里没必要。
    df = df.set_index(name, sorted=True, drop=True, divisions=divisions)
    return df


def fix_div(df: dd.DataFrame) -> dd.DataFrame:

    # 重设索引后，div应当要发生变化
    if df.divisions[0] is None:
        # 需要重新计算各个分区，此时div与上文的不同了
        chunks = df.map_partitions(len, meta=(None, int)).compute().to_list()
        div = list(accumulate(chunks, initial=0))
        total = sum(chunks)
        if total > 0:
            div[-1] = total - 1
        df.divisions = tuple(div)
    return df


def dask_info():
    df = dd.from_pandas(..., chunksize=...)
    df = df.repartition(partition_size="100MiB")  # 内存大小

    df.info()
    df.describe()
    len(df)  # 不论在pandas还是dask都是最快方法
    df.npartitions
    df.columns.to_list()

    rows, mem = dask.compute(df.shape[0], df.memory_usage().sum() / 1024**2)
    df.shape[0].compute()
    # 与dask.compute等价
    client.compute(df, sync=True)


def test(row):
    return 0


def bulk():
    df = dd.from_pandas(..., chunksize=1000)
    # dask apply 仍是调用map_partitions
    df.apply(test, axis=1, meta=("k", int))
    df.map_partitions(test, meta=(None, int))

    df["id"].map(test, meta=(None, int))


def add_column():
    # 从其他df引用列,df,df2具有相同单调递增索引，且df.divisions是明确的。
    df = ...
    df2 = ...
    df = df.assign(**{"F11_tmp": df2["F11"]})
    df["abc"] = df2["aaa"]


if __name__ == "__main__":
    client = Client(
        LocalCluster(
            scheduler_port=7777,
            n_workers=4,
            threads_per_worker=1,
            memory_limit="4GiB",  # 128G内存，32核：按110G，28算
            silence_logs=logging.ERROR,
        )
    )
    logger.info(f"{client.dashboard_link=}")
    logger.info(f"{client.scheduler.address=}")
