import multiprocessing as mp
from multiprocessing.shared_memory import ShareableList


def test(arg):
    print(arg[0])


if __name__ == "__main__":
    mp.set_start_method("spawn")

    shared_arr = mp.Array("f", [1.4, 2.1])
    shared_arr2 = ShareableList([1.89, 2.1, "aaa"])
    p = mp.Process(target=test, args=(shared_arr,))
    p.start()
    p.join()
    p = mp.Process(target=test, args=(shared_arr2,))
    p.start()
    p.join()

    del shared_arr
    shared_arr2.shm.close()
    shared_arr2.shm.unlink()
