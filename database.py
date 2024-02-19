import json
# https://github.com/PyMySQL/mysqlclient-python
# https://mysqlclient.readthedocs.io/user_guide.html
import MySQLdb


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


class Database:
    def __init__(self):
        dbuser = "catalystcreative_cca"
        dbname = "catalystcreative_arts"
        dbpass = json.loads(read_file("data/passwords.json"))[dbuser]
        self.db = MySQLdb.connect(host="localhost", user=dbuser, 
                passwd=dbpass, db=dbname)
        self.c = self.db.cursor()

    def query(self, sql):
        self.c.execute(sql)
        # Returns list of lists
        rows = self.c.fetchall()
        self.c.close()
        self.db.close()
        return rows

