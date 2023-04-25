# 多进程间共享数据
## 标准库 multiprocessing
1. 共享内存
```python
import multiprocessing as mp


def test(arg):
    print(arg[0])


if __name__ == "__main__":
    mp.set_start_method("spawn")

    shared_some = mp.Array("f", [1.4, 2.1])

    p = mp.Process(target=test, args=(shared_some,))
    p.start()
    p.join()
```

2. manager代理
```python
from multiprocessing import Process, Manager
from functools import wraps
import numpy as np
import pandas as pd
import psutil
import sys


def log_mem(func):
    @wraps(func)
    def wrap(*args):
        mem1 = psutil.Process().memory_info().rss
        print(f"{func.__name__} init memory: ", mem1 / 1024**2, "MB")
        rst = func(*args)
        mem2 = psutil.Process().memory_info().rss
        print(f"{func.__name__} use memory: ", (mem2 - mem1) / 1024**2, "MB")
        return rst

    return wrap


@log_mem
def test_big(arg):
    print(len(arg), arg[5678])


@log_mem
def test_df(arg):
    print(arg.someattr.iloc[0:3])


if __name__ == "__main__":
    df = pd.DataFrame(np.random.randint(2000, 5000, 500_0000), columns=["age"])
    print("df size: ", df.memory_usage(deep=True).sum() / 1024**2, "MB")

    mem1 = psutil.Process().memory_info().rss
    big = df.to_dict("index")
    print("big dict size with getsizeof: ", sys.getsizeof(big) / 1024**2, "MB")

    with Manager() as manager:
        d = manager.dict(big)
        ns = manager.Namespace()
        ns.someattr = df

        p1 = Process(target=test_big, args=(d,))
        # 这里不能传ns.someattr, 这样是把df作为参数传入
        p2 = Process(target=test_df, args=(ns,))
        for x in [p1, p2]:
            x.start()
        for x in [p1, p2]:
            x.join()
```
> df size:  38.1470947265625 MB  
big dict size with getsizeof:  160.00009155273438 MB  
test_big init memory:  76.0625 MB  
5000000 {'age': 4459}  
test_big use memory:  0.046875 MB  
test_df init memory:  76.3125 MB  
    age  
0  4102  
1  2529  
2  3805  
test_df use memory:  65.40625 MB  


3. 小结：  


## ray
ray的共享对象基于 pyarrow.Plasma, 如此一来门槛低了些。
```python
import pandas as pd
import ray
from dask import dataframe as dd
from ray._private.internal_api import free
from ray.util.dask import enable_dask_on_ray

k,v,r = "name","age","releation"
df = dd.read_parquet(...)
# a large object we will use in apply
cache = {k: v for k, v in df[[k, v]].itertuples(index=False)}


def mp_func(column, cache):
    ...
    return 0


ray.init()
with enable_dask_on_ray():
    shared_cache = ray.put(cache)
    result: pd.Series = (
            df[r]
            .apply(mp_func, args=(shared_cache,), meta=(None, float))
            .compute()
            .astype("float64")
    )
free([shared_cache])
ray.shutdown()
```
## vineyard

## lmdb
## pyarrow.Plasma
[官网说明](https://arrow.apache.org/docs/python/plasma.html)
```shell
plasma_store -m 1000000000 -s /tmp/plasma
```
```python
import pyarrow as pa
import pandas as pd
import pyarrow.plasma as plasma
client = plasma.connect("/tmp/plasma")

d = {'one' : pd.Series([1., 2., 3.], index=['a', 'b', 'c']),
     'two' : pd.Series([1., 2., 3., 4.], index=['a', 'b', 'c', 'd'])}
df = pd.DataFrame(d)
# 20位
object_id = plasma.ObjectID(np.random.bytes(20))

# 确定要分配的内存大小
record_batch = pa.RecordBatch.from_pandas(df)
mock_sink = pa.MockOutputStream()
with pa.RecordBatchStreamWriter(mock_sink, record_batch.schema) as stream_writer:
    stream_writer.write_batch(record_batch)
data_size = mock_sink.size()

# 写入内存
buf = client.create(object_id, data_size)
stream = pa.FixedSizeBufferWriter(buf)
with pa.RecordBatchStreamWriter(stream, record_batch.schema) as stream_writer:
    stream_writer.write_batch(record_batch)
# 完成写入，封闭
client.seal(object_id)

# 读取
[data] = client.get_buffers([object_id])
buffer = pa.BufferReader(data)
reader = pa.RecordBatchStreamReader(buffer)
record_batch = reader.read_next_batch()
result = record_batch.to_pandas()
```

