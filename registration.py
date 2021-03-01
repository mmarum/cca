import os
import sys
import json
import requests
import MySQLdb
from reg_form import RegistrationForm, RegFormWheelWars
from jinja2 import Environment, PackageLoader, select_autoescape
import time


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

    valid_registrations = ["after-school", "summer-camp", "wheel-wars", "testing-123"]

    if path == "" or path == "/":
        registration_name = "summer-camp" # set default
    else:
        if path.split("/")[1] not in valid_registrations:
            raise ValueError(f"Error: Path does not represent valid registration name. {path}")
        registration_name = path.split("/")[1]

    print("registration_name", registration_name)
    print("path", path)
    print("method", method)

    if "summer-camp" in path:
        if path.endswith("art_camp_1"):
            reg_title = "Art Camp 1: Ages 7 & Up - June 21-25, 2021 - 9am-12pm"
        elif path.endswith("art_camp_2"):
            reg_title = "Art Camp 2: Ages 12 & Up - June 21-25, 2021 - 2pm-5pm"
        elif path.endswith("art_camp_3"):
            reg_title = "Art Camp 3: Ages 7 & Up - July 12-16, 2021 - 9am-12pm"
        elif path.endswith("art_camp_4"):
            reg_title = "Art Camp 4: Ages 12 & Up - July 12-16, 2021 - 9am-12pm"
        elif path.endswith("pottery_camp_1"):
            reg_title = "Pottery Camp - 8 & Up - July 19-23, 2021 - 9am-12pm"
    elif path.endswith("after-school"):
        reg_title = "After School Pottery Program 2020"
    else:
        reg_title = ""

    print("reg_title", reg_title)

    if method == "POST" and path.endswith("/confirm"):
        print("step: confirm")
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

        if registration_name == "summer-camp":
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

            if registration_name == "summer-camp":

                rid = int(post_input_dict["rid"])

                keys_vals = ""
                for k, v in post_input_dict.items():
                    if k != "submit":
                        keys_vals += str(f"{k}='{v}', ")
                keys_vals = keys_vals.rstrip(', ')

                sql = f"UPDATE registration SET {keys_vals} WHERE rid = {rid}"

                print(f"sql: {sql}")

                c = db.cursor()
                c.execute(sql)
                c.close()

                template = env.get_template("summer-camp.html")

            elif registration_name == "wheel-wars":

                rid = str(post_input_dict["rid"])

                if rid and rid != "":

                    reg_file = "data/wheel-wars.json"

                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())

                    reg_data[rid] = post_input_dict

                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()

                template = env.get_template("wheel-wars.html")

            response = template.render(data=post_input_dict, rid=rid, registration_name=registration_name, reg_title=reg_title)

        # INSERT
        else:

            if registration_name == "summer-camp":

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

                template = env.get_template("summer-camp.html")
                response = template.render(data=post_input_dict, rid=rid, registration_name=registration_name, reg_title=reg_title)

            elif registration_name == "wheel-wars":

                post_input_dict["registration_name"] = "Wheel Wars"
                post_input_dict["event_date"] = "Saturday March 27, 2021"

                if post_input_dict["rid"] == "":

                    epoch_now = int(time.time())
                    rid = epoch_now
                    post_input_dict["rid"] = rid

                    reg_file = "data/wheel-wars.json"

                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())

                    reg_data[rid] = post_input_dict

                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()

                template = env.get_template("wheel-wars.html")
                response = template.render(data=post_input_dict, rid=post_input_dict["rid"], registration_name=registration_name, reg_title=reg_title)

    ####
    elif method == "POST" and path.endswith("/edit"):
        print("step: edit")

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
            reg_data = json.loads(read_file("data/wheel-wars.json"))
            this_reg_data = reg_data[rid]
            form = RegFormWheelWars(**this_reg_data)
            template = env.get_template("wheel-wars.html")
        else:
            db.query(f"SELECT * FROM registration WHERE rid = {rid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            print(f"row: {row}")
            form = RegistrationForm(**row)
            template = env.get_template("summer-camp.html")

        response = template.render(form=form, registration_name=registration_name, reg_title=reg_title)


    ####
    elif method == "POST" and path.endswith("/complete"):



        print("step: complete")
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        if registration_name == "summer-camp":

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

        elif registration_name == "wheel-wars":

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

            rid = str(post_input_dict["rid"])

            if rid and rid != "":

                reg_file = "data/wheel-wars.json"

                f = open(reg_file, "r")
                reg_data = json.loads(f.read())

                reg_data[rid]["status"] = "complete"

                f = open(reg_file, "w")
                f.write(json.dumps(reg_data, indent=4))
                f.close()

            template = env.get_template("wheel-wars.html")
            response = template.render(status="complete", registration_name=registration_name, reg_title=reg_title)


    ####
    elif path.endswith("/testing-123"):
        response = str(environ)
        write_file("testing-123.txt", response)


    else:

        if registration_name == "wheel-wars":
            form = RegFormWheelWars()
            template = env.get_template("wheel-wars.html")
        else:
            form = RegistrationForm()
            template = env.get_template("summer-camp.html")

        response = template.render(form=form, registration_name=registration_name, reg_title=reg_title)

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

