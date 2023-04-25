import base64
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from xml.dom.minidom import parseString

import requests
import web3
from hexbytes import HexBytes
from sqlalchemy import *
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import *
from tqdm import tqdm
from web3.datastructures import AttributeDict
from web3.exceptions import ContractLogicError

from abi import hull_abi, ship_abi
from dbmodel import HullTransfer, ScanConfig, Session, ShipTransfer, atomic, reflect
from libs.contract_log import Contract
from libs.moralis import MoralisApi
from libs.nodereal import NoderealApi

logging.getLogger("contractlog").setLevel("INFO")
adapter = requests.adapters.HTTPAdapter(
    pool_connections=50, pool_maxsize=500, pool_block=False, max_retries=3
)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

ship_address = "0xE5913A0358d1600fBF3D73DF2F1e2d791228A8b1"
hull_address = "0x4f0C8a8085774b28999f149954c908273D6632dF"
fixed_price_hull = "0x749bCD8e14ef7Aa3F1F35FCE0Fd46bc7A5033a9c"
market_hull = "0x1De015789Ba95ff8C144B5fA7105bbc99827Ed13"
detect_address = "0x1bb832bcbbabC1774Ed2450b8346F352F4e17CBa"
staking_address = "0xA42eA1c6E2B06D26610745D99222344eE93C8dd6"
fixed_price_ship = "0x3987C21b99cEE9545778ab4341BC650d77Ab6191"
market_ship = "0xFC95B2fA657d5C2f2eDcEbd1a858F29dDAA57C46"
company_address = "0x8fe471d0B6269a51D2ceFc4B926853b3375ABb40"
zero_address = "0x0000000000000000000000000000000000000000"
hull_internal = [company_address, fixed_price_hull, hull_address, market_hull]
ship_internal = [
    company_address,
    fixed_price_ship,
    staking_address,
    detect_address,
    market_ship,
]

token_mapper = {
    "hull": {
        "address": hull_address,
        "table_name": "dungeon_hull",
        "transfer_model": HullTransfer,
        "abi": hull_abi,
        "internal": hull_internal,
    },
    "ship": {
        "address": ship_address,
        "table_name": "dungeon_ship",
        "transfer_model": ShipTransfer,
        "abi": ship_abi,
        "internal": ship_internal,
    },
}

host = "https://bsc-mainnet.nodereal.io/v1/60c2985572004f3faee5d6ab6e2e96f4"
m = MoralisApi("VQkQd2xfopYIzfCvnqguj8kMvCbp5BFgJpo2usta7QWqcpnQBv4qyhsgv68L3bhs")
n = NoderealApi(host)
w3 = web3.Web3(web3.HTTPProvider(host, session=session))


class AttributeDecoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AttributeDict):
            return dict(obj)
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


def decode_hull_metadata(data):
    text = base64.b64decode(data["image"].split(",")[-1]).decode()
    xml = parseString(text)
    return [node.firstChild.wholeText for node in xml.getElementsByTagName("text")]


@atomic
def filltable(s):
    st = insert(ScanConfig).values(
        [
            ("hull", n.get_contract_creation(hull_address) - 1),
            ("ship", n.get_contract_creation(ship_address) - 1),
        ]
    )
    s.execute(st)


class Token:
    def __init__(self, token_name):
        config = token_mapper[token_name]
        self.name = token_name
        self.address = config["address"]
        self.abi = config["abi"]
        self.c = w3.eth.contract(self.address, abi=self.abi)
        self.model = reflect(config["table_name"])
        self.transfer_model = config["transfer_model"]
        self.to_internal = config["internal"]
        self.from_internal = self.to_internal + [zero_address]

    def __repr__(self):
        return f"Token: {self.name}"

    @atomic
    def bulk_insert_or_update(s: Session, self, data):
        if type(data) is dict:
            data = [data]
        st = insert(self.model).values(data)
        cols = {k: getattr(st.excluded, k) for k in data[0]}
        do_update = st.on_conflict_do_update(index_elements=["token_id"], set_=cols)
        s.execute(do_update)

    @atomic
    def add_events(s: Session, self, data):
        st = (
            insert(self.transfer_model)
            .values(data)
            .on_conflict_do_nothing(index_elements=["transactionHash", "logIndex"])
        )
        s.execute(st)

    @atomic
    def update_flag(s: Session, self, num):
        st = update(ScanConfig).where(ScanConfig.contract == self.name).values(blocknumber=num)
        s.execute(st)

    @atomic
    def newtokens_from_db(s, self):
        # subq = select(self.model.token_id).scalar_subquery()
        # st = (
        #     select(self.transfer_model.token_id)
        #     .where(~self.transfer_model.token_id.in_(subq))
        #     .distinct(self.transfer_model.token_id)
        # )
        st = select(self.transfer_model.token_id).except_(select(self.model.token_id))
        return s.scalars(st).all()

    def nftmeta(self, token_id):
        rst = self.c.caller.tokenURI(token_id)
        # if rst[:28] == 'data:application/json;base64':
        return json.loads(base64.b64decode(rst[28:]))

    @atomic
    def owner_from_db_transfer(s, self, token_id):
        t = aliased(self.transfer_model)
        owner_case = case(
            (t.to.in_(self.to_internal) & t.from_.not_in(self.from_internal), t.from_),
            else_=t.to,
        ).label("owner")
        st = (
            select(owner_case)
            .distinct(t.token_id)
            .where(t.token_id == token_id)
            .order_by(t.token_id, desc(t.blockNumber), desc(t.logIndex))
        )
        return s.scalar(st)

    def owner_from_remote(self, token_id):
        while True:
            try:
                bsc_owner = self.c.caller.ownerOf(token_id)
            except ContractLogicError:
                return
            except:
                print(token_id, "suspend")
                time.sleep(1)
                continue
            break
        if bsc_owner in self.to_internal:
            tx = m.nft_last_transfer(self.address, token_id)
            if tx["from_address"] not in self.from_internal:
                return tx["from_address"]
        return bsc_owner

    def sync_event(self):
        with Session() as s:
            start = s.scalar(select(ScanConfig.blocknumber).where(ScanConfig.contract == self.name))
        end = w3.eth.block_number
        toadd = []
        pbar = tqdm(total=end - start, ncols=80)
        fields1 = (
            "transactionHash",
            "logIndex",
            "event",
            "transactionIndex",
            "blockNumber",
        )
        c = Contract(self.address, self.abi, host)
        for x in c.logs(start + 1, end, "Transfer"):
            x_dict = json.loads(json.dumps(x, cls=AttributeDecoder, ensure_ascii=False))
            data = {field: x_dict[field] for field in fields1}
            data["from"] = x.args["from"]
            data["to"] = x.args["to"]
            data["token_id"] = x.args["tokenId"]
            toadd.append(data)
            if len(toadd) >= 100:
                self.add_events(toadd)
                toadd = []
                self.update_flag(x.blockNumber)
            pbar.n = x.blockNumber - (start + 1)
            pbar.update(0)
        pbar.n = end - start
        pbar.update(0)
        pbar.close()
        if toadd:
            self.add_events(toadd)
        self.update_flag(end)

    def refresh_all_from_db(self):
        new_tokens = self.newtokens_from_db()
        to_add = []
        for x in [new_tokens[i : i + 200] for i in range(0, len(new_tokens), 200)]:
            for y in x:
                obj = {"token_id": y, "owner": self.owner_from_db_transfer(y)}
                metadata = self.nftmeta(y)
                if self.name == "ship":
                    obj.update({"class": metadata["name"], "name": metadata["description"]})
                else:
                    attr = decode_hull_metadata(metadata)
                    obj.update({"type": attr[0]})
                to_add.append(obj)
        if to_add:
            self.bulk_insert_or_update(to_add)

        t = aliased(self.transfer_model)

        # 获取分组第一条：窗口函数
        # win = select(
        #     t.token_id,
        #     t.from_,
        #     t.to,
        #     func.row_number()
        #     .over(
        #         partition_by=t.token_id,
        #         order_by=[desc(t.blockNumber), desc(t.logIndex)],
        #     )
        #     .label("new_index"),
        # ).subquery()
        # owner_case = case(
        #     (
        #         win.c.to.in_(self.internal) & win.c.from_.not_in(self.internal),
        #         win.c.from_,
        #     ),
        #     else_=win.c.to,
        # ).label("owner")
        # owner_table = (
        #     select(win.c.token_id, owner_case).where(win.c.new_index == 1).subquery()
        # )

        # 获取分组第一条：distinct on
        owner_case = case(
            (t.to.in_(self.to_internal) & t.from_.not_in(self.from_internal), t.from_),
            else_=t.to,
        ).label("owner")
        owner_table = (
            select(t.token_id, owner_case)
            .distinct(t.token_id)
            .order_by(t.token_id, desc(t.blockNumber), desc(t.logIndex))
            .subquery()
        )

        # 批量更新：https://docs.sqlalchemy.org/en/20/tutorial/data_update.html#correlated
        # -updates
        # query_owner = (
        #     select(owner_table.c.owner)
        #     .where(owner_table.c.token_id == self.model.token_id)
        #     .scalar_subquery()
        # )
        # st = update(self.model).values(owner=query_owner)

        # 批量更新：https://docs.sqlalchemy.org/en/20/tutorial/data_update.html#update
        # -fromowner_table
        st = (
            update(self.model)
            .where(owner_table.c.token_id == self.model.token_id)
            .values({self.model.owner: owner_table.c.owner})
        )

        # 批量更新： where与value绑定到字典的key
        # st = (
        #     update(self.model)
        #     .where(self.model.token_id == bindparam("tid"))
        #     .values(owner=bindparam("real_owner"))
        # )
        # to_update = []
        # for x in {}:
        #     to_update.append(x)
        # s.connection().execute(st, to_update)
        # s.connection().commit()
        #
        with Session() as s:
            s.execute(st)
            s.commit()

    def refresh_all_from_remote(self):
        collect = {}
        total = n.nft_count(self.address)
        s = Session()
        db_total = s.scalar(select(func.count(self.model.token_id)))
        if db_total == total:
            token_ids = s.scalars(select(self.model.token_id))
            collect = {x: {} for x in token_ids}
        else:
            for x in tqdm(m.minted_nfts(self.address), total=total, ncols=80):
                if not x["metadata"]:
                    metadata = self.nftmeta(x["token_id"])
                else:
                    metadata = json.loads(x["metadata"])
                if self.name == "ship":
                    collect[x["token_id"]] = {
                        "class": metadata["name"],
                        "name": metadata["description"],
                    }
                else:
                    attr = decode_hull_metadata(metadata)
                    collect[x["token_id"]] = {
                        "type": attr[0]
                    }  # c.caller.getUserName(x.args.tokenId)

        pbar = tqdm(total=len(collect), ncols=80)

        def check(token_id):
            pbar.set_description_str(f"{token_id:<8}")
            owner = self.owner_from_remote(token_id)
            db_owner = s.scalar(select(self.model.owner).where(self.model.token_id == token_id))
            if owner != db_owner:
                pbar.write(f"\r{self.name} {token_id} {owner=} {db_owner=}")
            self.bulk_insert_or_update({"token_id": token_id, "owner": owner} | collect[token_id])

        # max 6 for MoralisApi
        with ThreadPoolExecutor(max_workers=5) as ex, pbar:
            for x in ex.map(check, collect):
                pbar.update(1)
        s.close()


if __name__ == "__main__":
    t = Token("hull")
    t.sync_event()
    t.refresh_all_from_db()
    t = Token("ship")
    t.sync_event()
    t.refresh_all_from_db()
