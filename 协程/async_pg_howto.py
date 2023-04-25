import asyncio
from asyncio import create_task

import asyncpg
import httpx
from hexbytes import HexBytes
from web3 import Web3, HTTPProvider
from web3._utils.abi import get_abi_output_types
from web3._utils.contracts import find_matching_fn_abi, encode_transaction_data
from web3.contract import Contract

from abi import hull_abi, hull_attr_abi

hull_address = "0x4f0C8a8085774b28999f149954c908273D6632dF"
property_address = "0x0affE57400E3F27976489980f12f9A77A44e4095"

endpoint_url = "https://bsc-mainnet.nodereal.io/v1/60c2985572004f3faee5d6ab6e2e96f4"
w3 = Web3(HTTPProvider(endpoint_url))
contract = w3.eth.contract(hull_address, abi=hull_abi)
property_contract = w3.eth.contract(property_address, abi=hull_attr_abi)

timeout = httpx.Timeout(5, read=15, connect=5.0)
client = httpx.AsyncClient(timeout=timeout)


async def call_fn(contract: Contract, func: str, args: list):
    fn_abi = find_matching_fn_abi(contract.abi, contract.web3.eth.codec, func, args)
    output_types = get_abi_output_types(fn_abi)
    data = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {
                "to": contract.address,
                # contract.encodeABI('getUserName', args)}
                "data": encode_transaction_data(
                    contract.web3, func, contract.abi, fn_abi=fn_abi, args=args
                ),
            },
            "latest",
        ],
        "id": 1,
    }
    result = await client.post(endpoint_url, json=data)
    return_data = result.json()["result"]
    if return_data in {"", "0x"}:
        return ""
    output_data = w3.eth.codec.decode_abi(output_types, HexBytes(return_data))
    if len(output_data) == 1:
        return output_data[0]
    return output_data


async def main():
    conn: asyncpg.Connection = await asyncpg.connect(
        user="postgres", password="postgres", database="postgres", host="127.0.0.1"
    )

    async def procress(x):
        conn: asyncpg.Connection = await asyncpg.connect(
            user="postgres", password="postgres", database="postgres", host="127.0.0.1"
        )
        args = [int(x["token_id"])]
        print(args)

        tasks = []
        type_call = create_task(call_fn(contract, "getUserName", args))
        tasks.append(type_call)

        owner_call = create_task(call_fn(contract, "ownerOf", args))
        tasks.append(owner_call)

        scarcity_call = create_task(call_fn(property_contract, "getScarcity", args))
        tasks.append(scarcity_call)

        rst = await asyncio.gather(*tasks)
        hull_type, owner, scarcity = rst
        print(args, hull_type, owner, scarcity)
        await conn.execute(
            "update dungeon_hull set type=$1,owner=$2,scarcity=$3 where token_id=$4",
            hull_type,
            owner,
            scarcity,
            str(args[0]),
        )

        await conn.execute("commit")

    while True:
        group = await conn.fetch(
            "SELECT token_id,type,scarcity,owner FROM dungeon_hull  ORDER BY token_id::int8 DESC LIMIT 10"
        )
        if not group:
            break
        await asyncio.gather(*(create_task(procress(record)) for record in group))
        break

    await client.aclose()
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
