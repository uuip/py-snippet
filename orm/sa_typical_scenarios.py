from sqlalchemy import *
from sqlalchemy.orm import aliased

from sa_dml import detect
from sa_utils import atomic, db

st = select(
    detect.start_time,
    func.to_char(
        func.to_timestamp(detect.start_time).op("AT TIME ZONE")("Asia/Shanghai"),
        "YYYY-MM-DD HH24:MI:SS",
    ),
)
st = select(
    detect.start_time,
    func.to_char(
        func.timezone("Asia/Shanghai", func.to_timestamp(detect.start_time)),
        "YYYY-MM-DD HH24:MI:SS +8",
    ),
)


@atomic
def element_not_in_another_table_except(s, model1, model2):
    st = select(model1.token_id).except_(select(model2.token_id))
    return s.scalars(st).all()


def element_not_in_another_table_subq(s, model1, model2):
    subq = select(model1.token_id).scalar_subquery()
    st = select(model2.token_id).where(~model2.token_id.in_(subq)).distinct(model2.token_id)


def element_not_in_another_table_leftjoin(model1, model2):
    qs = (
        select(model1)
        .join(model2, model1.id == model2.logmodel_id, isouter=True)
        .where(model2.id.is_null())
    )


def get_first_row_every_group_window_func(model):
    # 获取分组第一条：窗口函数
    t = aliased(model)
    win = select(
        t.token_id,
        t.from_,
        t.to,
        func.row_number()
        .over(partition_by=t.token_id, order_by=[desc(t.blockNumber), desc(t.logIndex)])
        .label("new_index"),
    ).subquery()
    owner_case = case(
        (win.c.to.in_([1, 2]) & win.c.from_.not_in([3, 4]), win.c.from_),
        else_=win.c.to,
    ).label("owner")
    owner_table = select(win.c.token_id, owner_case).where(win.c.new_index == 1).subquery()


def get_first_row_every_group_distinct_on(model):
    # 获取分组第一条：distinct on
    t = aliased(model)
    owner_case = case(
        (t.to.in_([1, 2]) & t.from_.not_in([3, 4]), t.from_),
        else_=t.to,
    ).label("owner")
    owner_table = (
        select(t.token_id, owner_case)
        .distinct(t.token_id)
        .order_by(t.token_id, desc(t.blockNumber), desc(t.logIndex))
        .subquery()
    )


def copy_table(model, Base):
    attrs = {"__tablename__": f"{model.__table__.name}copy"}

    db_orm_keymap = {v.name: k for k, v in model.__mapper__.c.items()}
    for col in model.__table__.columns:
        args = [col.name, col.type]
        if col.foreign_keys:
            args.extend(
                ForeignKey(x._colspec, ondelete=x.ondelete, onupdate=x.onupdate)
                for x in col.foreign_keys
            )
        kwargs = {
            "primary_key": col.primary_key,
            "unique": col.unique,
            "nullable": col.nullable,
            "default": col.default,
            "server_default": col.server_default,
            "onupdate": col.onupdate,
            "index": col.index,
        }
        attrs[db_orm_keymap[col.name]] = Column(*args, **kwargs)

    constraints = []
    for x in model.__table__.constraints:
        if isinstance(x, UniqueConstraint):
            constraints.append(UniqueConstraint(*[c.name for c in x.columns]))

    attrs["__table_args__"] = tuple(constraints)
    Model = type(f"{model.name}copy", (Base,), attrs)
    Base.metadata.create_all(bind=db, tables=[Model.__table__])
