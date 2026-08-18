"""
db_manager.py
─────────────
Singleton DatabaseConnection class.
Loads credentials from .env and provides connections to hr_analytics_dw.
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()  # reads .env file


class DatabaseConnection:
    """
    Singleton that manages a MySQL connection to hr_analytics_dw.
    Only one instance is ever created (Singleton pattern).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {
                "host":     os.getenv("DB_HOST",     "127.0.0.1"),
                "user":     os.getenv("DB_USER",     "root"),
                "password": os.getenv("DB_PASSWORD", ""),
                "database": os.getenv("DB_NAME",     "employee_analytics_dw2"),
                "use_pure": os.getenv("DB_USE_PURE", "True") == "True",
            }
        return cls._instance

    # ── public API ─────────────────────────────────────────────
    def get_connection(self):
        """Return a live mysql.connector connection."""
        try:
            conn = mysql.connector.connect(**self._config)
            return conn
        except Error as e:
            raise ConnectionError(f"[DB] Could not connect: {e}") from e

    def execute_read(self, sql: str, params: tuple = ()) -> list[dict]:
        """Run a SELECT and return list of row-dicts."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            return cursor.fetchall()
        except Error as e:
            raise RuntimeError(f"[DB] Read failed: {e}") from e
        finally:
            cursor.close()
            conn.close()

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Run INSERT / UPDATE / DELETE. Returns affected row count."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        except Error as e:
            conn.rollback()
            raise RuntimeError(f"[DB] Write failed: {e}") from e
        finally:
            cursor.close()
            conn.close()

    def call_procedure(self, proc_name: str, args: tuple = ()) -> list:
        """Call a stored procedure and collect all result sets."""
        conn = self.get_connection()
        results = []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.callproc(proc_name, args)
            for result in cursor.stored_results():
                results.extend(result.fetchall())
            conn.commit()
            return results
        except Error as e:
            raise RuntimeError(f"[DB] Procedure '{proc_name}' failed: {e}") from e
        finally:
            cursor.close()
            conn.close()