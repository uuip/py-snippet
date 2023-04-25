import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union
from uuid import UUID

import pandas as pd
from dask import dataframe as dd

from common.dask_util import reindex
from common.dataset_util import has_csv_header, headers, dt, data_cleaning
from log import logger
from scheduler import setup_django

try:
    setup_django.setup_django()
except:
    ...

from apps.client.minio_adapter.client import Client
from apps.dataset.models import DatasetModel
from octafl import BaseComponent


@dataclass
class Params:
    path: List[str]


def get_datafile_uri_with_uid(uid: Union[str, UUID]):
    uid = str(uid)  # 确保转成字符串
    try:
        dataset = DatasetModel.objects.get(uid=uid)
    except DatasetModel.DoesNotExist:
        raise Exception(f"找不到数据集{uid}")
    fname = f"/tmp/{dataset.filename}"
    Client.get_client().fget_object(dataset.filename, fname)
    logger.warning(dataset.filename)
    return fname


def product_drop(file):
    df = pd.read_csv(file, names=["ID1", "date"])
    # 1900: 将异常数据的年份设置为1900，后续必然在drop范围内
    df["date"] = df["date"].fillna(1900)
    df["T1"] = df["date"].astype(str).str.split("-", expand=True)[0].astype("i4")
    df.loc[df["T1"] < 1900, "T1"] = 1900
    return df.drop("date", axis=1)


class Loader(BaseComponent[Params]):
    def run(self):
        temp_dir = Path(self.storage.dist).absolute() / self.job.id / self.task.name
        temp_dir.mkdir(parents=True, exist_ok=True)
        to_drop = []
        # 这两份数据 4千万
        for f in ["/data/qyxyzs_cancel.csv", "/data/qyxyzs_revoke.csv"]:
            if Path(f).exists():
                to_drop.append(product_drop(f))
        if not to_drop:
            generator_list = []
            has_head = set()
            for p in self.params.path:
                _p = Path(p)
                logger.debug(f"{p=}, 当前目录 {os.getcwd()}")
                if not _p.exists() or not _p.is_file():
                    p = get_datafile_uri_with_uid(str(p))
                generator_list.append(p)
                has_head.add(has_csv_header(p))
            if len(has_head) == 1:
                if has_head.pop() is True:
                    df = dd.read_csv(generator_list, blocksize="150M", dtype=dt)
                else:
                    df = dd.read_csv(generator_list, blocksize="150M", names=headers, dtype=dt)
            else:
                raise TypeError("输入文件具有不同的表头")
            logger.debug(f"{df.npartitions=}")
        else:
            df_drop = pd.concat(to_drop)
            del to_drop

            has_droped = []
            size = 0
            for p in self.params.path:
                _p = Path(p)
                logger.debug(f"{p=}, 当前目录 {os.getcwd()}")
                if not _p.exists() or not _p.is_file():
                    p = get_datafile_uri_with_uid(str(p))
                if has_csv_header(p):
                    df_p = dd.read_csv(p, blocksize="150M", dtype=dt)
                else:
                    df_p = dd.read_csv(p, blocksize="150M", names=headers, dtype=dt)
                if not df_drop.empty:
                    df_p = df_p.compute()
                    logger.info(f"{p} line before drop: {len(df_p)}")
                    year = df_p["T1"].max()
                    size += len(df_p)
                    # #method:1
                    s = df_drop.loc[df_drop["T1"] < int(year), "ID1"]
                    df_p: pd.DataFrame = df_p.loc[~df_p["ID1"].isin(s)]
                    # #method: 2 内存不足
                    # df_sub = df_drop.loc[df_drop["T1"] < int(year), ["ID1"]]
                    # df_p = pd.concat([df_p, df_sub,df_sub]).drop_duplicates(subset=["ID1"], keep=False)
                    # method: 3 内存不足
                    # df_sub = df_drop.loc[df_drop["T1"] < int(year), ["ID1"]]
                    # df_p = (
                    #     df_p.merge(df_sub, how="left", indicator=True)
                    #     .query('_merge == "left_only"')
                    #     .drop("_merge", axis=1)
                    # )
                    logger.info(f"{p} line after drop: {len(df_p)}")
                    filename = temp_dir / Path(p).name
                    # #method: 1
                    # df_p = dd.from_pandas(df_p, chunksize=50_0000)
                    # df_p.to_parquet(filename, compression=None, write_metadata_file=True)
                    # #method: 2
                    df_p.to_parquet(filename, compression=None, row_group_size=50_0000)  # 行

                    has_droped.append(filename)
                    del df_p
            del df_drop
            # #method: 1
            # df = dd.concat(
            #     [
            #         dd.read_parquet(f, split_row_groups=True, calculate_divisions=True)
            #         for f in has_droped
            #     ]
            # )
            # #method: 2
            df = dd.read_parquet(has_droped, split_row_groups=True)
            df = df.repartition(npartitions=size // 50_0000 + 1)
        df: dd.DataFrame = reindex(df)
        # 这一行不能与上行合并，因为reindex使df列变化，而meta引用df
        df = df.map_partitions(data_cleaning, meta=df)
        self.save_data(name="default", data=df)
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info("数据装载成功")
