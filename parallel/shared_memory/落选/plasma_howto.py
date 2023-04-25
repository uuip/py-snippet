import multiprocessing as mp
import subprocess

import pyarrow as pa
import pyarrow.plasma as plasma

from common import *


def put(obj):
    # 20位
    client = plasma.connect("/tmp/plasma")
    object_id = plasma.ObjectID(np.random.bytes(20))

    # 确定要分配的内存大小
    record_batch = pa.RecordBatch.from_pandas(obj)
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
    return object_id


def get(object_id):
    client = plasma.connect("/tmp/plasma")
    [data] = client.get_buffers([object_id])
    buffer = pa.BufferReader(data)
    reader = pa.RecordBatchStreamReader(buffer)
    record_batch = reader.read_next_batch()
    result = record_batch.to_pandas()
    return result


def run_server():
    p = subprocess.Popen(["plasma_store", "-m", "1000000000", "-s", "/tmp/plasma"])
    return p


@log_mem
def test_df(arg):
    arg = get(arg)
    print(arg.iloc[5000:5008])


if __name__ == "__main__":
    ps = run_server()

    mp.set_start_method("spawn")

    df, big = make_data()
    df_id = put(df)
    print("put df size", f"{sys.getsizeof(df) / 1024 ** 2}")

    p = mp.Process(target=test_df, args=(df_id,))
    p.start()
    p.join()
    ps.terminate()
