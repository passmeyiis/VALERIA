import sqlite3
con = sqlite3.connect('valeria.db')
tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(t[0])