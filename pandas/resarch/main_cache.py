from typing import Literal, Optional

import numpy as np
import pandas as pd
import pydantic
from dask import dataframe as dd

from log import logger
from octafl import BaseComponent


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
        df = self.get_input_data(name="default")
        pk = self.params.from_field
        src_fields = self.params.value_field
        dst_fields = self.params.dest
        rk = self.params.relation_field
        delimiter = self.params.delimiter

        logger.info("开始构建缓存")
        kv = df[[pk] + src_fields].compute()
        cache = {item[0]: item[1:] for item in kv.itertuples(index=False)}
        del kv

        def map_func(field, i):
            if pd.isna(field):
                return np.nan
            rel = [x for x in str(field).split(delimiter) if len(x) == 32]
            s = []
            for x in rel:
                if v := cache.get(x):
                    s.append(v[i])
            if s := list(filter(pd.notna, s)):
                return sum(s) / len(s)
            return np.nan

        logger.info("开始整理关联列")
        relation_field = df[rk].compute()
        logger.info("开始计算")
        for i, dst in enumerate(dst_fields):
            logger.info(f"{i=}, {dst=}")
            s = relation_field.map(lambda x, i=i: map_func(x, i)).astype("float32")
            if s.empty:
                df[dst] = np.nan
            else:
                assert s.index.is_monotonic_increasing
                assert s.index.shape[0] - 1 == df.divisions[-1]
                s = dd.from_pandas(s, npartitions=df.npartitions)
                s = s.repartition(divisions=df.divisions)
                df[dst] = s
            logger.info(f"{dst=} 计算完成")

        self.save_data(name="default", data=df)
