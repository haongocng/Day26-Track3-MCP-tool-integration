import os
import sqlite3

# Path to store SQLite database file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    student_id INTEGER,
    course_id INTEGER,
    score REAL CHECK(score >= 0 AND score <= 100),
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
"""

SEED_SQL = """
-- Insert mock students
INSERT OR IGNORE INTO students (id, name, cohort) VALUES 
(1, 'Alice Nguyen', 'A1'),
(2, 'Bob Tran', 'A1'),
(3, 'Charlie Le', 'B1'),
(4, 'David Pham', 'B2'),
(5, 'Eva Vu', 'B1');

-- Insert mock courses
INSERT OR IGNORE INTO courses (id, title) VALUES 
(1, 'Mathematics'),
(2, 'Computer Science'),
(3, 'Physics');

-- Insert mock enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, score) VALUES 
(1, 1, 95.5),  -- Alice in Mathematics
(1, 2, 88.0),  -- Alice in CS
(2, 1, 76.0),  -- Bob in Mathematics
(2, 2, 91.5),  -- Bob in CS
(3, 2, 82.0),  -- Charlie in CS
(3, 3, 65.5),  -- Charlie in Physics
(4, 3, 89.0),  -- David in Physics
(5, 1, 88.0),  -- Eva in Mathematics
(5, 2, 79.5);  -- Eva in CS
"""

def create_database(db_path=DB_PATH):
    """
    Connect to SQLite, run the schema SQL to create structures,
    load seed data, and return the path to the database file.
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Connect and initialize database
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Execute tables creation
        cursor.executescript(SCHEMA_SQL)
        
        # Load seed data
        cursor.executescript(SEED_SQL)
        
        # Commit transaction
        conn.commit()
        print(f"[SUCCESS] Database initialized successfully at: {db_path}")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"[ERROR] Failed to initialize database: {e}")
        raise e
    finally:
        conn.close()
        
    return db_path

if __name__ == "__main__":
    create_database()
