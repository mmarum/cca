import os
import sys
import json
import MySQLdb
from reg_form import RegistrationForm
from jinja2 import Environment, PackageLoader, select_autoescape

def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

dbuser = "catalystcreative_cca"
passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]

env = Environment(
    loader=PackageLoader('registration', ''), # blank for no templates dir
    autoescape=select_autoescape(['html'])
)

sys.path.insert(0, os.path.dirname(__file__))
def registration(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    template = env.get_template("summer-camp.html")
    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit" and environ['HTTP_REFERER'].endswith('registration/'):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        key_val_array = post_input.split('\n')
        post_input_dict = {}
        fields = []
        vals = []
        for key_val in key_val_array:
            try:
                key = key_val.split('=')[0].strip()
                val = key_val.split('=')[1].strip()
                post_input_dict[key] = val
                fields.append(key)
                vals.append(val)
            except:
                pass

        for i in ["session1", "session2", "treatment_permission", "photo_release"]:
            if i not in fields:
                fields.append(i)
                vals.append(0)

        del fields[0:2]
        del vals[0:2]

        fields.remove('submit')
        vals.remove('Submit')

        # TODO: insert into database
        fields = str(fields).lstrip('[').rstrip(']').replace("'", "")
        vals = str(vals).lstrip('[').rstrip(']')
        sql = f"INSERT INTO registration ({fields}) VALUES ({vals})"

        #print(fields)
        #print(vals)
        print(sql)

        c = db.cursor()
        c.execute(sql)
        c.close()

        # SELECT latest rid
        rid = 1

        response = template.render(data=post_input_dict, rid=rid)

    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/edit" and environ['HTTP_REFERER'].endswith('registration/'):

        # TODO: select from database

        form = RegistrationForm(**row)
        response = template.render(form=form)

    else:
        form = RegistrationForm()
        response = template.render(form=form)

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

