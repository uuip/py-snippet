# https://learnblockchain.cn/docs/web3.js/web3-eth.html#eth-gettransactionreceipt-return
# cumulativeGasUsed - Number: 该交易执行时其所在区块已经累计消耗的 gas 量。
# gasUsed- Number: 该交易本身所消耗的 gas 量

# 整理requests方式请求的目的是为了在协程中使用，web3py的协程很难控制

import base64
import json
import logging

import requests
import web3
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.abi import get_abi_output_types
from web3._utils.contracts import find_matching_fn_abi

from web3utils.abi import token_abi

logging.basicConfig(level="INFO")
adapter = requests.adapters.HTTPAdapter(
    pool_connections=50, pool_maxsize=500, pool_block=False, max_retries=3
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

address = ""
private_key = ""

host = ""
token_address = "0xa4838122c683f732289805FC3C207Febd55BabDD"

w3 = Web3(web3.HTTPProvider(host, session=session, request_kwargs={"timeout": (5, 10)}))
w3.middleware_onion.inject(web3.middleware.geth_poa_middleware, layer=0)


def block_info():
    # 当前块高
    # w3.eth.get_block_number()
    w3.eth.block_number
    # 块信息
    w3.eth.get_block("latest").timestamp


def get_balance():
    # 账户余额
    w3.eth.get_balance(address)


def token_balance():
    token_contract = w3.eth.contract(token_address, abi=token_abi)
    # token余额
    token_contract.caller.balanceOf(address)
    # token小数位
    token_contract.caller.decimals()
    # 合约函数另一种调用
    token_contract.functions.decimals().call()


def token_balance_raw():
    token_contract = Web3().eth.contract(token_address, abi=token_abi)
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "to": token_address,
                # "data": Web3.keccak(text='balanceOf(address)').hex()[:10] + "0" * 24 + address[2:]
                "data": token_contract.encodeABI("balanceOf", [address]),
            },
            "latest",
        ],
    }
    rst = session.post(host, json=payload).json()["result"]
    Web3.fromWei(Web3.toInt(hexstr=rst), "ether")


def make_transaction():
    # 普通转账交易
    # transaction = {
    #     'gasPrice': w3.eth.gasPrice,
    #     'to': address,
    #     'value': 100,
    #     'gas': 2000000,
    #     'nonce': 0
    # }

    # 合约交易
    nonce = w3.eth.get_transaction_count(address)
    contract = w3.eth.contract(token_address, abi=token_abi)
    transaction = contract.functions.heal(3795, 5).build_transaction(
        {"gas": 10**5, "gasPrice": w3.eth.gasPrice, "nonce": nonce}
    )
    signed_txn = web3.Account.sign_transaction(transaction, private_key=private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(tx_hash.hex())


def sign_recover_message():
    # 签名数据
    message = encode_defunct(
        Web3.solidityKeccak(
            ["address", "address", "uint256[]", "uint256"],
            [token_address, address, [], 0],
        )
    )
    signed_message = web3.Account.sign_message(message, private_key)
    # 验证数据
    web3.Account.recover_message(message, signature=signed_message.signature)


def batch_block_info():
    # 批量块信息
    payload = []
    for id, bn in enumerate([19460832, 19460830]):
        payload.append(
            {
                "id": id,
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(bn), True],
            }
        )
    session.post(host, json=payload).json()


def batch_receipt():
    # 批量获取交易信息
    payload = []
    for id, tx in enumerate(
        [
            "0x809724aa0d250c9277117a07e3d9d1d742d89deb71591d6ff7525a261a75566c",
            "0x76a151aa7c3d6bd28ec2972005cea496d79dfc9ed59e15b9e82768958e7d452c",
        ]
    ):
        payload.append(
            {
                "id": id,
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx],
            }
        )
    session.post(host, json=payload).json()


def call_func(contract_address, abi, func: str, args: list, blocknum: int | str = "latest"):
    # 调用合约函数, 参照 web3.contract.call_contract_function
    if type(blocknum) is int:
        blocknum = hex(blocknum)
    contract = Web3().eth.contract(contract_address, abi=abi)
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "to": contract_address,
                # "data": encode_transaction_data(w3, func, contract_abi=abi, args=args)
                "data": contract.encodeABI(func, args),
            },
            blocknum,
        ],
    }
    result = session.post(host, json=payload)
    return format_result(abi, func, args, result)


def format_result(abi, func, args, result):
    try:
        return_data = result.json()["result"]
    except:
        print(f"{result=}")
        return
    if return_data == "0x":
        return
    fn_abi = find_matching_fn_abi(abi, Web3().codec, func, args)
    output_types = get_abi_output_types(fn_abi)
    output_data = w3.eth.codec.decode_abi(output_types, HexBytes(return_data))
    if len(output_data) == 1:
        rst = output_data[0]
        if isinstance(rst, str) and rst[:28] == "data:application/json;base64":
            return json.loads(base64.b64decode(rst[28:]))
        elif isinstance(rst, str) and rst.startswith("0x") and len(rst) == 42:
            return Web3.toChecksumAddress(rst)
        return rst
    else:
        rst_keys = [x["name"] for x in fn_abi["outputs"]]
        return {k: v for k, v in zip(rst_keys, output_data)}


async def batch_logs_raw(host, contract_addresses: list | str, from_block: int, to_block: int = 0):
    logging.info(f"get log from {host}")
    if not to_block:
        to_block = w3.eth.block_number
    logging.info(f"get log {from_block=} {to_block=}")
    payload = {
        "id": 1,
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [
            {
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "address": contract_addresses,
            }
        ],
    }

    rst = session.post(host, json=payload).json()["result"]
    return map(format_raw_log, rst)


def format_raw_log(log):
    log["address"] = Web3.toChecksumAddress(log["address"])
    log["logIndex"] = Web3.toInt(hexstr=log["logIndex"])
    log["blockNumber"] = Web3.toInt(hexstr=log["blockNumber"])
    log["transactionIndex"] = Web3.toInt(hexstr=log["transactionIndex"])
    log["blockHash"] = HexBytes(log["blockHash"])
    log["transactionHash"] = HexBytes(log["transactionHash"])
    log["topics"] = list(map(HexBytes, log["topics"]))
    return AttributeDict(log)
