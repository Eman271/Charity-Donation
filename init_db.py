"""Run once to create tables, views, trigger, and sample data."""
import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def init_db():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL is not set')

    with open('schema.sql', 'r') as f:
        sql = f.read()

    # Split into individual statements, respecting $$-quoted PL/pgSQL blocks
    statements = []
    current = []
    in_dollar_quote = False

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        if stripped.count('$$') % 2 == 1:
            in_dollar_quote = not in_dollar_quote
        current.append(line)
        if not in_dollar_quote and stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []

    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                try:
                    cur.execute(stmt)
                    print(f'  OK  {stmt[:70].replace(chr(10), " ").strip()}')
                except Exception as e:
                    print(f'  ERR {e} — {stmt[:60].replace(chr(10), " ").strip()}')

    print('\nDone — database is ready.')

if __name__ == '__main__':
    init_db()
