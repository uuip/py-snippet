# coding=utf-8

import re
import shlex
import subprocess
import traceback
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from requests.utils import urlparse


def rtsp_record(url: str, time=1800, retry=2):
    url_split = urlparse(url)
    ch = re.search("channel=(.*?)&", url)
    if ch:
        channel = ch[1]
    else:
        channel = "0"

    base_name = f"{url_split.hostname}-{channel}"
    part = 1
    mp4_loc_path = f"{base_name}-{part}.mp4"
    while Path(mp4_loc_path).exists():
        part += 1
        mp4_loc_path = f"{base_name}-{part}.mp4"

    mp4_time = sum(get_duration(f) for f in Path(".").glob(f"{base_name}*.mp4"))
    time = int(time - mp4_time)
    if time <= 0:
        return

    command = (
        'ffmpeg -re -loglevel error -hide_banner -stimeout 30000000 -rtsp_transport tcp  -i "" '
        f"-vsync 0 -copyts -avoid_negative_ts make_zero -c:a aac -c:v libx264 -t {time} -y"
    )
    command = shlex.split(command)
    command[10] = url
    command.append(mp4_loc_path)
    returncode = run_command(command)
    if returncode == 0:
        pass
    else:
        print("ffmpeg has a error", url)
    mp4_time = sum(get_duration(f) for f in Path(".").glob(f"{base_name}*.mp4"))
    if mp4_time < 1800 and retry > 0:
        rtsp_record(url, int(1800 - mp4_time), retry - 1)


def run_command(command):
    returncode = -1
    try:
        p = subprocess.run(
            command, timeout=60 * 35, stderr=subprocess.STDOUT, stdout=subprocess.PIPE
        )
        returncode = p.returncode
    except subprocess.TimeoutExpired:
        print(f"record cam TimeoutExpired {command}")
    except:
        traceback.print_exc()
        print(f"record cam failed {command}")
    return returncode


def make_snapshot(file):
    file = Path(file)
    command = f"ffmpeg.exe -loglevel error -hide_banner -i {file.name} -ss 00:00:05 -frames:v 1 -y {file.stem}.jpg"
    command = shlex.split(command)
    subprocess.run(command)


def get_duration(file):
    file = Path(file)
    command = f"ffprobe.exe -loglevel error -hide_banner -of default=noprint_wrappers=1:nokey=1 -show_entries format=duration -i {file.name}"
    command = shlex.split(command)
    p = subprocess.run(command, capture_output=True)
    if p.stdout:
        d = p.stdout.decode().strip()
        return float(d)
    else:
        return 0


if __name__ == "__main__":
    # ffplay -loglevel info -hide_banner -rtsp_transport tcp  -i
    rtsp_urls = set()
    with open(r"C:\Users\sharp\Desktop\rtsp.txt", encoding="utf8") as f:
        for l in f:
            l = l.strip()
            if l:
                rtsp_urls.add(l)
    # with open(r"C:\Users\sharp\Desktop\rtsp.txt", encoding='utf8') as f:
    #     for l in f:
    #         l = l.strip()
    #         if l:
    #             l = re.sub('channel=.*?&', 'channel={}&', l)
    #             for x in range(1, 33):
    #                 rtsp_urls.add(l.format(x))
    with ProcessPoolExecutor(max_workers=4) as executor:
        executor.map(rtsp_record, rtsp_urls)
        executor.shutdown(wait=True)
    # for f in Path('.').glob('*.mp4'):
    #     make_snapshot(f)
    # url='rtsp://admin:888888@223.197.209.186:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif'
    # rtsp_record(url)
