import pytest
from app.backend.llm.sql_guard import validate_sql


def test_reject_dml():
    for stmt in [
        "DELETE FROM licencias",
        "UPDATE licencias SET x=1",
        "INSERT INTO licencias VALUES (1)",
        "DROP TABLE licencias",
        "ALTER TABLE licencias ADD COLUMN x INT",
    ]:
        with pytest.raises(ValueError):
            validate_sql(stmt)


def test_accept_select():
    assert validate_sql("SELECT COUNT(*) FROM licencias WHERE MUNICIPIO='MEDELLIN'")
