import sqlite3

def show_sqlite_structure(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]

    print(f"Database: {db_file}\nTables: {table_names}\n")

    for table_name in table_names:
        print(f"--- Table: {table_name} ---")
        # Get column information
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            # col[1] is the column name, col[2] is the data type
            print(f"  --> {col[1]} ({col[2]})")

    conn.close()

# Usage example:
show_sqlite_structure("app.db")