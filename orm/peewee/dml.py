import logging

from model.pw import reflect
from peewee import *
from peewee import Expression

logger = logging.getLogger("peewee")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

detect, ship = reflect("dungeon_detect", "dungeon_ship")
logcache = reflect("ground_logcache")
network = reflect("geoip_network")
ship.__repr__ = lambda self: f"<{self.__class__.__name__} {self.token_id}>"
detect.__repr__ = lambda self: f"<{self.__class__.__name__} {self.round} {self.ship_id}>"

ship.get(ship.token_id == 5798)
ship.filter(ship.token_id == 5798).first()
ship.filter(token_id=5798).first()
ship.select(ship, ship.name.alias("new_name")).limit(3).first()
network.select().where(SQL("network >>= %s", ["1.1.4.1"])).first()
network.select().where(Expression(network.network, ">>=", "1.1.4.1")).first()

ship.select(fn.sum(ship.total_reward)).scalar()
ship.select(
    ship, (ship.token_id * 10).alias("new_tokenid"), SQL("token_id*10").alias("abc")
).first()

# 指定字段
# columns(network.network)

# 关联查询
ship.select().join(detect, on=(ship.token_id == detect.ship_id)).first()
# n+1, select() 触发n+1, select 指定字段或全部字段
qs = detect.select(detect, ship).join(ship).where(ship.token_id < 1000)
for x in qs:
    print(x.ship.name)
    break
detect.select(detect, ship).filter(ship__token_id__lte=1000).count()
detect.select(
    detect.start_time,
    fn.to_char(
        Expression(fn.to_timestamp(detect.start_time), "AT TIME ZONE", "Asia/Shanghai"),
        "YYYY-MM-DD HH24:MI:SS",
    ),
).first()

# 关联字段定义backref
# ship.select(detect, ship).filter(detect_set__chain=1).order_by(-ship.token_id).distinct().count()


# raw sql
# ship.raw("")


# & | ~

# order_by(detect.id.asc())
# order_by(-Tweet.created_date)
# SQL('rrr desc')

# detect.select(fn.DISTINCT(detect.round)).filter(...)

# 创建单个
def create_test():
    data = {
        "chain_name": "bbbb",
        "node_id": 3,
        "log_time": "2022-1-1",
        "log_content": "test",
    }
    logcache.create(**data)


# logcache.insert(data).execute()

# 批量创建
# with db.atomic():
#     logcache.bulk_create([logcache(**data)], batch_size=100)
# with db.atomic():
#     logcache.insert_many([data] * 10).execute()

# 更新单个
# save

# 批量更新
# logcache.update(log_content="llllllll").where().execute()
# logcache.bulk_update([l,], fields=["log_content",logcache.node_id])

# 删除单个
# 实例的delete是删除整个表！！！
# logcache.get(40).delete_instance()
# logcache.delete_instance(l)

# 删除
# logcache.delete().where().execute()
print(333)
