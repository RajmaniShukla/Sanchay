import sqlite3
conn = sqlite3.connect('data/sanchay.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in c.fetchall()]
print('DATABASE TABLES:')
for t in tables:
    c.execute(f'SELECT COUNT(*) FROM {t}')
    count = c.fetchone()[0]
    print(f'  {t:<30} -> {count} rows')

print()
c.execute('SELECT name FROM roles')
print('ROLES CREATED:')
for r in c.fetchall():
    print(f'  - {r[0]}')

c.execute('SELECT username, full_name FROM users')
print()
print('USERS CREATED:')
for r in c.fetchall():
    print(f'  - {r[0]} ({r[1]})')
conn.close()
print('\nDB verification complete.')
