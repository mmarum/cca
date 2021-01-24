import os
import sys
import json
import requests
import MySQLdb
from reg_form import RegistrationForm, RegFormWheelWars
from jinja2 import Environment, PackageLoader, select_autoescape

#python3.6.8
#requests
#jinja2
#mysql
#mysqlclient


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

def write_file(file_name, content):
    f = open(file_name, "w")
    f.write(content)
    f.close()
    return True

env = Environment(
    loader=PackageLoader('registration', 'templates'),
    autoescape=select_autoescape(['html'])
)

sys.path.insert(0, os.path.dirname(__file__))

def registration(environ, start_response):

    dbuser = "catalystcreative_cca"
    passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

    method = environ['REQUEST_METHOD']
    path = environ['PATH_INFO']

    valid_registrations = ["after-school", "summer-camp", "wheel-wars"]

    if path == "" or path == "/":
        registration_name = "after-school" # set default
    else:
        if path.split("/")[1] not in valid_registrations:
            raise ValueError(f"Error: Path does not represent valid registration name. {path}")
        registration_name = path.split("/")[1]

    print("registration_name", registration_name)
        

    if method == "POST" and path.endswith("/confirm"):
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

        # An unchecked checkbox doesn't pass a value so we need this
        for i in ["session1", "session2", "treatment_permission", "photo_release"]:
            if i not in fields:
                post_input_dict[i] = '' 
                fields.append(i)
                vals.append('')

        try:
            if int(post_input_dict["rid"]) > 0:
                action = "update"
            else:
                action = "insert"
        except:
            action = "insert"
  
        print("CONFIRM")
        print(f"post_input_dict: {post_input_dict}")
        print(f"action: {action}")

        # UPDATE
        if action == "update":
            keys_vals = ""
            for k, v in post_input_dict.items():
                if k != "submit":
                    keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')

            rid = post_input_dict["rid"]
            sql = f"UPDATE registration SET {keys_vals} WHERE rid = {rid}"

            print(f"sql: {sql}")

            c = db.cursor()
            c.execute(sql)
            c.close()

        # INSERT
        else:
            # Removing rid becuase this is an insert
            del fields[0]
            del vals[0]

            # Removing submit because not for the db
            fields.remove('submit')
            vals.remove('Continue')

            fields = str(fields).lstrip('[').rstrip(']').replace("'", "")
            vals = str(vals).lstrip('[').rstrip(']')
            sql = f"INSERT INTO registration ({fields}) VALUES ({vals})"

            print(f"sql: {sql}")

            c = db.cursor()
            c.execute(sql)
            c.close()

            # TODO: Need to solve for refresh problem:
            # if user refreshes then they'll keep inserting new row
            # Possibly by adding a create_time field

            sql2 = f"SELECT max(rid) FROM registration"
            d = db.cursor()
            d.execute(sql2)
            rid = int(d.fetchone()[0])
            d.close()

        template = env.get_template("after-school.html")
        response = template.render(data=post_input_dict, rid=rid, registration_name=registration_name)


    ####
    elif method == "POST" and path.endswith("/edit"):

        # DE-DUPE THESE NEXT 17 LINES:

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

        print("EDIT")
        print(f"post_input_dict: {post_input_dict}")
        rid = post_input_dict["rid"]

        if registration_name == "wheel-wars":
            form = RegFormWheelWars(**row)
            template = env.get_template("wheel-wars.html")
        else:
            db.query(f"SELECT * FROM registration WHERE rid = {rid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            print(f"row: {row}")
            form = RegistrationForm(**row)
            template = env.get_template("after-school.html")

        response = template.render(form=form, registration_name=registration_name)


    ####
    elif method == "POST" and path.endswith("/complete"):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        form_registration = json.loads(post_input)
        try:
            registrations = json.loads(read_file(f"../app/registration/registrations.json"))
        except:
            registrations = []
        registrations.append(form_registration)
        write_file(f"../app/registration/registrations.json", json.dumps(registrations, indent=4))

        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
        url = "https://www.catalystcreativearts.com/email/submit"
        data = {"subject": "CCA Summer camp registration", "content": f"{json.dumps(registrations, indent=4)}"}
        headers = {"Content-Type": "application/json"}
        r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
        print(r.status_code)

        registration_id = int(form_registration["registration_id"])
        order_id = form_registration["order_id"]
        sql = f"UPDATE registration SET order_id = '{order_id}' WHERE rid = {registration_id}"

        print(f"sql: {sql}")

        c = db.cursor()
        c.execute(sql)
        c.close()

        response = "200"

    else:

        if registration_name == "wheel-wars":
            form = RegFormWheelWars()
            template = env.get_template("wheel-wars.html")
        else:
            form = RegistrationForm()
            template = env.get_template("after-school.html")

        response = template.render(form=form, registration_name=registration_name)

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

