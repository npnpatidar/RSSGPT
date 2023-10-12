import sqlite3
import threading

class SQLiteConnectionPool:
    def __init__(self, max_connections, database_uri):
        self.max_connections = max_connections
        self.database_uri = database_uri
        self.connections = []
        self.lock = threading.Lock()

    def get_connection(self):
        with self.lock:
            if len(self.connections) < self.max_connections:
                connection = sqlite3.connect(self.database_uri)
                self.connections.append(connection)
                return connection
            else:
                raise Exception("Connection pool exhausted")

    def release_connection(self, connection):
        with self.lock:
            if connection in self.connections:
                self.connections.remove(connection)
                connection.close()

    def close_all_connections(self):
        with self.lock:
            for connection in self.connections:
                connection.close()
            self.connections = []

# Example usage
#pool = SQLiteConnectionPool(max_connections=5, database_uri='your_database.db')

# Get a connection from the pool
#connection = pool.get_connection()

# Execute queries using the connection

# Release the connection back to the pool
#pool.release_connection(connection)

# When your application exits, be sure to close all connections
#pool.close_all_connections()
