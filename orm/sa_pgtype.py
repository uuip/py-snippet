import enum
from typing import Optional

from sqlalchemy import *
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.orm import *
from sqlalchemy.orm.attributes import flag_modified

from dbconf import db_local as db

# https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#range-and-multirange-types
# json字段
# https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#json-types
# data_table.c.data['some key'].astext.cast(Integer) == 5


session = sessionmaker(bind=db, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


class Status(enum.Enum):
    open = 1
    close = 0


class DemoPg(Base):
    __tablename__ = "demo"
    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    books = mapped_column(ARRAY(item_type=Integer))
    data = mapped_column(JSON)
    datab = mapped_column(JSONB)
    catlog = mapped_column(
        Enum(Status, name="product_catlog", values_callable=lambda obj: [str(x.value) for x in obj])
    )
    nickname: Mapped[Optional[str]]

    # @hybrid_property
    # def fullname(self):
    #     return self.firstname + " " + self.lastname


Base.metadata.drop_all(bind=db, tables=[DemoPg.__table__])
Base.metadata.create_all(bind=db)
obj = DemoPg(
    books=[1],
    data={"max": 3},
    datab={"max": 4, "min": [{"aa": 4}], "desc": "测试", "is_deleted": False},
    catlog=Status.open,
)

s = session()
s.add(obj)
s.commit()
obj = s.scalars(select(DemoPg).where(DemoPg.catlog == Status.open)).first()
print(obj.id, obj.catlog.name)

# 查询存在key
st = select(DemoPg).where(DemoPg.datab.has_key("max"))

# # 查询value为某值JSONB.Comparator: as_boolean() as_float
st = select(DemoPg).where(DemoPg.datab["max"].as_integer() == 4)
st = select(DemoPg).where(DemoPg.datab["desc"].as_string() == "测试")
st = select(DemoPg).where(DemoPg.datab["is_deleted"].as_boolean().is_(False))

# 设置或添加key
a = s.scalars(
    update(DemoPg)
    .values(datab=func.jsonb_set(DemoPg.datab, ["ccc"], func.to_jsonb(50)))
    .returning(DemoPg)
)
print(a.first().datab)

# 设置或添加key
a = s.scalars(
    update(DemoPg)
    .values(datab=func.jsonb_set(DemoPg.datab, ["min", "1"], func.to_jsonb(50), True))
    .returning(DemoPg)
)
print(a.first().datab)

# 删除key
a = s.scalars(
    update(DemoPg).values(datab=DemoPg.datab.op("#-")(array(["min", "0"]))).returning(DemoPg)
)
print(a.first().datab, "endddddddddd")

# 修改实例的属性
obj.datab["max"] = 1000
flag_modified(obj, "datab")

s.commit()


# Range字段需要构造Range
# where(DemoPg.r_int.contains(Range(10, 50, bounds="[]")))
# for x in s.scalars(
#     select(DemoPg).where(DemoPg.r_int.not_extend_left_of(Range(0, 100, bounds="()")))
# ):
#     print(obj.id)
