import mysql.connector
from mysql.connector import Error

class DatabaseConnection:
    """Singleton class managing connections to MySQL OLTP and OLAP databases."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._config = {
                "host": "127.0.0.1",
                "user": "root",
                "password": "V@mpire3053"
            }
        return cls._instance

    def get_connection(self, db_name: str):
        """Creates and returns a connection instance for the specified database."""
        try:
            config = self._config.copy()
            config["database"] = db_name
            return mysql.connector.connect(**config)
        except Error as e:
            print(f"[DATABASE CONNECTION ERROR] ({db_name}): {e}")
            return None