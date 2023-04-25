import time

import faker
from sqlalchemy import *
from sqlalchemy.orm import *

from dbconf import db_local as db

Base = declarative_base()
Session = sessionmaker(bind=db, expire_on_commit=False, future=True)

local = "zh_CN"
faker.Faker.seed(int(time.time()))
fake_class = faker.Faker(locale=local)
unique_fake_class = faker.Faker(locale=local).unique


class Employee(Base):
    __tablename__ = "employee"
    id = Column(BigInteger, unique=True, primary_key=True, autoincrement=True)
    name = Column(String)
    company = Column(String)
    city = Column(String)
    phone = Column(BigInteger, unique=True)


class EmployeeMore(Base):
    __tablename__ = "employee_more"
    id = Column(BigInteger, unique=True, primary_key=True, autoincrement=True)
    name = Column(String)
    company = Column(String)
    city = Column(String)
    phone = Column(BigInteger, unique=True)


Base.metadata.create_all(bind=db)


def make1000(model):
    to_add = []
    for x in range(0, 1000):
        employee = {
            "name": fake_class.name(),
            "company": fake_class.company(),
            "city": fake_class.city(),
            "phone": unique_fake_class.phone_number(),
        }
        to_add.append(employee)
    with Session() as s:
        s.execute(insert(model), to_add)
        s.commit()


def makemore(amount, model):
    for x in range(0, int(amount / 1000)):
        make1000(model)


# makemore(1e6, Employee)
# makemore(5 * 1e6, EmployeeMore)
