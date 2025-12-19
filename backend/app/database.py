import sqlite3
import logging
import json
import hashlib
import os

logger = logging.getLogger(__name__)


class SQLiteDB:
# ... (keeping class definition start) ...

    # ... (skipping to save_deep_summary)

    def save_deep_summary(self, file_path, summary, intermediate_summaries=None):
        # We use files_summary table, but update deep_summary column
        try:
            # Check if exists
            self.cursor.execute("SELECT file_path FROM files_summary WHERE file_path = ?", (file_path,))
            data = self.cursor.fetchone()
            
            intermediate_json = json.dumps(intermediate_summaries) if intermediate_summaries else None
            
            if data:
                self.cursor.execute("UPDATE files_summary SET deep_summary = ?, intermediate_summaries = ? WHERE file_path = ?", 
                                  (summary, intermediate_json, file_path))
            else:
                # Need to calculate hash for NOT NULL constraint
                file_hash = "unknown"
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                except Exception:
                    pass
                
                self.cursor.execute("INSERT INTO files_summary (file_path, file_hash, deep_summary, intermediate_summaries) VALUES (?, ?, ?, ?)", 
                                  (file_path, file_hash, summary, intermediate_json))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving deep summary: {e}")
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

        # Create thesis_projects table
        create_thesis_projects_table_query = """
        CREATE TABLE IF NOT EXISTS thesis_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.cursor.execute(create_thesis_projects_table_query)

        # Create thesis_structure table
        create_thesis_structure_table_query = """
        CREATE TABLE IF NOT EXISTS thesis_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            structure_data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES thesis_projects (id) ON DELETE CASCADE
        )
        """
        self.cursor.execute(create_thesis_structure_table_query)

        # Add deep_summary column to files_summary if it doesn't exist
        try:
            self.cursor.execute("ALTER TABLE files_summary ADD COLUMN deep_summary TEXT")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass

        try:
            self.cursor.execute("ALTER TABLE files_summary ADD COLUMN intermediate_summaries TEXT")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass
            
        try:
            self.cursor.execute("ALTER TABLE files_summary ADD COLUMN original_chunks TEXT")
        except sqlite3.OperationalError:
            # Column likely already exists
            pass
        
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

    def get_schema_by_name(self, name):
        self.cursor.execute("SELECT id FROM analysis_schemas WHERE name = ?", (name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

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

    def get_analyzed_file_paths(self, schema_id):
        self.cursor.execute("SELECT file_path FROM analysis_results WHERE schema_id = ?", (schema_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def delete_analysis_results(self, schema_id):
        self.cursor.execute("DELETE FROM analysis_results WHERE schema_id = ?", (schema_id,))
        self.conn.commit()


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

    # Thesis Methods
    def create_thesis_project(self, name, description=""):
        try:
            self.cursor.execute("INSERT INTO thesis_projects (name, description) VALUES (?, ?)", (name, description))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_thesis_projects(self):
        self.cursor.execute("SELECT id, name, description, created_at FROM thesis_projects")
        return self.cursor.fetchall()

    def get_thesis_project(self, project_id):
        self.cursor.execute("SELECT id, name, description FROM thesis_projects WHERE id = ?", (project_id,))
        return self.cursor.fetchone()

    def save_thesis_structure(self, project_id, structure_data):
        self.cursor.execute("INSERT INTO thesis_structure (project_id, structure_data) VALUES (?, ?)", (project_id, structure_data))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_thesis_structure(self, project_id):
         # Get latest
        self.cursor.execute("SELECT structure_data FROM thesis_structure WHERE project_id = ? ORDER BY created_at DESC LIMIT 1", (project_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def save_deep_summary(self, file_path, summary, intermediate_summaries=None, original_chunks=None):
        # We use files_summary table, but update deep_summary column
        try:
            # Check if exists
            self.cursor.execute("SELECT file_path FROM files_summary WHERE file_path = ?", (file_path,))
            data = self.cursor.fetchone()
            
            intermediate_json = json.dumps(intermediate_summaries) if intermediate_summaries else None
            chunks_json = json.dumps(original_chunks) if original_chunks else None
            
            if data:
                self.cursor.execute("UPDATE files_summary SET deep_summary = ?, intermediate_summaries = ?, original_chunks = ? WHERE file_path = ?", 
                                  (summary, intermediate_json, chunks_json, file_path))
            else:
                # Need to calculate hash for NOT NULL constraint
                file_hash = "unknown"
                try:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                except Exception:
                    pass
                    
                self.cursor.execute("INSERT INTO files_summary (file_path, file_hash, deep_summary, intermediate_summaries, original_chunks) VALUES (?, ?, ?, ?, ?)", 
                                  (file_path, file_hash, summary, intermediate_json, chunks_json))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error saving deep summary: {e}")

    def get_deep_summary(self, file_path):
        self.cursor.execute("SELECT deep_summary, intermediate_summaries, original_chunks FROM files_summary WHERE file_path = ?", (file_path,))
        result = self.cursor.fetchone()
        if result:
            # TREAT MISSING DEEP SUMMARY AS CACHE MISS
            if not result[0]: # deep_summary
                return None
            return {
                "deep_summary": result[0],
                "intermediate_summaries": json.loads(result[1]) if result[1] else [],
                "original_chunks": json.loads(result[2]) if result[2] else []
            }
        return None

    def save_thesis_plan(self, project_id, plan_json):
        try:
             self.cursor.execute("UPDATE thesis_projects SET plan_json = ? WHERE id = ?", (plan_json, project_id))
             self.conn.commit()
        except Exception as e:
             logger.error(f"Error saving thesis plan: {e}")

    def get_thesis_plan(self, project_id):
        try:
            self.cursor.execute("SELECT plan_json FROM thesis_projects WHERE id = ?", (project_id,))
            row = self.cursor.fetchone()
            if row and row[0]:
                return row[0]
            return None
        except Exception as e:
            logger.error(f"Error getting thesis plan: {e}")
            return None
