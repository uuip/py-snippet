from typing import Type, TypeVar

from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import get_openapi
from pydantic import create_model, BaseModel
from pydantic.schema import schema
from sqlalchemy.orm import Relationship, DeclarativeBase

from response.generic import R

Model = TypeVar("Model", bound=BaseModel)


def sqlalchemy2pydantic(model: Type[DeclarativeBase], base: Type[BaseModel]) -> Type[BaseModel]:
    attrs = {}
    db_orm_column_map = {v.name: k for k, v in model.__mapper__.c.items()}
    fk_mapped_columns = {}  # orm中已经被外键映射过的列{"xx_id":"xx"}
    for k, v in model.__mapper__.attrs.items():
        if isinstance(v, Relationship):
            if v.direction.name == "MANYTOONE":
                fk_mapped_columns[k] = db_orm_column_map[list(v.local_columns)[0].name]
            elif v.direction.name == "ONETOMANY":
                # no need
                continue
            else:  # MANYTOMANY
                print("handle MANYTOMANY by yourself")
                continue
    schema_keys = set(db_orm_column_map.values()) - set(fk_mapped_columns.values())
    for k, v in model.__mapper__.c.items():
        if k in schema_keys:
            attrs[k] = (v.type.python_type, None)
    print("添加外键", set(fk_mapped_columns.keys()))
    kwargs = {"__base__": base}
    pydantic_model = create_model(f"{model.__name__}Schema", **kwargs, **attrs)
    return pydantic_model


def custom_openapi(app):
    def wrap():
        if not app.openapi_schema:
            app.openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=app.description,
                terms_of_service=app.terms_of_service,
                contact=app.contact,
                license_info=app.license_info,
                routes=app.routes,
                tags=app.openapi_tags,
                servers=app.servers,
            )
            for _, method_item in app.openapi_schema.get("paths").items():
                for _, param in method_item.items():
                    responses = param.get("responses")
                    # remove 422 response, also can remove other status code
                    if "422" in responses:
                        del responses["422"]
                    responses["400"] = {
                        "description": "Request Error",
                        "content": {
                            "application/json": {"schema": {"$ref": f"{REF_PREFIX}ErrorResponse"}}
                        },
                    }
            error_response_schema = schema(
                (R,), ref_prefix=REF_PREFIX, ref_template=f"{REF_PREFIX}{{model}}"
            )
            error_response_schema = {
                "ErrorResponse": list(error_response_schema["definitions"].values())[0]
            }

            properties = error_response_schema["ErrorResponse"]["properties"]
            properties["code"]["default"] = 400
            properties["msg"]["default"] = "request failed"

            openapi_schemas = app.openapi_schema["components"]["schemas"]
            openapi_schemas.update(error_response_schema)
            openapi_schemas.pop("ValidationError")
            openapi_schemas.pop("HTTPValidationError")
        return app.openapi_schema

    return wrap
