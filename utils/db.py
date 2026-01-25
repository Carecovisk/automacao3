from pathlib import Path
import sqlite3

from utils.ai import PesquisaPrompt


class QueryResultsDB:
    """SQLite helper for storing prompts and candidate items."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor() # type: ignore

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id TEXT NOT NULL,
                query_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )

        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                candidate_text TEXT NOT NULL,
                distance REAL NOT NULL,
                score REAL NOT NULL,
                rank INTEGER NOT NULL,
                FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
            )
            '''
        )

        cursor.execute(
            '''
            CREATE INDEX IF NOT EXISTS idx_candidates_query_id 
            ON candidates(query_id)
            '''
        )

        self.conn.commit()

    def store_prompts(self, prompts: list[PesquisaPrompt]) -> None:
        """Persist prompts and their candidate items."""
        if self.conn is None:
            raise ValueError("Database connection is not initialized.")

        cursor = self.conn.cursor()

        for prompt in prompts:
            cursor.execute(
                'INSERT INTO queries (prompt_id, query_text) VALUES (?, ?)',
                (str(prompt.id), prompt.item_description),
            )
            query_id = cursor.lastrowid

            for rank, item in enumerate(prompt.items, start=1):
                cursor.execute(
                    '''
                    INSERT INTO candidates (query_id, candidate_text, distance, score, rank)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (query_id, item.description, item.distance, item.score, rank),
                )

        self.conn.commit()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
