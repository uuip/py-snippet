import os
import random
import sys

import django

sys.path.append("/Users/sharp/Desktop/project/DataTransferAPI/dt_project")
os.environ["DJANGO_SETTINGS_MODULE"] = "dt_project.settings"
django.setup()

import arrow
import faker
from model_bakery import baker
from model_bakery.recipe import Recipe, foreign_key
from fake_data.django_factoryboy import make
from django.db.models import Max

from departments.models import Role, UserRole
from consts.common import RoleCode
from dt.models.ops import Instance, WarningLog
from dt.models.org import DtUserOrgMap, Org
from dt.models.task import DtProject, Task, TaskTable
from dt.models.user import DtUser
from dt.models.statistics import (
    DayFailInstance,
    DayInstanceStatusStatistics,
    DayInstanceType,
    DayTaskStatus,
    HourInstanceStatus,
    TaskFailedInstance,
)
from dt.models.source import SourceType


def make_org_admin():
    user = make(DtUser, phone="15321227216")
    org = make(Org, name=f"Org created by user:{user.id}", dt_user=user)
    role = make(Role, name=RoleCode.ORG_ADMIN.value, organization_id=org.id)
    make(DtUserOrgMap, dt_user=user, org=org)
    make(UserRole, user_id=user.id, role=role)
    return user, org


def makeWarningLog(user, org):
    # foreign_key若指定one_to_one=True每个关联都是新的实例
    project = Recipe(DtProject, org=org)
    task = Recipe(Task, org=org, dt_project=foreign_key(project))
    task_table = Recipe(TaskTable, task=foreign_key(task), join_dt_users=[user.id])
    instance = Recipe(Instance, task_table=foreign_key(task_table), dt_project=foreign_key(project))
    Recipe(WarningLog, org=org, instance=foreign_key(instance)).make(
        4, make_m2m=True, _bulk_create=True
    )


def makeWarningLog2(user, org):
    instance1 = make(Instance)
    instance2 = make(Instance)
    make(
        WarningLog,
        4,
        org=org,
        instance=instance1,
        instance__task_table__responsible_user=user,
    )
    make(
        WarningLog,
        4,
        org=org,
        instance=instance2,
        instance__task_table__responsible_user=user,
    )
    make(WarningLog, size=10)


def operation():
    return (
        DayFailInstance,
        DayInstanceStatusStatistics,
        DayInstanceType,
        DayTaskStatus,
        HourInstanceStatus,
        TaskFailedInstance,
        WarningLog,
        Instance,
    )


def basic():
    return TaskTable, Task, DtProject, UserRole, DtUserOrgMap, Role, Org, DtUser


def clean():
    for x in operation():
        x.objects.all().delete()
    SourceType.objects.filter(id__gt=2).all().delete()


def make_op_summary():
    fake = faker.Faker(locale="zh_CN")
    now = arrow.now()
    try:
        user = DtUser.objects.get(phone="15321227216")
        user = DtUser.objects.get(username="lulu")
    except:
        user = baker.make(DtUser, phone="15321227216")
    # user.set_password('aabbcc')
    # user.save()
    try:
        org = Org.objects.get(id=1)
        org = Org.objects.get(uid="NbuZrTWyCXUUaGFGSQPAGL")
    except:
        org = baker.make(Org)
        role = baker.make(Role, name=RoleCode.ORG_ADMIN.value, organization_id=org.id)
        baker.make(DtUserOrgMap, dt_user=user, org=org)
        baker.make(UserRole, user_id=user.id, role=role)
    # project = make(DtProject, org=org, dt_user=user)
    # task = make(Task, dt_project=project, dt_user=user, last_update_dt_user=user)
    # task_table = make(TaskTable, task=task, responsible_user=user)
    project = DtProject.objects.filter(org=org, dt_user=user).first()
    task = Task.objects.filter(dt_project=project, dt_user=user, last_update_dt_user=user).first()
    task_table = TaskTable.objects.filter(task=task, responsible_user=user).first()

    # baker.make(
    #     DayInstanceStatusStatistics,
    #     org=org,
    #     date=now.date(),
    #     total=15,
    #     pending=1,
    #     running=2,
    #     fail=3,
    #     success=4,
    #     forced_termination=5,
    # )
    #
    # baker.make(
    #     DayFailInstance,
    #     org=org,
    #     date=now.date(),
    #     timeout=1,
    #     invalid_connectivity=2,
    #     from_table_change=3,
    #     from_field_change=4,
    #     to_table_change=5,
    #     to_field_change=6,
    #     other=7,
    # )
    start_date = HourInstanceStatus.objects.filter(org=org).aggregate(max=Max("date"))["max"]
    hour = HourInstanceStatus.objects.filter(org=org, date=start_date).aggregate(max=Max("hour"))[
        "max"
    ]
    start_date = arrow.Arrow(start_date.year, start_date.month, start_date.day, hour=hour).shift(
        hours=1
    )
    for x in arrow.Arrow.range("hours", start_date or now.shift(days=-15).floor("day"), now):
        baker.make(
            HourInstanceStatus, org=org, date=x.datetime, hour=x.hour, success=fake.pyint(0, 50)
        )

    start_date = now
    # for x in arrow.Arrow.range("days", start_date or now.shift(days=-100), now):
    #     baker.make(DayTaskStatus, org=org, date=x.date(), online=fake.pyint(0, 50))
    #     baker.make(DayInstanceType, org=org, date=x.date(), common=fake.pyint(0, 50))

    for x in arrow.Arrow.range("days", start_date or now.shift(days=-40).floor("day"), now):
        duration = fake.pyint()
        baker.make(
            Instance,
            3,
            dt_project=project,
            scheduled_start=x.date(),
            start_at=x.shift(minutes=duration).datetime,
            waiting_duration=duration,
        )

    for x in arrow.Arrow.range("days", start_date or now.shift(days=-40).floor("day"), now):
        total = fake.pyint()
        failed = random.randint(0, total)
        baker.make(
            TaskFailedInstance,
            3,
            org=org,
            dt_project=project,
            task=task_table,
            date=x.date(),
            total=total,
            failed=failed,
        )


if __name__ == "__main__":
    user, org = make_org_admin()
    makeWarningLog2(user, org)
