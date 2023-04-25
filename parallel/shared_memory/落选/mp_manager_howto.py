import multiprocessing as mp

if __name__ == "__main__":
    from common import *

    # 默认fork的子进程会无条件复制父进程内存
    mp.set_start_method("spawn")
    df, big = make_data()
    with mp.Manager() as manager:
        d = manager.dict(big)
        ns = manager.Namespace()
        ns.someattr = df

        p1 = mp.Process(target=test_big, args=(d,))
        # 这里不能传ns.someattr, 这样是把df作为参数传入
        p2 = mp.Process(target=test_df, args=(ns,))
        for x in [p1, p2]:
            x.start()
        for x in [p1, p2]:
            x.join()
