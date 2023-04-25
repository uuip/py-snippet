import platform
import time

# 两个进度条，一个只显示desc
# status = P.Progress(TextColumn("{task.description}"))
# status_task = status.add_task("some print", total=None)
# progress_group = Group(status, pbar)

# status = tqdm(total=0, position=1, bar_format='{desc}')

if platform.system() == "Windows":
    from ctypes import windll

    timeBeginPeriod = windll.winmm.timeBeginPeriod
    timeBeginPeriod(1)


def test_tqdm_terminal():
    from tqdm import tqdm

    with tqdm(range(500)) as pbar:
        for x in pbar:
            pbar.set_description(f"{x:<8}")

            if x % 50 == 0:
                pbar.write(f"\r{x} {time.time()}")  # \r for running in pycharm
            time.sleep(0.001)


def test_tqdm_jlab():
    from tqdm.auto import tqdm

    pbar = tqdm(range(3000), total=3000, dynamic_ncols=True)
    for x in pbar:
        pbar.set_description(str(x))

        if x % 500 == 0:
            print(f"{x} {time.time()}")
        time.sleep(0.001)


def test_rich():
    from rich.progress import Progress, TimeElapsedColumn, MofNCompleteColumn
    from rich.console import _is_jupyter
    from rich import reconfigure

    reconfigure(color_system="truecolor", force_terminal=not _is_jupyter())
    format = [
        *Progress.get_default_columns(),
        TimeElapsedColumn(),
        MofNCompleteColumn(),
    ]

    with Progress(*format) as pbar:
        for x in pbar.track(range(500)):
            pbar.update(0, description=f"{x}")

            if x % 50 == 0:
                print(f"{x} {time.time()}")
            time.sleep(0.001)


test_rich()
test_tqdm_terminal()
