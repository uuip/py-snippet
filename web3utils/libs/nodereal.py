import logging
from functools import lru_cache

import requests

logging.basicConfig(level="INFO")
adapter = requests.adapters.HTTPAdapter(
    pool_connections=50, pool_maxsize=500, pool_block=False, max_retries=3
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)


class NoderealApi:
    # 只支持bsc主网
    def __init__(self, host):
        self.host = host
        self.page_size = hex(100)

    @lru_cache
    def nft_type(self, contract_address):
        return self.token_meta(contract_address)["result"]["tokenType"]

    def token_meta(self, contract_address):
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getTokenMeta",
            "params": [contract_address],
            "id": 0,
        }
        return session.post(self.host, json=payload).json()

    def nft_count(self, contract_address):
        # 已发行的nft数量, 同getTotalSupply721，1155
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getNFTTokenCount",
            "params": [contract_address],
            "id": 1,
        }
        rsp = session.post(self.host, json=payload).json()
        return int(rsp["result"], 16)

    def minted_nfts(self, contract_address):
        # 已发行的nft列表
        nft_type = self.nft_type(contract_address)
        next_page = ""
        while True:
            payload = {
                "jsonrpc": "2.0",
                "method": "nr_getNFTTokens",
                "params": [contract_address, nft_type, self.page_size, next_page],
                "id": 1,
            }
            rst = session.post(self.host, json=payload).json()["result"]
            yield from rst["tokenIds"]
            if "pageKey" not in rst:
                break
            next_page = rst["pageKey"]
            if not next_page:
                break

    def nft_holders(self, contract_address):
        # nft的持有者
        withBalance = False
        next_page = ""
        nft_type = self.nft_type(contract_address)
        while True:
            payload = {
                "jsonrpc": "2.0",
                "method": "nr_getNFTCollectionHolders",
                "params": [
                    contract_address,
                    nft_type,
                    self.page_size,
                    next_page,
                    withBalance,
                ],
                "id": 1,
            }
            rst = session.post(self.host, json=payload).json()["result"]
            yield from rst["holderAddresses"]
            next_page = rst["pageKey"]
            if not next_page:
                break

    def holder_nfts_on_contract(self, contract_address, holder_address):
        # 用户持有的nft列举
        next_page = ""
        while True:
            payload = {
                "jsonrpc": "2.0",
                "method": "nr_getNFTInventory",
                "params": [holder_address, contract_address, self.page_size, next_page],
                "id": 1,
            }
            rst = session.post(self.host, json=payload).json()["result"]
            for item in rst["details"]:
                item["tokenId"] = int(item["tokenId"], 16)
                item["balance"] = int(item["balance"], 16)
                yield item
            next_page = rst["pageKey"]
            if not next_page:
                break

    def nft_holder(self, contract_address, token_id):
        # 某个token的所有者
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getNFTHolders",
            "params": [contract_address, hex(token_id)],
            "id": 1,
        }
        return session.post(self.host, json=payload).json()

    def nft_detail(self, contract_address, token_id):
        # 某个token的详情
        nft_type = self.nft_type(contract_address)
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getNFTMeta",
            "params": [contract_address, hex(token_id), nft_type],
            "id": 1,
        }
        return session.post(self.host, json=payload).json()

    def nft_holders_count(self, contract_address):
        # nft合约的持有者数量
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getNFTHolderCount",
            "params": [contract_address],
            "id": 1,
        }
        rst = session.post(self.host, json=payload).json()
        return int(rst["result"]["result"], 16)

    def nft_collection_holders_count(self, contract_address):
        # 与nft_holders_count(getNFTHolderCount)重复?
        nft_type = self.nft_type(contract_address)
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getNFTCollectionHolderCount",
            "params": [contract_address, nft_type],
            "id": 1,
        }
        rst = session.post(self.host, json=payload).json()
        return int(rst["result"], 16)

    # def getSummedSupply1155(self, contract_address):
    #     payload = {"jsonrpc": "2.0", "method": "nr_getSummedSupply1155",
    #                "params": [contract_address], "id": 1}
    #
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)

    # def getTokenBalance1155(self, contract_address, account_address, token_id):
    #     payload = {"jsonrpc": "2.0", "method": "nr_getTokenBalance1155",
    #                "params": [contract_address,
    #                           account_address, 'latest', hex(token_id)], "id": 1}
    #
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)
    #
    # def getTokenBalance721(self, contract_address, account_address):
    #     # 用户持有合约上多少个nft
    #     payload = {"jsonrpc": "2.0", "method": "nr_getTokenBalance721",
    #                "params": [contract_address, account_address, 'latest'], "id": 1}
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)

    # def getTotalSupply1155(self, contract_address, token_id):
    #     payload = {"jsonrpc": "2.0", "method": "nr_getTotalSupply1155",
    #                "params": [contract_address, 'latest', hex(token_id)], "id": 1}
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)

    # def getTotalSupply721(self, contract_address):
    #     # 与getNFTTokenCount相同
    #     payload = {"jsonrpc": "2.0", "method": "nr_getTotalSupply721",
    #                "params": [contract_address, 'latest'], "id": 0}
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)

    # def getTotalSupply20(self, contract_address):
    #     payload = {"jsonrpc": "2.0", "method": "nr_getTotalSupply20",
    #                "params": [contract_address, "latest"], "id": 1}
    #     rsp = session.post(self.host, json=payload).json()
    #     return int(rsp['result'], 16)

    def get_token_balance(self, contract_address: str, accound_address: str):
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getTokenBalance20",
            "params": [contract_address, accound_address, "latest"],
            "id": 1,
        }
        rsp = session.post(self.host, json=payload).json()
        return int(rsp["result"], 16)

    def get_contract_creation(self, contract_address):
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getContractCreationTransaction",
            "params": [contract_address],
            "id": 1,
        }
        return session.post(self.host, json=payload).json()["result"]["blockNumber"]

    def get_transaction(self, tx_hash):
        payload = {
            "jsonrpc": "2.0",
            "method": "nr_getTransactionDetail",
            "params": [tx_hash],
            "id": 1,
        }
        return session.post(self.host, json=payload).json()

    def get_transaction_receipts_by_blocknumber(self, start_block, stop_block=None):
        # 按块索引receipt，但没有汇总块信息与receipt, 比web3按单个交易查好点
        if not stop_block:
            stop_block = start_block + 1
        payload = []
        for id, bn in enumerate(range(start_block, stop_block)):
            payload.append(
                {
                    "id": id,
                    "jsonrpc": "2.0",
                    "method": "nr_getTransactionReceiptsByBlockNumber",
                    "params": [hex(bn)],
                }
            )
        return session.post(self.host, json=payload).json()

    def nft_last_transfer(self, contract_address: str, token_id: int):
        # nft最近的transfer，免费版step 1000
        nft_type = self.nft_type(contract_address).strip("ERC")
        next_page = ""
        step = 1000
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 0}
        latest = session.post(self.host, json=payload).json()["result"]
        end = int(latest, 16)
        while True:
            payload = {
                "jsonrpc": "2.0",
                "method": "nr_getAssetTransfers",
                "params": [
                    {
                        "category": [nft_type],
                        "fromBlock": hex(end - step),
                        "toBlock": hex(end),
                        "contractAddresses": [contract_address],
                        "order": "desc",
                        "excludeZeroValue": False,
                        "PageKey": next_page,
                        "maxCount": "0x3E8",  # 1000
                    }
                ],
                "id": 1,
            }
            rst = session.post(self.host, json=payload).json()["result"]
            if "transfers" in rst:
                for tx in filter(
                    lambda x: int(x["erc721TokenId"], 16) == int(token_id),
                    rst["transfers"],
                ):
                    return tx
            if "pageKey" not in rst:
                break
            next_page = rst["pageKey"]
            end = end - step - 1


if __name__ == "__main__":
    host = "https://bsc-mainnet.nodereal.io/v1/60c2985572004f3faee5d6ab6e2e96f4"
    hull_address = "0x4f0C8a8085774b28999f149954c908273D6632dF"
    n = NoderealApi(host)
    print(n.nft_last_transfer(hull_address, 20575))
