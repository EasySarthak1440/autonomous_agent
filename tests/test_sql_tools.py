"""Tests for sql_manager tool."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.builtin import sql_manager


@pytest.fixture
def db_path():
    path = tempfile.mktemp(suffix=".db")
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def setup_employees(db_path):
    sql_manager(db_path, """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT,
            salary REAL
        )
    """)
    sql_manager(db_path,
        "INSERT INTO employees (id, name, department, salary) VALUES (?, ?, ?, ?)",
        [1, 'Sarthak', 'AI', 90000]
    )
    sql_manager(db_path,
        "INSERT INTO employees (id, name, department, salary) VALUES (?, ?, ?, ?)",
        [2, 'Rahul', 'HR', 50000]
    )
    sql_manager(db_path,
        "INSERT INTO employees (id, name, department, salary) VALUES (?, ?, ?, ?)",
        [3, 'Priya', 'IT', 80000]
    )
    sql_manager(db_path,
        "INSERT INTO employees (id, name, department, salary) VALUES (?, ?, ?, ?)",
        [4, 'Ankit', 'AI', 70000]
    )
    yield db_path

class TestCreateTable:
    def test_create_table(self, db_path):
        result = sql_manager(db_path, """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                age INTEGER
            )
        """)
        assert result["success"] is True
        assert result["operation"] == "create_table"

    def test_create_table_if_not_exists(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (x INTEGER)")
        result = sql_manager(db_path, "CREATE TABLE IF NOT EXISTS t (x INTEGER)")
        assert result["success"] is True

    def test_create_table_duplicate_fails(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (x INTEGER)")
        result = sql_manager(db_path, "CREATE TABLE t (x INTEGER)")
        assert result["success"] is False
        assert "already exists" in result["error"].lower()

class TestInsert:
    def test_insert_single_row(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (id INTEGER, name TEXT)")
        result = sql_manager(db_path,
            "INSERT INTO t (id, name) VALUES (?, ?)", [1, 'test'])
        assert result["success"] is True
        assert result["operation"] == "insert"
        assert result["last_insert_id"] == 1

    def test_insert_multiple_rows(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (id INTEGER, v TEXT)")
        r1 = sql_manager(db_path, "INSERT INTO t VALUES (?, ?)", [1, 'a'])
        r2 = sql_manager(db_path, "INSERT INTO t VALUES (?, ?)", [2, 'b'])
        r3 = sql_manager(db_path, "INSERT INTO t VALUES (?, ?)", [3, 'c'])
        assert r1["success"] and r2["success"] and r3["success"]

    def test_insert_nullable_column(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (id INTEGER, label TEXT)")
        result = sql_manager(db_path,
            "INSERT INTO t (id) VALUES (?)", [1])
        assert result["success"] is True

class TestSelect:
    def test_select_all(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT * FROM employees")
        assert result["success"] is True
        assert result["operation"] == "select"
        assert result["row_count"] == 4
        assert result["columns"] == ["id", "name", "department", "salary"]

    def test_select_specific_columns(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT name, salary FROM employees")
        assert result["success"] is True
        assert result["columns"] == ["name", "salary"]
        assert len(result["rows"]) == 4

    def test_select_with_where(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department = ?", ['AI'])
        assert result["success"] is True
        assert result["row_count"] == 2
        for row in result["rows"]:
            assert row["department"] == 'AI'

    def test_select_with_where_and_or(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department = ? AND salary > ?",
            ['AI', 75000])
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"][0]["name"] == 'Sarthak'

    def test_select_with_in(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department IN (?, ?)",
            ['AI', 'IT'])
        assert result["success"] is True
        assert result["row_count"] == 3

    def test_select_with_between(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE salary BETWEEN ? AND ?",
            [60000, 85000])
        assert result["success"] is True
        assert result["row_count"] == 2

    def test_select_with_like(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE name LIKE ?", ['S%'])
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"][0]["name"] == 'Sarthak'

    def test_select_order_by_asc(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT name, salary FROM employees ORDER BY salary ASC")
        salaries = [row["salary"] for row in result["rows"]]
        assert salaries == sorted(salaries)

    def test_select_order_by_desc(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT name, salary FROM employees ORDER BY salary DESC")
        salaries = [row["salary"] for row in result["rows"]]
        assert salaries == sorted(salaries, reverse=True)

    def test_select_limit(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT * FROM employees LIMIT 2")
        assert result["row_count"] == 2

    def test_select_limit_with_order(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees ORDER BY salary DESC LIMIT 1")
        assert result["row_count"] == 1
        assert result["rows"][0]["salary"] == 90000

class TestAggregate:
    def test_count(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT COUNT(*) as cnt FROM employees")
        assert result["rows"][0]["cnt"] == 4

    def test_max_salary(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT MAX(salary) as max_sal FROM employees")
        assert result["rows"][0]["max_sal"] == 90000

    def test_min_salary(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT MIN(salary) as min_sal FROM employees")
        assert result["rows"][0]["min_sal"] == 50000

    def test_avg_salary(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT AVG(salary) as avg_sal FROM employees")
        assert result["rows"][0]["avg_sal"] == 72500.0

    def test_sum_salary(self, setup_employees):
        result = sql_manager(setup_employees, "SELECT SUM(salary) as total FROM employees")
        assert result["rows"][0]["total"] == 290000

class TestGroupBy:
    def test_group_by_department(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT department, AVG(salary) as avg_sal FROM employees GROUP BY department")
        assert result["success"] is True
        departments = {row["department"] for row in result["rows"]}
        assert departments == {'AI', 'HR', 'IT'}

    def test_group_by_having(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT department, AVG(salary) as avg_sal FROM employees "
            "GROUP BY department HAVING AVG(salary) > ?", [60000])
        assert result["success"] is True
        for row in result["rows"]:
            assert row["avg_sal"] > 60000

class TestUpdate:
    def test_update_single_row(self, setup_employees):
        result = sql_manager(setup_employees,
            "UPDATE employees SET salary = ? WHERE id = ?", [95000, 1])
        assert result["success"] is True
        assert result["operation"] == "update"
        assert result["affected_rows"] == 1

        verify = sql_manager(setup_employees,
            "SELECT salary FROM employees WHERE id = 1")
        assert verify["rows"][0]["salary"] == 95000

    def test_update_multiple_rows(self, setup_employees):
        result = sql_manager(setup_employees,
            "UPDATE employees SET department = ? WHERE department = ?",
            ['Engineering', 'IT'])
        assert result["affected_rows"] == 1

    def test_update_all_rows(self, setup_employees):
        result = sql_manager(setup_employees,
            "UPDATE employees SET salary = ?", [100000])
        assert result["affected_rows"] == 4

class TestDelete:
    def test_delete_single_row(self, setup_employees):
        result = sql_manager(setup_employees,
            "DELETE FROM employees WHERE id = ?", [4])
        assert result["success"] is True
        assert result["operation"] == "delete"
        assert result["affected_rows"] == 1

    def test_delete_all_rows(self, setup_employees):
        result = sql_manager(setup_employees, "DELETE FROM employees")
        assert result["affected_rows"] == 4

        verify = sql_manager(setup_employees, "SELECT COUNT(*) as cnt FROM employees")
        assert verify["rows"][0]["cnt"] == 0

class TestJoin:
    def test_inner_join(self, db_path):
        sql_manager(db_path,
            "CREATE TABLE employees (id INTEGER, name TEXT, dept_id INTEGER)")
        sql_manager(db_path,
            "CREATE TABLE departments (dept_id INTEGER, dept_name TEXT)")

        sql_manager(db_path, "INSERT INTO employees VALUES (?, ?, ?)", [1, 'Alice', 1])
        sql_manager(db_path, "INSERT INTO employees VALUES (?, ?, ?)", [2, 'Bob', 2])
        sql_manager(db_path, "INSERT INTO departments VALUES (?, ?)", [1, 'Engineering'])
        sql_manager(db_path, "INSERT INTO departments VALUES (?, ?)", [2, 'Marketing'])

        result = sql_manager(db_path,
            "SELECT e.name, d.dept_name FROM employees e "
            "JOIN departments d ON e.dept_id = d.dept_id")
        assert result["success"] is True
        assert result["row_count"] == 2

class TestDrop:
    def test_drop_table(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (x INTEGER)")
        result = sql_manager(db_path, "DROP TABLE t")
        assert result["success"] is True
        assert result["operation"] == "drop"

    def test_drop_nonexistent_table(self, db_path):
        result = sql_manager(db_path, "DROP TABLE nonexistent")
        assert result["success"] is False

class TestTruncate:
    def test_truncate_table(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (x INTEGER)")
        sql_manager(db_path, "INSERT INTO t VALUES (?)", [1])
        result = sql_manager(db_path, "DELETE FROM t")
        assert result["success"] is True
        assert result["affected_rows"] == 1

class TestSubquery:
    def test_second_highest_salary(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT MAX(salary) as second_max FROM employees "
            "WHERE salary < (SELECT MAX(salary) FROM employees)")
        assert result["rows"][0]["second_max"] == 80000

class TestParameterizedQueries:
    def test_params_prevent_injection(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (id INTEGER, name TEXT)")
        sql_manager(db_path, "INSERT INTO t VALUES (?, ?)", [1, 'safe'])

        malicious = "1; DROP TABLE t"
        sql_manager(db_path, "SELECT * FROM t WHERE id = ?", [malicious])
        result = sql_manager(db_path, "SELECT * FROM t")
        assert result["row_count"] == 1

class TestErrorHandling:
    def test_nonexistent_db(self):
        result = sql_manager("/nonexistent/dir/test.db", "SELECT 1")
        assert result["success"] is False

    def test_invalid_sql(self, db_path):
        result = sql_manager(db_path, "SELECTX FROM nowhere")
        assert result["success"] is False

    def test_select_from_nonexistent_table(self, db_path):
        result = sql_manager(db_path, "SELECT * FROM nonexistent")
        assert result["success"] is False

    def test_empty_query(self, db_path):
        result = sql_manager(db_path, "")
        assert result["success"] is False

class TestCreateDatabase:
    def test_create_database(self):
        path = tempfile.mktemp(suffix=".db")
        try:
            result = sql_manager(path, "SELECT 1")
            assert result["success"] is True
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

class TestEdgeCases:
    def test_like_pattern_matching(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE name LIKE ?", ['%i%'])
        names = [row["name"].lower() for row in result["rows"]]
        assert all('i' in n for n in names)

    def test_and_condition(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department = ? AND salary > ?",
            ['AI', 60000])
        assert result["row_count"] == 2

    def test_or_condition(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department = ? OR department = ?",
            ['HR', 'IT'])
        assert result["row_count"] == 2

    def test_not_condition(self, setup_employees):
        result = sql_manager(setup_employees,
            "SELECT * FROM employees WHERE department != ?", ['AI'])
        assert result["row_count"] == 2

    def test_null_handling(self, db_path):
        sql_manager(db_path, "CREATE TABLE t (id INTEGER, val INTEGER)")
        sql_manager(db_path, "INSERT INTO t (id) VALUES (?)", [1])
        sql_manager(db_path, "INSERT INTO t VALUES (?, ?)", [2, 100])
        result = sql_manager(db_path, "SELECT * FROM t WHERE val IS NULL")
        assert result["row_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
