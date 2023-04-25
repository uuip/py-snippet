import datetime
import socket
import traceback
from collections import defaultdict
from itertools import chain as _chain

from asgiref.sync import async_to_sync
from celery_chord.utils.log import get_task_logger
from channels.layers import get_channel_layer
from conf import config
from django.db.models import Count
from dungeon.models.auction_models import Staking
from triathon.celery import app
from utils.xmlrpc_to import TimeoutServerProxy as ServerProxy

from .generic import rd

# unique name for new instance, as redis Pub/Sub has no relation to the key space,
# Publishing on db 10, will be heard by a subscriber on db 1.
group_name = "prod-nft-v2"
rpc_server = config.rpc_api
server = ServerProxy(config.rpc_api, allow_none=True)
rd.setnx("flag_node_attack", 0)
logger = get_task_logger("nft")
channel_layer = get_channel_layer()


def sort_nft_type(item):
    try:
        return ["Daemon", "Destroyer", "Delusionist", "Dungeon"].index(item["class_field"])
    except ValueError:
        return 5


def calc_nft_rate():
    utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
    utc_hour = utc_now.hour
    utc_ts = int(utc_now.timestamp())
    chains = Staking.objects.values("chain").order_by("chain").distinct()

    for chain in chains:
        chain_id = chain["chain"]
        if utc_hour in list(_chain(range(3, 9), range(10, 16), range(17, 23))):
            qs = Staking.objects.filter(chain=chain_id, start_time__lte=utc_ts, end_time__gt=utc_ts)
            ongoing = qs.values("name", "class_field").annotate(counts=Count("name")).order_by()
            if ongoing.exists():
                start_time = qs.values("start_time").first()["start_time"]
                rate = (utc_ts - start_time) / 6 / 3600
            else:
                continue
            ongoing = list(ongoing)
            ongoing.sort(key=sort_nft_type)
            all_nfts = sum([x["counts"] for x in ongoing])
            result = defaultdict(list)
            previous_actives = 0
            for nft in ongoing:
                v = int(nft["counts"])
                active = min(int(all_nfts * rate) + 1 - previous_actives, v)
                previous_actives += active
                result["data"].append({"name": nft["name"], "total": v, "active": active})
                # Reducing Nodes
                try:
                    if nft["name"] == "Reducing Nodes" and not int(rd.get("flag_node_attack") or 0):
                        reduce_node()
                except BaseException:
                    logger.exception("reduce_node error")
            result = dict(result)
            if result:
                result["stage"] = "current"
                result["timestamp"] = utc_ts
                # 0,97,Tusima
                if chain_id == 0:
                    result["chainid"] = "97"
                else:
                    result["chainid"] = "98"
                yield result
        else:
            result_next = defaultdict(list)
            waiting = (
                Staking.objects.filter(chain=chain_id, start_time__gt=utc_ts)
                .values("name")
                .annotate(total=Count("name"))
                .order_by()
            )

            for nft in waiting:
                # {'name': 'Physical Node Attack', 'counts': 1}
                nft["active"] = 0
                result_next["data"].append(nft)
            result_next = dict(result_next)
            if result_next:
                result_next["stage"] = "next"
                result_next["timestamp"] = utc_ts
                if chain_id == 0:
                    result_next["chainid"] = "97"
                else:
                    result_next["chainid"] = "98"
                yield result_next
            try:
                if int(rd.get("flag_node_attack") or 0):
                    add_node()
            except BaseException:
                logger.exception("add_node error")


def reduce_node():
    # chain detect has done this
    return
    rd.set("flag_node_attack", 1)
    try:
        server.DelBscNode("5", "bsc92")
    except socket.timeout:
        logger.error("socket.timeout when reduce_node")
    except BaseException:
        traceback.print_exc()


def add_node():
    # chain detect has done this
    return
    rd.set("flag_node_attack", 0)
    try:
        server.AddBscNode("5", "bsc92")
    except socket.timeout:
        logger.error("socket.timeout when add_node")
    except BaseException:
        traceback.print_exc()


@app.task(name="display_nft", expires=30)
def display_nft():
    try:
        for data in calc_nft_rate():
            async_to_sync(channel_layer.group_send)(
                group_name, {"type": "broadcast_message", "message": data}
            )
    except BaseException:
        logger.exception("display_nft error")
