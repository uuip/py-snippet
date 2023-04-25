import logging
from functools import singledispatchmethod

import arrow
import requests
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.contracts import find_matching_event_abi, find_matching_fn_abi
from web3.datastructures import AttributeDict

int_fields = [
    "block_number",
    "number",
    "log_index",
    "transaction_index",
    "gas",
    "gas_price",
    "gas_limit",
    "gas_used",
    "receipt_cumulative_gas_used",
    "receipt_gas_used",
    "receipt_status",
    "difficulty",
    "total_difficulty",
    "transaction_count",
    "base_fee_per_gas",
    "balance",
    "token_id",
    "amount",
    "block_number_minted",
    "id",
    "decimals",
    "tokenId",
    "earning",
]

adapter = requests.adapters.HTTPAdapter(
    pool_connections=50, pool_maxsize=500, pool_block=False, max_retries=3
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


class MoralisApi:
    def __init__(self, api_key, chain="bsc"):
        # chain:  bsc testnet,bsc,eth
        self.host = "https://deep-index.moralis.io/api/v2"
        self.headers = {
            "accept": "application/json",
            "X-API-Key": api_key,
        }
        self.chain = chain

    @singledispatchmethod
    def _recursive_process(self, obj):
        return obj

    @_recursive_process.register
    def _process_dict(self, obj: dict):
        for k, v in obj.items():
            if isinstance(v, (list, dict)):
                self._recursive_process(v)
                continue
            if v:
                if "timestamp" in k or k == "created_at":
                    obj[k] = arrow.get(v).int_timestamp
                elif k == "updated_at":
                    obj[k] = arrow.get(float(v)).int_timestamp
                elif k in int_fields:
                    obj[k] = int(v)
                elif k == "nonce":
                    if v.startswith("0x"):
                        obj[k] = int(v, 16)
                    else:
                        obj[k] = int(v)
                elif k in [
                    "token_address",
                    "owner_of",
                    "from_address",
                    "to_address",
                    "address",
                    "sender",
                ]:
                    obj[k] = Web3.toChecksumAddress(v)

    @_recursive_process.register
    def _process_list(self, obj: list):
        for x in obj:
            if isinstance(x, dict):
                self._process_dict(x)

    def _request(self, path, params=None, payload=None):
        params = params or {"chain": self.chain}
        params["chain"] = self.chain
        if payload:
            rsp = session.post(self.host + path, headers=self.headers, params=params, json=payload)
        else:
            rsp = session.get(self.host + path, headers=self.headers, params=params)
        try:
            rst = rsp.json()
        except:
            logging.error(rsp.content)
            raise
        self._recursive_process(rst)
        return rst

    def _request_all(self, path, params=None, payload=None):
        params = params or {"chain": self.chain}
        params["chain"] = self.chain
        rst: dict = self._request(path, params=params, payload=payload)
        if "result" not in rst:
            logging.error(rst)
            raise KeyError
        for x in rst["result"]:
            if "total" in rst and type(x) is dict:
                x["total_result"] = rst["total"]
            yield x
        if "cursor" in rst:
            cursor = rst["cursor"]
            if cursor:
                params["cursor"] = cursor
                yield from self._request_all(path, params=params, payload=payload)
        elif set(rst.keys()) & {"total", "page", "page_size"}:
            offset = (rst["page"] + 1) * rst["page_size"]
            if offset < rst["total"]:
                params["offset"] = offset
                yield from self._request_all(path, params=params, payload=payload)

    def get_metadata_erc20(self, contract_address: str | list):
        path = "/erc20/metadata"
        params = {"chain": self.chain, "addresses": contract_address}
        return self._request(path, params)[0]

    def get_metadata_nft(self, contract_address):
        path = f"/nft/{contract_address}/metadata"
        return self._request(path)

    def holder_nfts_on_contract(self, contract_address: str, holder_address: str):
        path = f"/{holder_address}/nft/{contract_address}"
        yield from self._request_all(path)

    def holder_nfts(self, holder_address: str):
        # 账户的nft, ERC721 and ERC1155
        path = f"/{holder_address}/nft"
        yield from self._request_all(path)

    def minted_nfts(self, contract_address):
        path = f"/nft/{contract_address}"
        params = {"chain": self.chain, "limit": 100}
        yield from self._request_all(path, params)

    def nft_holders(self, contract_address):
        path = f"/nft/{contract_address}/owners"
        yield from self._request_all(path)

    def nft_detail(self, contract_address: str, token_id: int):
        path = f"/nft/{contract_address}/{token_id}"
        return self._request(path)

    # def nft_detail_owner(self, contract_address: str, token_id: int):
    #     # cost 25CU, but same as  path = f'/nft/{contract_address}/{token_id}'
    #     path = f'/nft/{contract_address}/{token_id}/owners'
    #     return self._request(path)['result'][0]

    def nft_last_transfer(self, erc721_address: str, token_id: int):
        path = f"/nft/{erc721_address}/{token_id}/transfers"
        rst = self._request(path)
        if "result" not in rst:
            logging.error(rst)
            raise KeyError
        return rst["result"][0]

    def search_nft(self, contract_address, q):
        path = "/nft/search"
        params = {"q": q, "filter": "name"}
        yield from self._request_all(path, params)

    def datetoblock(self, date):
        path = "/dateToBlock"
        params = {"date": date, "chain": self.chain}
        return self._request(path, params=params)["block"]

    def get_block(self, block: int):
        # 获取块信息, 包含交易, 且gasprice与gasused同时返回
        path = f"/block/{block}"
        return self._request(path)

    def get_transaction(self, tx_hash: str):
        # 交易信息及回执, 即gasprice与gasused同时返回
        path = f"/transaction/{tx_hash}"
        return self._request(path)

    def get_transactions_by_address(
        self,
        address: str,
        from_block: int = None,
        to_block=None,
        from_date=None,
        to_date=None,
    ):
        # 获取账号/合约交易
        if from_block:
            section = {
                "from_block": from_block,
                "to_block": to_block,
            }
        else:
            section = {
                "from_date": from_date,
                "to_date": to_date,
            }
        path = f"/{address}"
        params = {"chain": self.chain, "cursor": None}  # 读取下一页
        params.update(section)
        yield from self._request_all(path, params)

    def get_balance(self, address: str):
        path = f"/{address}/balance"
        return self._request(path)["balance"]

    def get_token_balance(self, contract_address: str, accound_address: str):
        # erc20 token 余额
        path = f"/{accound_address}/erc20"
        params = {"chain": self.chain, "token_addresses": contract_address}
        return self._request(path, params)[0]

    def call_func(self, contract_address: str, abi: list, function_name: str, args: list):
        # params 的key应当与abi定义的参数名字相同
        w3 = Web3()
        fn_abi = find_matching_fn_abi(abi, w3.eth.codec, function_name, args)
        kwargs = {x["name"]: y for x, y in zip(fn_abi["inputs"], args)}
        path = f"/{contract_address}/function"
        params = {"chain": self.chain, "function_name": function_name}
        payload = {"abi": abi, "params": kwargs}
        rst = session.post(
            self.host + path, json=payload, headers=self.headers, params=params
        ).json()
        if isinstance(rst, dict):
            rst_keys = [x["name"] for x in fn_abi["outputs"]]
            rst = {k: rst[k] for k in rst.keys() if k in rst_keys}
        return rst

    def processed_logs(
        self,
        contract_address: str,
        abi: dict,
        event_name: str,
        from_block: int = None,
        to_block=None,
        from_date=None,
        to_date=None,
    ):
        if from_block:
            section = {
                "from_block": from_block,
                "to_block": to_block,
            }
        else:
            section = {
                "from_date": from_date,
                "to_date": to_date,
            }
        # log 缺少 transactionIndex，logIndex
        event_abi = find_matching_event_abi(abi, event_name)
        event_args = ",".join(x["type"] for x in event_abi["inputs"])
        topic = Web3.keccak(text=f"{event_name}({event_args})").hex()
        path = f"/{contract_address}/events"
        params = {
            "chain": self.chain,
            "topic": topic,
        }
        params.update(section)
        yield from self._request_all(path, params, payload=event_abi)

    # def raw_logs(self, contract_address: str, from_block: int = 1, to_block=None,
    #              from_date=None, to_date=None):
    #     # log 缺少 transactionIndex，logIndex
    #     path = f"/{contract_address}/logs"
    #     params = {"chain": self.chain,
    #               "from_block": from_block,
    #               "to_block": to_block,
    #               "cursor": None  # 读取下一页
    #               }
    #     yield from self._request_all(path, params)


def format_log(log: dict):
    log["timestamp"] = log.pop("block_timestamp")
    log["address"] = Web3.toChecksumAddress(log["address"])
    log["blockNumber"] = log.pop("block_number")
    log["blockHash"] = HexBytes(log.pop("block_hash"))
    log["transactionHash"] = HexBytes(log.pop("transaction_hash"))
    log["args"] = AttributeDict(log.pop("data"))
    return AttributeDict(log)
