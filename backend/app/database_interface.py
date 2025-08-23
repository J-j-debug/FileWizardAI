from abc import ABC, abstractmethod

class DatabaseInterface(ABC):

    @abstractmethod
    def select(self, table_name, where_clause=None):
        pass

    @abstractmethod
    def is_file_exist(self, file_path, file_hash):
        pass

    @abstractmethod
    def insert_file_summary(self, file_path, file_hash, summary, topic, tags):
        pass

    @abstractmethod
    def get_file_summary(self, file_path):
        pass

    @abstractmethod
    def drop_table(self):
        pass

    @abstractmethod
    def get_all_files(self):
        pass

    @abstractmethod
    def update_file(self, old_file_path, new_file_path, new_hash):
        pass

    @abstractmethod
    def delete_records(self, file_paths):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def initialize_prompts(self, prompts: dict):
        pass

    @abstractmethod
    def get_prompt(self, prompt_name):
        pass

    @abstractmethod
    def get_all_prompts(self):
        pass

    @abstractmethod
    def update_prompt(self, prompt_name, prompt_text):
        pass
