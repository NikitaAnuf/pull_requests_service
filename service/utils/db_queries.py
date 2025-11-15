from psycopg2.extras import RealDictCursor

from connection import connection


def select_query(query: str, parameters: dict = {}, return_one: bool = False) -> tuple | None:
    with connection.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, parameters)
        if cursor.rowcount == 0:
            return None
        else:
            result = cursor.fetchone() if return_one else cursor.fetchall()
    return result


def change_data_query(query: str, parameters: dict) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        return True if cursor.rowcount >= 1 else False
