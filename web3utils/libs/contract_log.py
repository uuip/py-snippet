import logging
import time

import requests
import web3
from web3 import Web3
from web3.contract import Contract as _Contract
from web3.datastructures import AttributeDict

logger = logging.getLogger("contractlog")
adapter = requests.adapters.HTTPAdapter(
    pool_connections=50, pool_maxsize=500, pool_block=False, max_retries=3
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)
#
#
#     topic[0] : keccak(“Transfer(address,address,uint256)”)，对事件的字符做keccak散列运算
#     topic[1] : address类型from参数补齐64位
#     topic[2] : address类型to参数补齐64位
# "topics": [
#   "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",  //keccak(Transfer(address,address,uint256))， //合约事件签名哈希值，对事件的字符做keccak散列运算
#   "0x000000000000000000000000b8262c6a2dcabd92a77df1d5bd074afd07fc5829",  //当前交易from的地址
#   "0x000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec7"   //当前交易to的地址
# ],


def make_topics(contract_addr, abi):
    contract = Web3().eth.contract(contract_addr, abi=abi)
    topic_dict = {}
    for x in contract.events._events:
        fn = getattr(contract.events, x["name"])
        topic = fn.build_filter().topics[0]
        topic_dict[topic] = fn
    return topic_dict


def process_log(topic_dict, log) -> AttributeDict:
    this_topic = log.topics[0].hex()
    if this_topic in topic_dict:
        fn = topic_dict[this_topic]
        event = fn().processLog(log)
        return event


class Contract(_Contract):
    def __init__(self, address, abi, host):
        self.web3 = Web3(
            web3.HTTPProvider(host, session=session, request_kwargs={"timeout": (5, 10)})
        )
        self.abi = abi
        self.address = address
        self.web3.middleware_onion.inject(web3.middleware.geth_poa_middleware, layer=0)
        self.step = 2000
        super().__init__(address)
        self.topics = make_topics(self.address, self.abi)

    def logs(self, from_block: int, to_block: int = None, event=None):
        if not to_block:
            to_block = self.web3.eth.block_number

        filter_query = {"address": [self.address]}
        if event:
            event_type = getattr(self.events, event)
            topic = event_type.build_filter().topics[0]
            topics = {topic: event_type}
            filter_query["topics"] = [topic]
        else:
            topics = self.topics

        for start in range(from_block, to_block + 1, self.step):
            stop = min(start + self.step - 1, to_block)
            filter_query.update(
                {
                    "fromBlock": start,
                    "toBlock": stop,
                }
            )
            logger.debug(f"get log {start=} {stop=}")
            while True:
                try:
                    logs = self.web3.eth.get_logs(filter_query)
                except:
                    logger.warning(f"retry log {start=} {stop=}")
                    time.sleep(1)
                    continue
                break
            yield from (process_log(topics, log) for log in logs)


class MUltiContractsLogs:
    def __init__(self, addresses, abis, host):
        self.w3 = Web3(
            web3.HTTPProvider(host, session=session, request_kwargs={"timeout": (5, 10)})
        )
        self.w3.middleware_onion.inject(web3.middleware.geth_poa_middleware, layer=0)
        self.contract_addresses = addresses
        self.topics = {}
        self.step = 2000
        for addr, abi in zip(addresses, abis):
            self.topics.update(make_topics(addr, abi))

    def batch_logs(self, from_block: int, to_block: int = 0):
        if not to_block:
            to_block = self.w3.eth.block_number

        for start in range(from_block, to_block + 1, self.step):
            stop = min(start + self.step - 1, to_block)
            filter_query = {
                "fromBlock": start,
                "toBlock": stop,
                "address": self.contract_addresses,
            }
            logger.info(f"get log {start=} {stop=}")
            logs = self.w3.eth.get_logs(filter_query)
            yield from (process_log(self.topics, log) for log in logs)
