import sys
from functools import wraps

import numpy as np
import pandas as pd
import psutil
import os


def log_mem(func):
    @wraps(func)
    def wrap(*args):
        mem1 = psutil.Process().memory_info().rss
        print(f"{os.getpid()=} {func.__name__} init memory: ", mem1 / 1024**2, "MB")
        rst = func(*args)
        mem2 = psutil.Process().memory_info().rss
        print(f"{os.getpid()=} {func.__name__} use memory: ", (mem2 - mem1) / 1024**2, "MB")
        return rst

    return wrap


@log_mem
def test_big(arg):
    print(len(arg), arg[5678])


@log_mem
def test_df(arg):
    print(f"{type(arg)=}")
    print(arg.someattr.iloc[0:3])


def make_data():
    df = pd.DataFrame(np.random.randint(2000, 5000, 500_0000), columns=["age"])
    print("store dataframe use memory: ", df.memory_usage(deep=True).sum() / 1024**2, "MB")

    big = dict(zip(range(500_0000), np.random.randint(2000, 5000, 500_0000)))
    print(f"store big dict use memory: ", sys.getsizeof(big) / 1024**2, "MB")
    return df, big
