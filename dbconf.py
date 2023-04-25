from sqlalchemy import URL, create_engine

local = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "prac",
    "username": "postgres",
    "password": "postgres",
}
dev203 = {
    "host": "101.251.211.203",
    "port": "5432",
    "database": "triathon_website_backend",
    "username": "postgres",
    "password": "abcdos123",
}

dt = {
    "host": "106.3.151.9",
    "port": 64253,
    "username": "zhixin_user",
    "password": "8sjehj37dkwo92",
    "database": "scf_test_v1_3_0",
}
# create_engine('sqlite:///foo.db')
url = URL.create(drivername="postgresql+psycopg2", **local)
db_local = create_engine(url, echo=True)

url = URL.create(drivername="postgresql+psycopg2", **dev203)
db_203 = create_engine(url, echo=True)

url = URL.create(drivername="postgresql+psycopg2", **dt)
db_dt = create_engine(url, echo=False)
