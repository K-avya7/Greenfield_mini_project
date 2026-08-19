import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()  # Reads .env file for local testing


def get_setting(key: str, default: str = ""):
    """Retrieve configuration from Streamlit secrets first, then OS environment variables."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


class DatabaseConnection:
    """
    Singleton that manages a MySQL connection to hr_analytics_dw / Aiven.
    Only one instance is ever created (Singleton pattern).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {
                "host": get_setting("DB_HOST", "127.0.0.1"),
                "user": get_setting("DB_USER", "root"),
                "password": str(get_setting("DB_PASSWORD", "")),
                "port": int(get_setting("DB_PORT", "3306")),
                "database": get_setting("DB_NAME", "employee_analytics_dw2"),
                "use_pure": str(get_setting("DB_USE_PURE", "True")).lower() == "true",
                "connection_timeout": int(get_setting("DB_CONNECTION_TIMEOUT", "20")),
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