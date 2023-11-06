import sqlite3

class DB:
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.commit()
            self.cursor.close()
            self.connection.close()

    def create_player_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS players(id, name, positions, height, birth_date, foot, country, market_value)")

    def insert_player(self, info):
        values = info.values()
        self.cursor.execute(f"INSERT INTO players VALUES ({','.join(['?'] * len(values))})", tuple(values))

    def get_player(self, id):
        self.cursor.execute(f"SELECT * FROM players WHERE id=?", (id,))
        return self.cursor.fetchone()