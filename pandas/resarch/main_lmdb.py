import platform
import shutil
import subprocess
from codecs import encode
from pathlib import Path
from typing import Literal, Optional

import bottleneck as bn
import dask
import lmdb
import numpy as np
import pandas as pd
import pydantic
import ujson as json
from dask import dataframe as dd

from log import logger
from octafl import BaseComponent
from octafl.config import settings

if platform.system() == "Linux":
    cache_dir = Path("/dev/shm")
else:
    cache_dir = Path(settings.file_storage_dir)


class Params(pydantic.BaseModel):
    from_field: str  # 匹配字段
    relation_field: str  # 关系字段
    delimiter: Optional[str] = "&&&"  # 关系分隔符
    value_field: list[str]  # 值字段
    dest: list[str]  # 保存值的字段
    func: Literal["avg", "sum", "max", "min"]


class Join(BaseComponent[Params]):
    """计算关联匹配指标"""

    def run(self):
        """将要关联的数据写入到共享内存数据库lmdb，然后根据rk从kv取值。
        如果cache只需构建一次，用这个方法很好。
        lmdb的get比dict.get还要快，并且
        dask_obj.map(some_dict)会把dict复制到各个进程（大量数据字典内存占用高），lmdb不会.
        当join的方式因为数据量太大导致性能问题时，可以使用本篇代码。
        """
        df = self.get_input_data(name="default")
        pk = self.params.from_field
        src_fields = self.params.value_field
        dst_fields = self.params.dest
        rk = self.params.relation_field
        delimiter = self.params.delimiter
        size = len(dst_fields)
        cache_path = cache_dir / self.job.id
        cache_path.mkdir(parents=True, exist_ok=True)

        logger.info("find position columns start")

        def find_unique(df: dd.DataFrame):
            """为减少写入的数据量，分割pk列字符串，查找位置使其唯一"""
            # logger对象不跨进程
            from log import logger

            for n in range(0, 3):
                s: dd.Series = df[pk].str[-(16 + n * 8) :]
                count, total = dask.compute(s.nunique(), df.shape[0])
                if count == total:
                    logger.info(f"position slice: {-(16 + n * 8)}")
                    return -(16 + n * 8)

        position = find_unique(df)

        # 这个情况使用orjson会内存泄露
        def make_kv(df: pd.DataFrame):
            bk = df[pk].str[position:].map(encode)
            # 将多个字段压缩到一个字段形成一个新列，之后json.dumps
            bv = pd.Series(df[src_fields].round(8).to_numpy().tolist(), index=df.index).map(
                lambda x: json.dumps(x).encode()
            )
            return pd.DataFrame({"bk": bk, "bv": bv}, index=df.index)

        def map_func(field, txn):
            if pd.isna(field):
                return np.array([np.nan] * size)
            rel = [x[position:].encode() for x in str(field).split(delimiter) if len(x) == 32]
            s = []
            for id1 in rel:
                if v := txn.get(id1):
                    s.append(json.loads(v))
            if s:
                # 原生python 33.5 µs
                # rst = []
                # for i in range(size):
                #     if items := list(filter(pd.notna, (item[i] for item in s))):
                #         rst.append(sum(items) / len(items))
                #     else:
                #         rst.append(np.nan)
                # return np.array(rst, dtype="f4")
                return bn.nanmean(s, axis=0)  # 3.67 µs
                # return np.nanmean(s, axis=0) # 慢,67.4 µs
            return np.array([np.nan] * size)

        def func_part(df: pd.DataFrame):
            env = lmdb.open(str(cache_path), readonly=True)
            with env.begin(write=False) as txn:
                tmp = df[rk].map(lambda x: map_func(x, txn))
                return pd.DataFrame(np.stack(tmp.array), columns=dst_fields, dtype="f4", index=df.index)

        logger.info("make cache start")
        cache: pd.DataFrame = df.map_partitions(make_kv, meta={"bk": object, "bv": object}).compute()

        logger.info("write lmdb data start")
        # 这篇代码中的耗时操作，cache_path指定为/dev/shm会提高写入性能
        env = lmdb.open(str(cache_path), map_size=20 * 1024**3)  # 5kw要大概要6G磁盘，经position裁剪后3-4G
        with env.begin(write=True) as txn:
            cursor = txn.cursor()
            cursor.putmulti(zip(cache["bk"], cache["bv"]))
        logger.success("write lmdb data finished")
        del cache

        if platform.system() == "Linux":
            p = subprocess.run(["du", "-hd0", str(cache_path)], capture_output=True, text=True)
            logger.debug(p.stdout.split()[0])

        # 此处两边的索引应当相同且都是单调递增
        df[dst_fields] = df.map_partitions(func_part, meta=pd.DataFrame(columns=dst_fields, dtype="f4"))
        # logger.debug(df.loc[~df[dst_fields[0]].isna(), dst_fields].tail().compute())
        self.save_data(name="default", data=df)
        shutil.rmtree(cache_path, ignore_errors=True)
