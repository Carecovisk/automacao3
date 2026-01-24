import sqlite3


def init_sqlite_db(db_path: str = './data/output/query_results.db'):
    """Initialize SQLite database with queries and candidates tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create queries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create candidates table with foreign key to queries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL,
            candidate_text TEXT NOT NULL,
            distance REAL NOT NULL,
            rank INTEGER NOT NULL,
            FOREIGN KEY (query_id) REFERENCES queries(id) ON DELETE CASCADE
        )
    ''')
    
    # Create index for faster lookups
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidates_query_id 
        ON candidates(query_id)
    ''')
    
    conn.commit()
    return conn


def store_query_results(conn: sqlite3.Connection, query: str, docs: list[str], distances: list[float]):
    """Store a single query and its candidates in the database."""
    cursor = conn.cursor()
    
    # Insert query
    cursor.execute('INSERT INTO queries (query_text) VALUES (?)', (query,))
    query_id = cursor.lastrowid
    
    # Insert candidates
    for rank, (doc, distance) in enumerate(zip(docs, distances), start=1):
        cursor.execute('''
            INSERT INTO candidates (query_id, candidate_text, distance, rank)
            VALUES (?, ?, ?, ?)
        ''', (query_id, doc, distance, rank))
    
    conn.commit()
    return query_id
