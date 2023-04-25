import os
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Process, Pool

import toolz
from joblib import Parallel, delayed
from loky import get_reusable_executor

group = 1000
seq = ...


def make_bulk(func, seq):
    return [func(x) for x in seq]


def mp():
    ps = []
    for _ in range(os.cpu_count()):
        p = Process(target=make_bulk, args=(...,))
        p.start()
        ps.append(p)

        for x in ps:
            x.join()


def mp_pool():
    with Pool() as pool:
        for x in toolz.partition_all(group, seq):
            for rst in pool.map(make_bulk, x):
                yield from rst


def futures():
    with ProcessPoolExecutor() as executor:
        for x in toolz.partition_all(group, seq):
            for rst in executor.map(make_bulk, x):
                yield from rst


def loky():
    executor = get_reusable_executor()
    for x in toolz.partition_all(group, seq):
        for rst in executor.map(make_bulk, x):
            yield from rst


def joblib():
    for x in toolz.partition_all(group, seq):
        task = Parallel(n_jobs=-1)(delayed(make_bulk)(i) for i in x)
        for rst in task:
            yield from rst
