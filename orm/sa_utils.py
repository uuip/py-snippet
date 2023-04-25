# https://github.com/agronholm/sqlacodegen
# https://docs.sqlalchemy.org/en/14/orm/declarative_tables.html#declarative-table-configuration
# https://docs.sqlalchemy.org/en/20/core/type_basics.html
# class HullTransfer(AutoBase):
#     __abstract__ = True
#     __tablename__ = "hull_transfer"
#     __table_args__ = (
#         UniqueConstraint("transactionHash", "logIndex", name="unique_hull_transfer"),
#         # PrimaryKeyConstraint('a','b'),
#         # Index("uniqueidx",'transactionHash', 'logIndex',unique=True)
#     )
from functools import lru_cache, wraps

from sqlalchemy import *
from sqlalchemy import Table, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import *

from dbconf import db_local as db

Session = sessionmaker(bind=db, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    ...


def atomic(func=None):
    def decorator(run_func):
        @wraps(run_func)
        def wrapper(*args, **kwargs):
            with Session() as s:  # type: Session
                try:
                    rst = run_func(s, *args, **kwargs)
                except SQLAlchemyError:
                    s.rollback()
                    raise
                else:
                    s.commit()
                    return rst

        return wrapper

    return decorator(func) if func is not None else decorator


def to_dict_modelcolunm(obj):
    return {k: getattr(obj, k) for k, v in obj.__mapper__.c.items()}


def to_dict_dbcolumn(obj):
    # db column  -> model column, example: from -> from_
    db_orm_column_map = {v.name: k for k, v in obj.__mapper__.c.items()}
    return {c.name: getattr(obj, db_orm_column_map[c.name]) for c in obj.__table__.columns}


#######################################################################################
def classname_for_table(base, tablename, table):
    # todo:不同app下有相同的模型如何处理
    return tablename

    with Session() as s:
        django_apps = s.scalars(text("select distinct app_label from django_content_type")).all()
    django_apps.sort(key=lambda x: -len(x))
    for x in django_apps:
        if tablename.startswith(x + "_"):
            return tablename.replace(x + "_", "", 1)
    return tablename


def reflect_to_table(*table_names):
    # 返回的是Table
    Base.metadata.reflect(db, only=table_names)
    tables = [Base.metadata.tables[t] for t in table_names]
    if len(tables) == 1:
        return tables[0]
    return tables


# https://docs.sqlalchemy.org/en/14/orm/declarative_tables.html#using-deferredreflection
def reflect_to_table_demo():
    class Base(DeclarativeBase):
        ...

    class ship(Base):
        __table__ = Table("dungeon_ship", Base.metadata, autoload_with=db)
        detect_collection = relationship("detect", back_populates="ship")  # foreign_keys=None

        def __repr__(self):
            return f"<{self.__class__.__name__} {self.token_id}>"

    class detect(Base):
        __table__ = Table("dungeon_detect", Base.metadata, autoload_with=db)
        ship = relationship("ship", back_populates="detect_collection")

        def __repr__(self):
            return f"<{self.__class__.__name__} {self.id}>"

    Base.metadata.create_all(db, tables=[detect.__table__])


const_store = {}


@lru_cache()
def unique_constraints(*columns):
    table_name = columns[0].table.name
    if table_name not in const_store:
        const = inspect(db).get_unique_constraints(table_name=table_name)
        const_store[table_name] = const
    else:
        const = const_store[table_name]
    for item in filter(lambda x: set(x["column_names"]) == set(c.name for c in columns), const):
        return item["name"]
