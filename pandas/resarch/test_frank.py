import math
from typing import List

import dask
import pandas as pd
import pydantic
import yaml
from dask import dataframe as dd
from rich import get_console, box
from rich.align import Align
from rich.table import Table

from common.dask_util import reindex
from common.dataset_util import headers, dt, data_cleaning
from log import logger

base_dir = "/mnt/c/Users/sharp/Desktop/project/credit_index/backend"
with open(f"{base_dir}/python/scheduler/dsl/standard-host.yml") as f:
    profile = yaml.safe_load(f)


class SignleParam(pydantic.BaseModel):
    range: List[int] = pydantic.Field(default_factory=lambda: list(range(100, 1001, 100)))
    source: str
    dest: str
    reversed = False


class Params(pydantic.BaseModel):
    rank: List[SignleParam]
    group_by: str


def show(df: pd.DataFrame):
    table = Table(box=box.ASCII)
    table.add_column("index")
    for x in df.columns:
        table.add_column(x, min_width=len(x), max_width=16, justify="center")
    for x in df.itertuples():
        table.add_row(*map(lambda cell: Align(str(cell), align="right"), x))
    get_console().print(table)


def series_show(s: pd.Series):
    table = Table(box=box.ASCII)
    table.add_column("index")
    name = s.name or "value"
    table.add_column(name, min_width=len(name), max_width=16, justify="center")
    for x in s.items():
        table.add_row(*map(lambda cell: Align(str(cell), align="right"), x))
    get_console().print(table)


pd.DataFrame.show = show
pd.Series.show = series_show


def run(params):
    logger.debug("convert to df")
    df = dd.read_csv(f"{base_dir}/mytest/50w_2022.csv", dtype=dt, names=headers)
    df = reindex(df)
    df = data_cleaning(df)
    logger.debug("df ready")

    logger.debug(f"计算分数")

    asc = [params.group_by] + [i.source for i in params.rank if not i.reversed]
    desc = [params.group_by] + [i.source for i in params.rank if i.reversed]
    asc_df, desc_df = dask.compute(df[asc], df[desc])
    # 上文 dask df已经重设了index 为递增唯一索引，下文的join依赖索引
    asc_ranked_df: pd.DataFrame = asc_df.groupby(params.group_by).rank(method="min")
    desc_rank_df = desc_df.groupby(params.group_by).rank(method="min", ascending=False)
    ranked_df = asc_ranked_df.join(desc_rank_df)

    def make_params():
        for i in params.rank:
            r = ranked_df[[i.source]].join(df[params.group_by].compute())
            count_by_year = dict(r.groupby(params.group_by).count()[i.source])
            dr = dd.from_pandas(r, npartitions=df.npartitions)
            dr = dr.repartition(divisions=df.divisions, force=True)
            yield i, count_by_year, dr

    def func(row, rank, count_by_year):
        value, year = row
        # if pd.isna(value):
        #     return rank[0]
        total = count_by_year[year]
        index = math.ceil(value / total * len(rank)) - 1
        return rank[index]

    df = df.assign(
            **{
                    i.dest: dr.apply(func, args=(i.range, count_by_year), axis=1, meta=(None, "int32"))
                    for i, count_by_year, dr in make_params()
                    }
            ).compute()
    # for i in params.rank:
    #     print(rst.groupby(i.dest).count())
    print(df["F11_score"].value_counts().sort_index())
    # df.loc[:99, ["ID1", "F11", "F11_score"]].show()
    # print(rst.to_string())


if __name__ == "__main__":
    params = Params(**profile["components"][1]["params"])
    run(params)
