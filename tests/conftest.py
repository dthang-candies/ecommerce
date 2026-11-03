"""Tests run against a real MySQL database `unicart_test`, rebuilt from sql/schema.sql for every test."""
import os
import re
from pathlib import Path

import pymysql
import pytest
from fastapi.testclient import TestClient

from unicart.domain.extended import security
from unicart.persistence.database import Database
from unicart.presentation.app import create_app

HOST = os.getenv("TEST_DB_HOST", "localhost")
USER = os.getenv("TEST_DB_USER", "root")
PASSWORD = os.getenv("TEST_DB_PASSWORD", "")
TEST_DB = "unicart_test"
URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:3306/{TEST_DB}?charset=utf8mb4"
SCHEMA = (Path(__file__).resolve().parent.parent / "sql" / "schema.sql").read_text(encoding="utf-8")
SAMPLE_PASSWORD = "Abc@12345"
_HASH = security.hash_password(SAMPLE_PASSWORD, iterations=1000)        # cheap hash keeps the suite fast

ADMIN, SERVICE, WAREHOUSE = "admin@abc.vn", "service@abc.vn", "warehouse@abc.vn"
AN, BINH = "an@gmail.com", "binh@gmail.com"
SALES, MARKETING, MANAGER = "sales@abc.vn", "marketing@abc.vn", "manager@abc.vn"


def _rebuild_database() -> None:
    sql = re.sub(r"\bunicart\b", TEST_DB, SCHEMA)
    sql = re.sub(r"--[^\n]*", "", sql)                 # drop comments (the script has none inside strings)
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, charset="utf8mb4", autocommit=True)
    with conn.cursor() as cur:
        for stmt in sql.split(";"):
            if stmt.strip():
                cur.execute(stmt)
        cur.execute(f"USE {TEST_DB}")
        cur.execute("UPDATE account SET password_hash=%s", (_HASH,))
        for acc_id, email, role in ((6, SALES, 4), (7, MARKETING, 6), (8, MANAGER, 7)):
            cur.execute("INSERT INTO account(id,email,password_hash,role_id) VALUES (%s,%s,%s,%s)",
                        (acc_id, email, _HASH, role))
    conn.close()


@pytest.fixture()
def db():
    _rebuild_database()
    return Database(URL)


@pytest.fixture()
def client(db):
    with TestClient(create_app(db)) as c:
        yield c


@pytest.fixture()
def session(db):
    with db.new_session() as s:
        yield s


def login(client: TestClient, email: str, password: str = SAMPLE_PASSWORD) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def as_(client):
    """as_('an@gmail.com') -> Authorization header of that (cached) login."""
    cache: dict[str, dict] = {}

    def get(email: str) -> dict:
        if email not in cache:
            cache[email] = login(client, email)
        return cache[email]
    return get
