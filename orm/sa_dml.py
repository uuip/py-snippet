from sqlalchemy import *
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import *

from sa_utils import db, atomic

AutoBase = automap_base()
session = sessionmaker(bind=db, expire_on_commit=False, future=True)


class Detect(AutoBase):
    __tablename__ = "dungeon_detect"
    ship = relationship("Ship", back_populates="detect_collection")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.ship_id}>"


class Ship(AutoBase):
    __tablename__ = "dungeon_ship"
    detect_collection = relationship("Detect", back_populates="ship")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.token_id} {self.name}>"


AutoBase.prepare(autoload_with=db)
s = session(bind=db)

ship = Ship
detect = Detect
network = getattr(AutoBase.classes, "geoip_network")
# s.scalars(st).first()
# session开始后，查询出的对象会缓存；需要expire或refresh，或者新的session; 配合expire_on_commit

s.query(ship).where(ship.token_id == 5798)
st = select(ship).where(ship.token_id == 5798)

# 汇总
select(func.count("*")).select_from(ship)
st = select(func.sum(ship.total_reward))
# &, | and ~
st = select(network.network).where(text("network >> :ip")).params(ip="1.1.4.1")
st = select(network.network).where(network.network.op(">>")("1.1.4.1"))
st = select(network.geoname_id).group_by(network.geoname_id)
st = select(network).distinct(network.geoname_id)
# 排序
st = select(ship.name).order_by(ship.token_id.desc())
st = select(ship.name).order_by(asc("token_id"))
st = select(ship.name).order_by(text("token_id desc"))
# s.scalars(st,execution_options={"populate_existing":True})
# 指定输出字段
st = select(ship).with_only_columns(ship.name)  # 不包含id
st = select(ship).options(load_only(ship.name, ship.token_id))  # 包含id
# 传统用法
s.query(ship).with_entities(ship.name, ship.token_id).first()
# 列别名
st = select(ship.name, (ship.total_reward * 10).label("newtotal")).order_by(desc("newtotal"))

# 关联查询
st = select(ship).join(detect, ship.token_id == detect.ship_id).where(detect.round == 159)
st = select(ship).join(detect.ship).where(detect.round == 159).with_for_update()
st = select(ship.name).select_from(detect).join(ship).where(detect.round == 159)
st = select(ship.name, detect.round).join_from(ship, detect).where(detect.round == 159)
for x in s.execute(st):
    print(x.name, x.round)
st = (
    select(Bundle("attr", ship.name, detect.round))
    .join_from(ship, detect)
    .where(detect.round == 159)
)
for x in s.execute(st):
    print(x.attr.name, x.attr.round)

# n+1 避免, options中的字段需要是select表的一个字段

# 子表查父表
# 总1次查询
st = select(detect).join(ship).limit(5).options(contains_eager(detect.ship))
# joinedload 指定innerjoin，否则left join一次父表变成3表join, 总1次查询
# st = select(detect).options(joinedload(detect.ship, innerjoin=True).load_only(ship.name)).limit(5)
# 先查出limit数量的子表，然后发起第二条查询，父表id in 集合，总2次查询
# st = select(detect).options(selectinload(detect.ship).load_only(ship.name)).limit(5)
# immediateload 为子表第二条记录起每一条记录查一次父表，总次数为limit
# st=select(detect).options(immediateload(detect.ship).load_only(ship.name)).limit(5)
# 先查出limit数量的子表，然后发起第二条查询，父表join(前面查子表语句为子查询)，总2次查询; 但子表对象未关联父表对象，出错
# st=select(detect).options(subqueryload(detect.ship).load_only(ship.name)).limit(5)

# 父表查子表
# 先查出父表，然后查子表中父表id in ... 总2次查询
# st = select(ship).options(selectinload(ship.detect_collection)).limit(5)

# 父表查子表 + where
st = select(ship).join(detect).options(selectinload(ship.detect_collection)).where(detect.id == 2)

# 总结：过滤条件是对方表字段时，需要显式join，, 否则返回笛卡尔积（逗号分隔的两个表）

for x in s.scalars(st, execution_options={"populate_existing": True}):
    print(x.token_id, x.detect_collection)
    for y in x.detect_collection:
        print(y.id)

# any 如何使用
st = select(detect).where(detect.ship_id == any_([318, 319]))
st = select(detect).where(detect.ship_id.in_([318, 319]))
# not_in

# ARRAY 字段
# 包含另一个array
# contains
# 与另一个array存在交集
# overlap

# bool字段
# is_(True)
# is_not
# is_(None)

# 字符串
# ilike("bsc99%")
# istartswith(bsc)
# icontains,match
# regexp_match(...,flag)

# 数值
# st=select(ground_node).where((ground_node.id<=8) & (ground_node.id>=4))
# st=select(ground_node).where(ground_node.id.between(4,8))

# raw sql
s.execute(text("select 1"))


# 刷新对象
# select().execution_options(populate_existing=True)
# update，delete 时可选指定 'auto' 'fetch' False
# update().execution_options(synchronize_session=False)

# 创建单个
def insert_single():
    log1 = ship(token_id=3)
    s.add(log1)


# 批量创建
# s.execute(insert(User),[{"name":"aaa"}])
@atomic
def bulk_insert():
    st = insert(ship).values(
        [
            {
                ship.name: "cccc",
                ship.token_id: 3,
                "log_time": "2022-1-1",
                "log_content": "test",
            },
            {
                "name": "bbbb",
                "token_id": 3,
                "log_time": "2022-1-1",
                "log_content": "test",
            },
        ]
    )
    s.execute(st)


# https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#updating-using-the-excluded-insert-values
@atomic
def bulk_insert_on_conflict_do_update(s: session, model, data):
    if type(data) is dict:
        data = [data]
    st = insert(model).values(data)
    cols = {k: getattr(st.excluded, k) for k in data[0]}
    do_update = st.on_conflict_do_update(index_elements=["token_id"], set_=cols)
    s.execute(do_update)


@atomic
def bulk_insert_on_conflict_do_nothing(s: session, model, data):
    st = (
        insert(model)
        .values(data)
        .on_conflict_do_nothing(index_elements=["transactionHash", "logIndex"])
    )
    s.execute(st)


def update_single():
    object.someattr = ...
    s.commit()

    st = update(ship).where(ship.id == 1).values(blocknumber=123)
    s.execute(st)


def bulk_update(model, owner_table):
    # 批量更新 1.x 风格
    s.bulk_save_objects([object])
    s.query(ship).filter(ship.id == 1).update({"chain_name": "dskdkdkd"})

    # 批量更新: 子查询：https://docs.sqlalchemy.org/en/20/tutorial/data_update.html#correlated-updates
    query_owner = (
        select(owner_table.c.owner)
        .where(owner_table.c.token_id == model.token_id)
        .scalar_subquery()
    )
    st = update(model).values(owner=query_owner)

    # 批量更新-关联查询：https://docs.sqlalchemy.org/en/20/tutorial/data_update.html#update-fromowner_table
    st = (
        update(model)
        .where(owner_table.c.token_id == model.token_id)
        .values({model.owner: owner_table.c.owner})
    )

    # 批量更新：where与value绑定到字典的key
    st = (
        update(model)
        .where(model.token_id == bindparam("tid"))
        .values(owner=bindparam("real_owner"))
    )
    to_update = []
    with db.begin() as conn:
        conn.execute(st, to_update)
        conn.commit()


def update_with_case_value():
    st = (
        update(detect)
        .where(detect.round == 191)
        .values(total_earning=case((detect.round == 191, 550), else_=detect.round))
    )


def delete_single():
    s.delete(...)


def bulk_delete():
    s.query(ship).filter(ship.id == 2).delete()
    s.execute(delete(ship).where(ship.id == 3))
