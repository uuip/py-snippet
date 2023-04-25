## 本项目初版状态描述：

1. 每个计算过程分为3步，约20个步骤：
 - 读取csv为iter
 - 计算  
   `iter_result = map(some_func,iter)`
 - 结果写出到csv
2. 经测试可以处理几M或500万数据。

3. 客户声明要处理的数据有5千万。  
经测试： 本项目初版不能处理5千万数据。  
具体表现为pandas加载文件时提示numpy不能分配内存...  
- 开发阶段数据：29G 5.0千万，3个string字段，59个float或int字段；  
- 客户现场数据：最高 21G 9.1千万，3个string字段，52个float或int字段，最低3千万，7G；10年数据。

4. 修改出错步骤为：
```python
def csv_to_df(file_path):
    f = open(file_path, encoding="utf-8")
    reader = pd.read_csv(f, sep=",", iterator=True)
    loop = True
    chunk_size = 50 * 1024 **2
    chunks = []
    while loop:
        try:
            chunk = reader.get_chunk(chunk_size)
            chunks.append(chunk)
        except StopIteration:
            loop = False
    df = pd.concat(chunks, axis=0, ignore_index=True)
    f.close()
    return df
```
5. 正常运行后，处理5千万需要1.5天。

## 优化方向：
1. 批量处理取代逐行处理
   - 使用pandas Dataframe 处理二维表
   - 使用合适的框架加速pandas：选择Dask
2. 结构化文件取代csv
   - 确定好框架后，根据框架支持来选择：选择parquet

## 框架选择：
- 标准库多进程
- Dask
  - 优点：
    - 兼容绝大多数pandas常用方法
    - 多核计算
    - 文件io快
    - lazy load  
  - 缺点：
    - merge, join。千万级数据不要在dask里搞，在on是非索引时，150G内存不够。ray也是一样的。
    - 默认每个分片的索引在分区内是单调递增的；与pandas不同。
***

- Numba
  - 不适用
- Nuitka
- Cython
  - 编译失败
- Pypy 
  - Linux aarch64 运行失败
  - X64架构，普通计算速度弱于CPython多进程，但差距不大。
- swifter 基于dask
   - 未测试
- Modin 基于dask or ray
  - 计算失败
- pandarallel 基于标准库多进程，文件缓存
  - 计算失败

- Ray：  
  机器学习框架，用来组织各种模型训练。它不是数据治理工具，它只有dataset。也有类似pandas的方法，但是不兼容。  
  Dask不满足要求时，可以用这个。  
  - 优点：
    - 集群扩展性
    - 提供共享内存支持。（float,int, pickle 5)
  - 缺点：
    - csv内存加载。
    - Linux aarch64 有个依赖包要先装上rust环境，和 Mac M1 下安装包得参照文档装依赖。

- Vaex：  
网上有很多Vaex的《前言》性质介绍。其中宣传最多的是lazy load。
我很怀疑那些人是不是只是拿几条体验了一下。

  - 优点：
    - lazy load. 即使csv也可以。（pandas内存加载）
    - 虚拟列。列只是表达式，在最后计算阶段呈现。（pandas即时计算）

  - 缺点：
    - io：慢。读写csv，与纯python有一比，40分钟没搞完，直接ctrl+c了。
          26G csv即使转换为hdf5，要15分钟。
    - 文档：大体看完一遍后没理清它的自定义函数怎么用。相对与pandas，vaex的apply传参数比较离谱。
    - 学习成本：除了pd外，再学一个dataframe。
    - 优点项的条目不是它独有。


