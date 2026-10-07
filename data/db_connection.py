import os
from typing import Tuple, Optional, Any, Dict
from .db_config import get_db_config

# Try importing mysql.connector or pymysql
_DRIVER = None
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    _DRIVER = "mysql.connector"
except ImportError:
    try:
        import pymysql
        import pymysql.cursors
        from pymysql import Error as MySQLError
        _DRIVER = "pymysql"
    except ImportError:
        _DRIVER = None


def get_driver_name() -> Optional[str]:
    """Returns the installed MySQL driver name or None."""
    return _DRIVER


def get_connection(use_database: bool = True):
    """
    Creates and returns a connection to MySQL.
    If use_database is False, connects to MySQL server without selecting a specific database
    (useful for creating the database schema).
    """
    if _DRIVER is None:
        raise RuntimeError("No MySQL driver installed. Please install mysql-connector-python or pymysql.")

    cfg = get_db_config()
    connect_params = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
    }
    if use_database and cfg.get("database"):
        connect_params["database"] = cfg["database"]

    if _DRIVER == "mysql.connector":
        return mysql.connector.connect(**connect_params)
    elif _DRIVER == "pymysql":
        connect_params["charset"] = cfg.get("charset", "utf8mb4")
        connect_params["cursorclass"] = pymysql.cursors.DictCursor
        return pymysql.connect(**connect_params)
    else:
        raise RuntimeError("Unsupported driver")


def test_connection() -> Tuple[bool, str, Dict[str, Any]]:
    """
    Tests the connection to MySQL and reports status.
    Returns: (is_connected, message, details)
    """
    if _DRIVER is None:
        return (
            False,
            "No MySQL driver found. Install with: pip install mysql-connector-python or pip install pymysql",
            {"driver": None}
        )

    cfg = get_db_config()
    details = {
        "driver": _DRIVER,
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "database": cfg["database"]
    }

    try:
        conn = get_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION();")
        version = cursor.fetchone()
        if isinstance(version, dict):
            version_str = list(version.values())[0]
        elif isinstance(version, (tuple, list)):
            version_str = version[0]
        else:
            version_str = str(version)
        details["version"] = version_str
        cursor.close()
        conn.close()
        return (True, f"Successfully connected to MySQL {version_str} ({cfg['database']})", details)
    except Exception as e:
        return (False, f"Connection failed: {str(e)}", details)
