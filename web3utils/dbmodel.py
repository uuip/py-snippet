from functools import wraps

from sqlalchemy import *
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import *

url = URL.create(
    **dict(
        drivername="postgresql+psycopg2",
        host="127.0.0.1",
        port="5432",
        database="postgres",
        username="postgres",
        password="postgres",
    )
)

db = create_engine(url, echo=False)
Session = sessionmaker(bind=db, expire_on_commit=False)
Base = declarative_base()


class EventBase(Base):
    __abstract__ = True

    id = Column(BigInteger, autoincrement=True, primary_key=True)
    transactionHash = Column(VARCHAR(66))
    logIndex = Column(Integer)

    event = Column(Text, nullable=False)
    transactionIndex = Column(Integer)
    blockNumber = Column(Integer)

    from_ = Column(VARCHAR(42), name="from")
    to = Column(VARCHAR(42))
    token_id = Column(Integer, index=True)


class HullTransfer(EventBase):
    __tablename__ = "hull_transfer"
    __table_args__ = (
        UniqueConstraint("transactionHash", "logIndex", name="unique_hull_transfer"),
        # PrimaryKeyConstraint('a','b'),
        # Index("uniqueidx",'transactionHash', 'logIndex',unique=True)
    )


class ShipTransfer(EventBase):
    __tablename__ = "ship_transfer"
    __table_args__ = (UniqueConstraint("transactionHash", "logIndex", name="unique_ship_transfer"),)


class ScanConfig(Base):
    __tablename__ = "scanconfig"
    contract = Column(VARCHAR(10), nullable=False, primary_key=True)
    blocknumber = Column(Integer)


Base.metadata.create_all(bind=db)


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


def reflect(*table_names):
    def classname_for_table(base, tablename, table):
        return tablename.split("_")[-1]

    autobase = automap_base()
    autobase.prepare(
        autoload_with=db,
        classname_for_table=classname_for_table,
    )
    models = [getattr(autobase.classes, classname_for_table(None, t, None)) for t in table_names]
    if len(models) == 1:
        return models[0]
    return models
