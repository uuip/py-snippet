import datetime

import peewee as pw
from peewee import *
from playhouse.reflection import generate_models

# sqlite_db = SqliteDatabase('/path/to/app.db')
db = PostgresqlDatabase(
    host="101.251.211.203",
    port="5432",
    database="triathon_website_backend",
    user="postgres",
    password="abcdos123",
    autorollback=True,
    # Automatically rollback queries that fail when not in an explicit transaction.
)
atomic = db.atomic
django_apps = db.execute_sql("select distinct app_label from django_content_type")
django_apps = sorted([x[0] for x in django_apps], key=lambda x: -len(x))
# 生成模型代码
# http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#pwiz-a-model-generator


class OnChainLog(pw.Model):
    """记录已上链的操作日志"""

    logmodel_id = pw.BigIntegerField()
    request_id = pw.TextField()
    request_time = pw.DateTimeField(default=datetime.datetime.now)
    transaction = pw.TextField()

    class Meta:
        table_name = "logmodel_onchain"
        database = db


def reflect(*table_names):
    models = generate_models(db, table_names=table_names)
    rst = [models[t] for t in table_names]
    # list(map(rebuild_relation, rst))
    # list(map(change_model_name, rst))
    if len(rst) == 1:
        return rst[0]
    return rst


def rebuild_relation(child):
    #  默认反向名 playhouse.reflection.Introspector.generate_models 修改
    # params['backref']
    for x in django_apps:
        if child.__name__.startswith(x + "_"):
            child_graceful = child.__name__.replace(x + "_", "", 1)
            break
    ref_info = [
        {
            "fk_field": fk_field.name,
            "father": father,
            "to_field": fk_field.rel_field.name,
            "backref": fk_field.backref,
        }
        for fk_field, father in child._meta.refs.items()
    ]
    for x in ref_info:
        rel = ForeignKeyField(x["father"], field=x["to_field"], backref=f"{child_graceful}_set")
        child._meta.add_field(x["fk_field"], rel)
        delattr(x["father"], x["backref"])


def change_model_name(model):
    # todo:不同app下有相同的模型如何处理
    for x in django_apps:
        if model.__name__.startswith(x + "_"):
            graceful = model.__name__.replace(x + "_", "", 1)
            model._meta.model.__name__ = graceful
            model._meta.name = graceful


# class demo(Model):
#     class Meta:
#         database = db
#         table_name = "dungeon_ship"
#         constraints = [SQL("UNIQUE(caddress,ship,round)")]
#
#     def __repr__(self):
#         return f'<{self.__class__.__name__} {self.token_id}>'
