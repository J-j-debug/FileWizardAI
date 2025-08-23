import psycopg2
import psycopg2.errors
from .database_interface import DatabaseInterface

class SupabaseDB(DatabaseInterface):
    def __init__(self, db_url):
        self.conn = psycopg2.connect(db_url)
        self.cursor = self.conn.cursor()
        create_table_query = "CREATE TABLE IF NOT EXISTS files_summary (file_path TEXT PRIMARY KEY,file_hash TEXT NOT NULL,summary TEXT)"
        self.cursor.execute(create_table_query)
        self.conn.commit()
        try:
            self.cursor.execute("ALTER TABLE files_summary ADD COLUMN topic TEXT")
            self.conn.commit()
        except psycopg2.errors.DuplicateColumn:
            self.conn.rollback()
        try:
            self.cursor.execute("ALTER TABLE files_summary ADD COLUMN tags TEXT")
            self.conn.commit()
        except psycopg2.errors.DuplicateColumn:
            self.conn.rollback()

        create_prompts_table_query = "CREATE TABLE IF NOT EXISTS prompts (prompt_name TEXT PRIMARY KEY, prompt_text TEXT NOT NULL)"
        self.cursor.execute(create_prompts_table_query)
        self.conn.commit()

    def select(self, table_name, where_clause=None):
        sql = f"SELECT * FROM {table_name}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def is_file_exist(self, file_path, file_hash):
        self.cursor.execute("SELECT * FROM files_summary WHERE file_path = %s AND file_hash = %s", (file_path, file_hash))
        file = self.cursor.fetchone()
        return bool(file)

    def insert_file_summary(self, file_path, file_hash, summary, topic, tags):
        self.cursor.execute("SELECT * FROM files_summary WHERE file_path=%s", (file_path,))
        user_exists = self.cursor.fetchone()

        if user_exists:
            self.cursor.execute("UPDATE files_summary SET file_hash=%s, summary=%s, topic=%s, tags=%s WHERE file_path=%s",
                                (file_hash, summary, topic, tags, file_path))
        else:
            self.cursor.execute("INSERT INTO files_summary (file_path, file_hash, summary, topic, tags) VALUES (%s, %s, %s, %s, %s)",
                                (file_path, file_hash, summary, topic, tags))
        self.conn.commit()

    def get_file_summary(self, file_path):
        self.cursor.execute("SELECT summary, topic, tags FROM files_summary WHERE file_path = %s", (file_path,))
        result = self.cursor.fetchone()
        if result:
            return {"summary": result[0], "topic": result[1], "tags": result[2]}
        return None

    def drop_table(self):
        self.cursor.execute("DROP TABLE IF EXISTS files_summary")
        self.cursor.execute("DROP TABLE IF EXISTS prompts")
        self.conn.commit()

    def get_all_files(self):
        self.cursor.execute("SELECT file_path FROM files_summary")
        results = self.cursor.fetchall()
        files_path = [row[0] for row in results]
        return files_path

    def update_file(self, old_file_path, new_file_path, new_hash):
        self.cursor.execute("UPDATE files_summary SET file_path = %s, file_hash = %s WHERE file_path = %s",
                            (new_file_path, new_hash, old_file_path))
        self.conn.commit()

    def delete_records(self, file_paths):
        if not file_paths:
            return
        placeholders = ",".join(["%s"] * len(file_paths))
        self.cursor.execute(f"DELETE FROM files_summary WHERE file_path IN ({placeholders})", file_paths)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def initialize_prompts(self, prompts: dict):
        for name, text in prompts.items():
            self.cursor.execute("SELECT * FROM prompts WHERE prompt_name=%s", (name,))
            exists = self.cursor.fetchone()
            if not exists:
                self.cursor.execute("INSERT INTO prompts (prompt_name, prompt_text) VALUES (%s, %s)", (name, text))
        self.conn.commit()

    def get_prompt(self, prompt_name):
        self.cursor.execute("SELECT prompt_text FROM prompts WHERE prompt_name = %s", (prompt_name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_prompts(self):
        self.cursor.execute("SELECT prompt_name, prompt_text FROM prompts")
        results = self.cursor.fetchall()
        return [{"prompt_name": row[0], "prompt_text": row[1]} for row in results]

    def update_prompt(self, prompt_name, prompt_text):
        self.cursor.execute("UPDATE prompts SET prompt_text=%s WHERE prompt_name=%s", (prompt_text, prompt_name))
        self.conn.commit()
