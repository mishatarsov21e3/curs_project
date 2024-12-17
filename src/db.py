import asyncpg
from config import DB_CONFIG


async def init_database():
    conn = await asyncpg.connect(
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        database='postgres'
    )

    try:
        try:
            await conn.execute(f"""
                CREATE DATABASE {DB_CONFIG['database']}
                OWNER {DB_CONFIG['user']}
                ENCODING 'UTF8';
            """)
            print(f"База данных {DB_CONFIG['database']} успешно создана.")
        except asyncpg.DuplicateDatabaseError:
            print(f"База данных {DB_CONFIG['database']} уже существует.")
    finally:
        await conn.close()

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT UNIQUE PRIMARY KEY,
                user_name TEXT,
                balance NUMERIC DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS shoes (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                shoe_id INT REFERENCES shoes(id),
                quantity INT NOT NULL,
                total_price NUMERIC NOT NULL,
                status TEXT DEFAULT 'pending'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                amount NUMERIC NOT NULL,
                type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        ]

        for query in tables:
            await conn.execute(query)
            print(f"Таблица создана: {query.split()[3]}")

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
    finally:
        await conn.close()