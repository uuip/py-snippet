from sqlalchemy import *
from sqlalchemy.orm import *

from dbconf import db_local as db
from fake_data.sqlalchemy_factoryboy import make


class Base(DeclarativeBase):
    pass


class MiddleTable(Base):
    __tablename__ = "association_table"
    left_id = mapped_column(ForeignKey("user.id"), primary_key=True)
    right_id = mapped_column(ForeignKey("project.id"), primary_key=True)


class User(Base):
    __tablename__ = "user"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    username = mapped_column(String)

    emails = relationship("Email", back_populates="user")

    wife = relationship("Wife", uselist=False, back_populates="user")

    country_id = mapped_column(ForeignKey("country.id"))
    country = relationship("Country", back_populates="users")

    projects = relationship("Project", secondary=MiddleTable.__table__, back_populates="join_users")

    allsendmsg = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    allreceivedmsg = relationship(
        "Message", foreign_keys="Message.receiver_id", back_populates="receiver"
    )


# onetomany
class Email(Base):
    __tablename__ = "email"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    address = mapped_column(String)
    user_id = mapped_column(ForeignKey(User.id))
    user = relationship(User, back_populates="emails")


# onetoone
class Wife(Base):
    __tablename__ = "wife"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    name = mapped_column(String)
    user_id = mapped_column(ForeignKey(User.id), unique=True)
    user = relationship(User, back_populates="wife")


# manytoone
class Country(Base):
    __tablename__ = "country"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    name = mapped_column(String)
    users = relationship(User, back_populates="country")


# manytomany
class Project(Base):
    __tablename__ = "project"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    name = mapped_column(String)
    join_users = relationship(User, secondary=MiddleTable.__table__, back_populates="projects")


# 多列引用一个表的同一字段
class Message(Base):
    __tablename__ = "message"

    id = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    msg = mapped_column(String)
    sender_id = mapped_column(ForeignKey(User.id))
    receiver_id = mapped_column(ForeignKey(User.id))
    sender = relationship(User, foreign_keys=sender_id, back_populates="allsendmsg")
    receiver = relationship(User, foreign_keys=receiver_id, back_populates="allreceivedmsg")


def init():
    Base.metadata.drop_all(
        bind=db,
        tables=[
            MiddleTable.__table__,
            Email.__table__,
            Wife.__table__,
            Project.__table__,
            Message.__table__,
            User.__table__,
            Country.__table__,
        ],
    )
    Base.metadata.create_all(bind=db, tables=[Country.__table__])
    Base.metadata.create_all(bind=db)
    u1 = make(User)
    u2 = make(User)
    make(Message, 5, sender=u1, receiver=u2)
    make(Message, 7, sender=u2, receiver=u1)


init()
