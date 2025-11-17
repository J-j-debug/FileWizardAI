import sqlite3


class SQLiteDB:
    def __init__(self):
        self.conn = sqlite3.connect('FileWizardAi.db')
        self.cursor = self.conn.cursor()
        # Enable foreign key support
        self.cursor.execute("PRAGMA foreign_keys = ON")

        # Create files_summary table
        create_files_summary_table_query = "CREATE TABLE IF NOT EXISTS files_summary (file_path TEXT PRIMARY KEY,file_hash TEXT NOT NULL,summary TEXT)"
        self.cursor.execute(create_files_summary_table_query)

        # Create notebooks table
        create_notebooks_table_query = """
        CREATE TABLE IF NOT EXISTS notebooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """
        self.cursor.execute(create_notebooks_table_query)

        # Create notebook_files table to link notebooks and files
        create_notebook_files_table_query = """
        CREATE TABLE IF NOT EXISTS notebook_files (
            notebook_id INTEGER,
            file_path TEXT,
            FOREIGN KEY (notebook_id) REFERENCES notebooks (id) ON DELETE CASCADE,
            FOREIGN KEY (file_path) REFERENCES files_summary (file_path) ON DELETE CASCADE,
            PRIMARY KEY (notebook_id, file_path)
        )
        """
        self.cursor.execute(create_notebook_files_table_query)

        # Create analysis_schemas table
        create_analysis_schemas_table_query = """
        CREATE TABLE IF NOT EXISTS analysis_schemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            schema_data TEXT NOT NULL
        )
        """
        self.cursor.execute(create_analysis_schemas_table_query)

        # Create analysis_results table
        create_analysis_results_table_query = """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schema_id INTEGER,
            file_path TEXT,
            results TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schema_id) REFERENCES analysis_schemas (id) ON DELETE CASCADE,
            FOREIGN KEY (file_path) REFERENCES files_summary (file_path) ON DELETE CASCADE
        )
        """
        self.cursor.execute(create_analysis_results_table_query)
        self.conn.commit()

    # Notebook CRUD methods
    def create_notebook(self, name, description=""):
        try:
            self.cursor.execute("INSERT INTO notebooks (name, description) VALUES (?, ?)", (name, description))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_notebooks(self):
        self.cursor.execute("SELECT id, name, description FROM notebooks")
        return self.cursor.fetchall()

    def update_notebook(self, notebook_id, name, description):
        try:
            self.cursor.execute("UPDATE notebooks SET name = ?, description = ? WHERE id = ?", (name, description, notebook_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_notebook(self, notebook_id):
        self.cursor.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        self.conn.commit()

    # Notebook file management
    def add_files_to_notebook(self, notebook_id, file_paths):
        try:
            with self.conn:
                # First, ensure all files exist in the files_summary table to satisfy foreign key constraints.
                # We'll insert them with a placeholder hash and summary.
                summary_files_to_add = [(path, "dummy_hash", "") for path in file_paths]
                self.cursor.executemany(
                    "INSERT OR IGNORE INTO files_summary (file_path, file_hash, summary) VALUES (?, ?, ?)",
                    summary_files_to_add
                )

                # Now, link the files to the notebook, ignoring duplicates.
                files_to_link = [(notebook_id, path) for path in file_paths]
                self.cursor.executemany("INSERT OR IGNORE INTO notebook_files (notebook_id, file_path) VALUES (?, ?)", files_to_link)
            return True
        except sqlite3.IntegrityError as e:
            # This block might still be useful for catching other unexpected integrity errors.
            print(f"Database integrity error: {e}")
            return False

    def get_files_for_notebook(self, notebook_id):
        self.cursor.execute("SELECT file_path FROM notebook_files WHERE notebook_id = ?", (notebook_id,))
        results = self.cursor.fetchall()
        return [row[0] for row in results]

    def remove_files_from_notebook(self, notebook_id, file_paths):
        files_to_remove = [(notebook_id, path) for path in file_paths]
        self.cursor.executemany("DELETE FROM notebook_files WHERE notebook_id = ? AND file_path = ?", files_to_remove)
        self.conn.commit()

    # Analysis Schema methods
    def create_analysis_schema(self, name, schema_data):
        try:
            self.cursor.execute("INSERT INTO analysis_schemas (name, schema_data) VALUES (?, ?)", (name, schema_data))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_analysis_schemas(self):
        self.cursor.execute("SELECT id, name, schema_data FROM analysis_schemas")
        return self.cursor.fetchall()

    def get_analysis_schema(self, schema_id):
        self.cursor.execute("SELECT id, name, schema_data FROM analysis_schemas WHERE id = ?", (schema_id,))
        return self.cursor.fetchone()

    # Analysis Result methods
    def save_analysis_result(self, schema_id, file_path, results):
        self.cursor.execute(
            "INSERT INTO analysis_results (schema_id, file_path, results) VALUES (?, ?, ?)",
            (schema_id, file_path, results)
        )
        self.conn.commit()

    def get_analysis_results(self, schema_id):
        self.cursor.execute(
            "SELECT file_path, results, timestamp FROM analysis_results WHERE schema_id = ?",
            (schema_id,)
        )
        return self.cursor.fetchall()


    # Existing methods for files_summary
    def select(self, table_name, where_clause=None):
        sql = f"SELECT * FROM {table_name}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def is_file_exist(self, file_path, file_hash):
        self.cursor.execute("SELECT * FROM files_summary WHERE file_path = ? AND file_hash = ?", (file_path, file_hash))
        file = self.cursor.fetchone()
        return bool(file)

    def insert_file_summary(self, file_path, file_hash, summary):
        self.cursor.execute("""
            INSERT INTO files_summary (file_path, file_hash, summary)
            VALUES (?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash = excluded.file_hash,
                summary = excluded.summary
        """, (file_path, file_hash, summary))
        self.conn.commit()

    def get_file_summary(self, file_path):
        self.cursor.execute("SELECT summary FROM files_summary WHERE file_path = ?", (file_path,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def drop_table(self):
        self.cursor.execute("DROP TABLE IF EXISTS files_summary")
        self.cursor.execute("DROP TABLE IF EXISTS notebook_files")
        self.cursor.execute("DROP TABLE IF EXISTS notebooks")
        self.conn.commit()

    def get_all_files(self):
        self.cursor.execute("SELECT file_path FROM files_summary")
        results = self.cursor.fetchall()
        files_path = [row[0] for row in results]
        return files_path

    def update_file(self, old_file_path, new_file_path, new_hash):
        self.cursor.execute("UPDATE files_summary SET file_path = ?, file_hash = ? WHERE file_path = ?",
                            (new_file_path, new_hash, old_file_path))
        self.conn.commit()

    def delete_records(self, file_paths):
        placeholders = ",".join("?" * len(file_paths))
        self.cursor.execute(f"DELETE FROM files_summary WHERE file_path IN ({placeholders})", file_paths)
        self.conn.commit()

    def close(self):
        self.conn.close()
