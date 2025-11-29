import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'youvisa.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH.as_posix())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            cpf TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Countries
    c.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            required_docs TEXT -- Comma separated list of doc types
        )
    ''')
    
    # Tasks (Visa Applications)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            country_id INTEGER,
            status TEXT DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, READY
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(country_id) REFERENCES countries(id)
        )
    ''')
    
    # Documents
    c.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            doc_type TEXT,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(telegram_id, name, cpf):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (telegram_id, name, cpf) VALUES (?, ?, ?)', (telegram_id, name, cpf))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user(telegram_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_country(name, required_docs):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO countries (name, required_docs) VALUES (?, ?)', (name, required_docs))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_countries():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM countries')
    countries = c.fetchall()
    conn.close()
    return countries

def get_country_by_name(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM countries WHERE name = ?', (name,))
    country = c.fetchone()
    conn.close()
    return country

def create_task(user_id, country_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO tasks (user_id, country_id, status) VALUES (?, ?, ?)', (user_id, country_id, 'IN_PROGRESS'))
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_user_active_task(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT t.*, c.name as country_name, c.required_docs 
        FROM tasks t 
        JOIN countries c ON t.country_id = c.id 
        WHERE t.user_id = ? AND t.status != 'COMPLETED'
        ORDER BY t.created_at DESC LIMIT 1
    ''', (user_id,))
    task = c.fetchone()
    conn.close()
    return task

def add_document(task_id, doc_type, file_path):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO documents (task_id, doc_type, file_path) VALUES (?, ?, ?)', (task_id, doc_type, file_path))
    conn.commit()
    conn.close()

def get_task_documents(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM documents WHERE task_id = ?', (task_id,))
    docs = c.fetchall()
    conn.close()
    return docs

def update_task_status(task_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
    conn.commit()
    conn.close()

def get_all_tasks_details():
    conn = get_connection()
    # Returns a pandas-friendly list of dicts or tuples
    query = '''
        SELECT 
            t.id as task_id,
            u.name as user_name,
            u.cpf as user_cpf,
            c.name as country,
            c.required_docs,
            t.status,
            t.created_at
        FROM tasks t
        JOIN users u ON t.user_id = u.id
        JOIN countries c ON t.country_id = c.id
    '''
    import pandas as pd
    return pd.read_sql_query(query, conn)

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
