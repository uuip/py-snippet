import datetime
import time
from typing import Type, TypeVar

import factory
import factory.fuzzy
import faker
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models

local = "zh_CN"
faker.Faker.seed(int(time.time()))
fake_class = faker.Faker(locale=local)
unique_fake_class = faker.Faker(locale=local).unique

model_factorys = {}
M = TypeVar("M", bound=models.Model)
F = Type[factory.django.DjangoModelFactory]


def make(model: Type[M], size: int = 1, **kwargs) -> M:
    if size == 1:
        return get_factory(model).create(**kwargs)
    return get_factory(model).create_batch(size, **kwargs)


def fake(dtype, *args, **kwargs):
    return factory.LazyFunction(lambda: getattr(fake_class, dtype)(*args, **kwargs))


def unique_fake(dtype, *args, **kwargs):
    return factory.LazyFunction(lambda: getattr(unique_fake_class, dtype)(*args, **kwargs))


class GetOrCreateDjangoFactory(factory.django.DjangoModelFactory):
    @classmethod
    def _get_or_create(cls, model: Type[M], *args, **kwargs) -> M:
        manager = cls._get_manager(model).order_by("-pk")
        unique_key = set(
            field.name for field in model._meta.fields if (field.unique or field.primary_key)
        )
        for x in model._meta.unique_together:
            if set(kwargs) & set(x) == set(x):
                qs_kwargs = {k: v for k, v in kwargs.items() if k in set(x)}
                if obj := manager.filter(**qs_kwargs).first():
                    return obj
        for k, v in kwargs.items():
            if k in unique_key and v is not None:
                if obj := manager.filter(**{k: v}).first():
                    return obj
        if obj := manager.filter(**kwargs).first():
            return obj
        return manager.create(**kwargs)


def get_factory(model: Type[M]) -> F:
    if f := model_factorys.get(model):
        return f
    f = make_factory(model)
    model_factorys[model] = f
    return f


def make_factory(model_class: Type[M], **kwargs) -> F:
    factory_name = "%sFactory" % model_class.__name__
    base_class = GetOrCreateDjangoFactory

    class Meta:
        model = model_class
        django_get_or_create = True

    attrs = {field.name: get_auto_field(field, model_class) for field in model_class._meta.fields}
    attrs["Meta"] = Meta
    attrs.update(specially_designated(model_class))
    attrs.update(kwargs)

    factory_class = type(factory.Factory).__new__(
        type(factory.Factory), factory_name, (base_class,), attrs
    )
    factory_class.__name__ = "%sFactory" % model_class.__name__
    factory_class.__doc__ = "Auto-generated factory for class %s" % model_class
    return factory_class


def get_auto_field(field: models.Field, model: models.Model):
    field_type = type(field)
    if field.blank and field.null:
        return
    if field_type is models.BigAutoField:
        return
    if field.choices:
        return factory.fuzzy.FuzzyChoice(field.choices, getter=lambda c: c[0])

    if field_type is models.EmailField:
        return unique_fake("email")
    if field_type is models.URLField:
        return fake("url")
    if isinstance(field, models.IntegerField):
        if field.unique:
            return unique_fake("pyint")
        return factory.fuzzy.FuzzyInteger(10)
    if field_type is models.DecimalField:
        return factory.fuzzy.FuzzyDecimal(10)
    if field_type is models.FloatField:
        return factory.fuzzy.FuzzyFloat(0.2)
    if field_type is models.BooleanField:
        return fake("pybool")
    if field_type is models.JSONField:
        return {}
    if field_type is ArrayField:
        if choices := field.base_field.choices:
            return [factory.fuzzy.FuzzyChoice(choices, getter=lambda c: c[0])]
        return []
    if field_type in [models.CharField, models.TextField]:
        if "email" == field.name:
            return unique_fake("email")
        if "username" == field.name:
            return unique_fake("user_name")
        if "phone" == field.name:
            return unique_fake("phone_number")
        if "first_name" == field.name:
            return fake("first_name")
        if "last_name" == field.name:
            return fake("last_name")
        if "password" == field.name:
            return fake("password")
        if "nick_name" == field.name:
            return fake("name")
        if "号" in field.name:
            return unique_fake("pyint")
        if "desc" in field.name:
            return fake("sentence")
        # factory.fuzzy.FuzzyText(length=12
        return factory.LazyFunction(lambda: faker.Faker(local).text(max_nb_chars=10)[:-1])
    if isinstance(field, models.ForeignKey):  # OneToOneField
        if model == field.related_model:
            if field.null:
                # https://factoryboy.readthedocs.io/en/stable/reference.html?highlight=path#circular-imports
                return
            else:
                raise ValueError("关联自己")
        return factory.SubFactory(get_factory(field.related_model))
    if field_type is models.DateTimeField:
        if field.auto_now_add or field.auto_now:
            return
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(hours=24)
        tomorrow = today + datetime.timedelta(hours=24)
        if field.name == "end_at":
            return fake("date_time_between_dates", datetime_start=today, datetime_end=tomorrow)
        return fake("date_time_between_dates", datetime_start=yesterday)
    if field_type is models.DateField:
        if field.auto_now_add or field.auto_now:
            return
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(hours=24)
        tomorrow = today + datetime.timedelta(hours=24)
        if field.name == "end_at":
            return fake("date_between_dates", datetime_start=today, date_end=tomorrow)
        return fake("date_between_dates", date_start=yesterday)
    if field_type is GenericForeignKey:
        # https://factoryboy.readthedocs.io/en/stable/recipes.html#django-models-with-genericforeignkeys
        raise ValueError(str(field_type))
    if field.default is not models.NOT_PROVIDED:
        default = field.default
        if callable(default):
            return factory.LazyFunction(default)
        return default


def specially_designated(model):
    fields_map = {}
    if model.__name__ == "Org":
        fields_map["name"] = fake("company")
    elif model.__name__ == "Task":
        fields_map["org"] = factory.SelfAttribute("dt_project.org")
    elif model.__name__ == "Instance":
        fields_map["dt_project"] = factory.SelfAttribute("task_table.task.dt_project")
    elif model.__name__ == "WarningLog":
        fields_map["org"] = factory.SelfAttribute("instance.dt_project.org")
        fields_map["project_name"] = factory.SelfAttribute("instance.dt_project.name")
        fields_map["desc"] = factory.SelfAttribute("instance.dt_project.desc")
    elif model.__name__ == "DtProject":
        fields_map["controls"] = manytomany(model._meta.get_field("controls"))
    return fields_map


def manytomany(field: models.Field):
    @factory.post_generation
    def fill(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            qs = extracted
        else:
            qs = field.related_model.objects.all()[:2]
        getattr(self, field.name).add(*qs)

    return fill


def genericforeignkey():
    object_id = factory.SelfAttribute("content_object.id")
    content_type = factory.LazyAttribute(
        lambda o: ContentType.objects.get_for_model(o.content_object)
    )
    content_object = factory.SubFactory(...)
