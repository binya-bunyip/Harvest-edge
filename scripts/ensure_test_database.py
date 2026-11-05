import asyncio
import os

import asyncpg


async def main() -> None:
    connection = await asyncpg.connect(
        database="postgres",
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host="db",
    )
    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            "harvest_edge_test",
        )
        if not exists:
            await connection.execute("CREATE DATABASE harvest_edge_test")
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
