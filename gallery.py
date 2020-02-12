import os
import sys
import json
import MySQLdb
# mysql -u jedmarum_cca jedmarum_piwi833 -p

def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

class Gallery:
    def __init__(self, category=6):
        self.category = category

    def get_images(self):
        dbuser = "jedmarum_cca"
        passwd = json.loads(read_file("data/passwords.json"))[dbuser]
        # TODO: Do something with category
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="jedmarum_piwi833")
        c = db.cursor()
        c.execute(f"select id, file, name, width, height, path from piwigz_images limit 10")
        allrows = c.fetchall()
        c.close()
        db.close()
        return allrows

