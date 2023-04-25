from contract import Contract, MUltiContractsLogs

from moralis import MoralisApi
from nodereal import NoderealApi

m = MoralisApi("", chain="bsc")
n = NoderealApi(host)

# 合约一共发行的nft数量
print(n.nft_count(ship_address))

# nft持有者数量
# print(n.nft_collection_holders_count(sample1155))

# 合约发行的nft列举
# for x in n.minted_nfts(ship_address):
#     print(x)
# for x in m.minted_nfts(ship_address):
#     print(x)

# nft持有者列举
# for x in n.nft_holders(ship_address):
#     print(x)
# for x in m.nft_holders(ship_address):
#     print(x)

# nft 持有者详情
# for x in n.holder_nfts_on_contract(ship_address, account_address):
#     print(x)
# for x in m.holder_nfts_on_contract(ship_address, account_address):
#     print(x)

# token_id 详情
# print(n.nft_detail(ship_address, 16919))
# print(m.nft_detail(ship_address,16919))

# token_id 所有者
# print(n.nft_holder(ship_address, 16919))
# print(m.nft_detail(ship_address,16919))

# 交易详情
# print(n.get_transaction(tx_hash=))
# print(n.get_transaction_receipts_by_blocknumber(21435139))
# m.get_transaction(tx_hash=)

ship_contract = Contract(ship_address, ship_abi, host)
# for x in ship_contract.log(21412749, to_block=21412749,event='Transfer'):
#     print(x)

cs = MUltiContractsLogs([ship_address], [ship_abi], host)
# for x in cs.batch_logs(21412749):
#     print(x)
