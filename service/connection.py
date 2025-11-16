import psycopg2

from variables import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


try:
    connection = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
except:
    print(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
    print("Unable to connect to the database")
