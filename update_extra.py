import os
import sys
import json
import MySQLdb

# mysql -u catalystcreative_cca catalystcreative_arts -p

"""
Usage:
from update_extra import UpdateExtra
u = UpdateExtra(311, "Feb 6 3-5pm, Feb 6 6-8pm, Feb 7 1-3pm, Feb 7 4-6pm", 20)
u.set_via_admin()
u.set_via_purchase("Feb 7 1-3pm")
u.update_extra()
"""

dbuser = "catalystcreative_cca"
dbname = "catalystcreative_arts"
f = open("data/passwords.json", "r")
dbpass = json.loads(f.read())[dbuser]
f.close()

class UpdateExtra:

    def __init__(self, eid, price_text, elimit):
        self.eid = int(eid)
        self.contents = price_text
        self.elimit = int(elimit)
        self.sql = ""

        if ";" in self.contents:
            raise ValueError("contents must not contain semicolon")

        # GET EXISTING extra_data value
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=dbpass, db=dbname)
        db.query(f"SELECT extra_data FROM events WHERE eid = {self.eid}")
        r = db.store_result()
        try:
            row = r.fetch_row(maxrows=1, how=1)[0]
            self.existing_data = json.loads(row["extra_data"])
        except:
            self.existing_data = ""
        db.close()
        print("self.existing_data", self.existing_data)


    def set_via_admin(self):
        if self.existing_data != "":
            print("DO NOTHING: Already has existing data")
            print("self.existing_data", self.existing_data)
            return True

        # ONLY SET if there is no existing_data
        if self.existing_data == "":
            contents_array = self.contents.split(",")
            print("contents_array", contents_array)
            spots_remaining = int(self.elimit / len(contents_array))
            print("spots_remaining", spots_remaining)

            # Convert contents to json:
            this_object = {}
            for item in contents_array:
                this_object[item.lstrip()] = spots_remaining

            contents_json = json.dumps({ "spots_remaining": this_object })

            self.sql = f"UPDATE events SET extra_data = '{str(contents_json)}' WHERE eid = {self.eid}"
            print(self.sql)


    def set_via_purchase(self, key):
        print("self.existing_data", self.existing_data)
        self.existing_data["spots_remaining"][key] -= 1
        contents_json = json.dumps(self.existing_data)
        self.sql = f"UPDATE events SET extra_data = '{str(contents_json)}' WHERE eid = {self.eid}"
        print(self.sql)


    def update_extra(self):
        if self.sql != "":
            db = MySQLdb.connect(host="localhost", user=dbuser, passwd=dbpass, db=dbname)
            c = db.cursor()
            c.execute(self.sql)
            c.close()

