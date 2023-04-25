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
        size = len(dst_fields)

        logger.warning("与使用循环版本的性能相当")
        logger.info("开始构建缓存")
        kv = df[[pk] + src_fields].compute()
        cache = {item[0]: item[1:] for item in kv.itertuples(index=False)}
        del kv

        def map_func(field):
            if pd.isna(field):
                return [np.nan] * size
            rel = [x for x in str(field).split(delimiter) if len(x) == 32]
            s = []
            for id1 in rel:
                if v := cache.get(id1):
                    s.append(v)
            if s:
                rst = []
                for i in range(size):
                    if items := list(filter(pd.notna, (item[i] for item in s))):
                        rst.append(sum(items) / len(items))
                    else:
                        rst.append(np.nan)
                return rst
            return [np.nan] * size

        logger.info("开始整理关联列")
        relation_field = df[rk].compute()
        logger.info("开始计算")
        s = relation_field.map(map_func)
        s = pd.DataFrame(
            s.to_list(),
            columns=dst_fields,
            dtype="f4",
            index=s.index,
        )
        logger.info("计算完成，开始存储")
        if s.empty:
            df[dst_fields] = np.nan
        else:
            assert s.index.is_monotonic_increasing
            assert s.index.shape[0] - 1 == df.divisions[-1]
            s = dd.from_pandas(s, npartitions=df.npartitions)
            s = s.repartition(divisions=df.divisions)
            df[dst_fields] = s

        self.save_data(name="default", data=df)
