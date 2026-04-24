import json
import pymysql
from tools import read_file


def query(sql):

    sql = sql.lower()
    dbname = "catalystcreative_66" if "piwigz" in sql else "catalystcreative_arts"
    dbuser = "catalystcreative_cca"
    dbpass = json.loads(read_file("data/passwords.json"))[dbuser]

    db = pymysql.connect(
        host = "localhost",
        user = dbuser,
        password = dbpass,
        database = dbname,
        cursorclass = pymysql.cursors.DictCursor
    )

    with db.cursor() as cur:

        cur.execute(sql)
        if "select" in sql:
            rows = cur.fetchmany(1000)

    if "select" not in sql:
        db.commit()

    if "insert" in sql:
        new_id = cur.lastrowid

    db.close()

    if "select" in sql:
        return rows

    elif "insert" in sql:
        return new_id

