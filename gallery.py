import os
import sys
import json
import MySQLdb
# mysql -u catalystcreative_cca catalystcreative_66 -p
# update piwigz_categories set comment = '' where id = 13;

def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

class Gallery:

    def __init__(self, category=1):
        self.category = category

    def get_gallery(self):

        # DEDUPE THIS LATER !!!
        dbuser = "catalystcreative_cca"
        passwd = json.loads(read_file("data/passwords.json"))[dbuser]
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_66")

        db.query(f"SELECT name, comment FROM piwigz_categories WHERE id = {self.category}")
        r = db.store_result()
        try:
            row = r.fetch_row(maxrows=1, how=1)[0]
            db.close()
            return row
        except:
            return ""

    def get_images(self):

        # DEDUPE THIS LATER !!!
        dbuser = "catalystcreative_cca"
        passwd = json.loads(read_file("data/passwords.json"))[dbuser]
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_66")

        c = db.cursor()
        c.execute(f"SELECT i.id, i.file, i.name, i.width, i.height, i.path \
            FROM piwigz_images i, piwigz_image_category c \
            WHERE c.image_id = i.id AND c.category_id = {self.category} \
            ORDER BY c.rank")
        # Learn how to use cursor to retrieve a few at a time
        allrows = c.fetchall()
        c.close()
        db.close()
        return allrows

"""
select id, name from piwigz_categories;
+----+---------------------+
| id | name                |
+----+---------------------+
|  1 | Acrylic Painting    |
|  2 | Watercolor Painting |
|  3 | Paint Your Pet      |
|  4 | Fused Glass         |
|  5 | Resin Art           |
|  6 | Fluid Art           |
|  7 | Summer Art Camp     |
+----+---------------------+
"""

