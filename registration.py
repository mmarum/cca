import os
import sys
import json
import requests
import MySQLdb
from urllib.parse import unquote, urlencode
from reg_form import RegistrationForm, RegFormWheelWars, RegFormPaintWars
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
    loader=PackageLoader('registration', '../app/templates'),
    autoescape=select_autoescape(['html'])
)

sys.path.insert(0, os.path.dirname(__file__))


def filter_form_data(environ):
    length = int(environ.get('CONTENT_LENGTH', '0'))
    post_input = environ['wsgi.input'].read(length).decode('UTF-8')
    post_input_list = post_input.split("&")
    form_data = {}
    for item in post_input_list:
        temp = item.split("=")
        name = temp[0]
        value = unquote(temp[1].replace("+", " "))
        if value != "":
            if name == "customer_phone" and "href" in value:
                value = clean_phone_number(value)
            form_data[name] = value
    #print("filter_form_data() form_data", form_data)
    return form_data


def registration(environ, start_response):

    dbuser = "catalystcreative_cca"
    passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

    method = environ['REQUEST_METHOD']
    path = environ['PATH_INFO']

    valid_registrations = ["art-camp", "wheel-wars", "paint-wars"] # "after-school", "summer-camp"

    if path == "" or path == "/":
        registration_name = "summer-camp" # set default
    else:
        if path.split("/")[1] not in valid_registrations:
            raise ValueError(f"Error: Path does not represent valid registration name. {path}")
        registration_name = path.split("/")[1]

    #print("registration_name", registration_name)
    #print("path", path)
    #print("method", method)

    #camps = ["art_camp_1", "art_camp_2", "art_camp_3", "art_camp_4", "pottery_camp_1"]

    camps = ["art_camp_2023_1", "art_camp_2023_2", "art_camp_2023_3", "art_camp_2023_4", "art_camp_2023_5", "art_camp_2023_6", "art_camp_2023_7", "art_camp_2023_8"]

    #if "summer-camp" in path and path.split("/")[2] in camps:
    if "art-camp" in path and path.split("/")[2] in camps:
        session_detail = path.split("/")[2]
    elif path.endswith("after-school"):
        session_detail = "After School Pottery Program 2020"
    else:
        session_detail = ""

    #print("session_detail", session_detail)

    #if method == "POST" and path.endswith("/confirm"):
    if path.endswith("/confirm"):
        #print("step: confirm")
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

        if registration_name in ["art-camp"]: # "summer-camp", "after-school"
            # An unchecked checkbox doesn't pass a value so we need this
            for i in ["treatment_permission", "photo_release"]:
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
  
        #print("CONFIRM")
        #print(f"post_input_dict: {post_input_dict}")
        #print(f"action: {action}")

        # UPDATE
        if action == "update":

            if registration_name in ["art-camp"]: # "summer-camp", "after-school"

                rid = int(post_input_dict["rid"])

                keys_vals = ""
                for k, v in post_input_dict.items():
                    if k != "submit":
                        keys_vals += str(f"{k}='{v}', ")
                keys_vals = keys_vals.rstrip(', ')

                sql = f"UPDATE registration SET {keys_vals} WHERE rid = {rid}"

                #print(f"sql: {sql}")

                c = db.cursor()
                c.execute(sql)
                c.close()

                #template = env.get_template("summer-camp.html")
                template = env.get_template("art-camp-registration.html")

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

            elif registration_name == "paint-wars":

                rid = str(post_input_dict["rid"])

                if rid and rid != "":

                    reg_file = "data/paint-wars.json"

                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())

                    reg_data[rid] = post_input_dict

                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()

                template = env.get_template("paint-wars.html")


            response = template.render(data=post_input_dict, rid=rid, registration_name=registration_name)

        # INSERT
        else:

            if registration_name in ["art-camp"]: # "summer-camp", "after-school"

                # Removing rid becuase this is an insert
                del fields[0]
                del vals[0]

                # Removing submit because not for the db
                fields.remove('submit')
                vals.remove('Continue')

                fields = str(fields).lstrip('[').rstrip(']').replace("'", "")
                vals = str(vals).lstrip('[').rstrip(']')
                sql = f"INSERT INTO registration ({fields}) VALUES ({vals})"

                #print(f"sql: {sql}")

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

                #template = env.get_template("summer-camp.html")
                template = env.get_template("art-camp-registration.html")
                response = template.render(data=post_input_dict, rid=rid, registration_name=registration_name)

            elif registration_name == "wheel-wars":

                post_input_dict["registration_name"] = "Wheel Wars"
                post_input_dict["event_date"] = "Saturday, March 25, 2023 3-5PM"

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
                response = template.render(data=post_input_dict, rid=post_input_dict["rid"], registration_name=registration_name)

            elif registration_name == "paint-wars":

                post_input_dict["registration_name"] = "Paint Wars"
                post_input_dict["event_date"] = "Saturday Oct 28, 2023, 7-9 PM"

                if post_input_dict["rid"] == "":

                    epoch_now = int(time.time())
                    rid = epoch_now
                    post_input_dict["rid"] = rid

                    reg_file = "data/paint-wars.json"

                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())

                    reg_data[rid] = post_input_dict

                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()

                template = env.get_template("paint-wars.html")
                response = template.render(data=post_input_dict, rid=post_input_dict["rid"], registration_name=registration_name)


    ####
    #elif method == "POST" and path.endswith("/edit"):
    elif path.endswith("/edit"):
        #print("step: edit")

        # DE-DUPE THESE NEXT 17 LINES:

        """
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

        #print("EDIT")
        #print(f"post_input_dict: {post_input_dict}")
        """

        form_data = filter_form_data(environ)
        rid = form_data["rid"]

        if registration_name == "wheel-wars":
            reg_data = json.loads(read_file("data/wheel-wars.json"))
            this_reg_data = reg_data[rid]
            form = RegFormWheelWars(**this_reg_data)
            template = env.get_template("wheel-wars.html")
        elif registration_name == "paint-wars":
            reg_data = json.loads(read_file("data/paint-wars.json"))
            this_reg_data = reg_data[rid]
            form = RegFormPaintWars(**this_reg_data)
            template = env.get_template("paint-wars.html")
        else:
            db.query(f"SELECT * FROM registration WHERE rid = {rid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            #print(f"row: {row}")
            form = RegistrationForm(**row)
            #template = env.get_template("summer-camp.html")
            template = env.get_template("art-camp-registration.html")

        response = template.render(form=form, registration_name=registration_name)


    ####
    #elif method == "POST" and path.endswith("/complete"):
    elif path.endswith("/complete"):

        #print("step: complete")
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        if registration_name in ["art-camp"]: # "summer-camp", "after-school"

            form_registration = json.loads(post_input)

            form_orders = form_registration.copy()

            #print("registration form_orders", form_orders)

            try:
                registrations = json.loads(read_file(f"../app/registration/registrations.json"))
            except:
                registrations = []
            registrations.append(form_registration)
            write_file(f"../app/registration/registrations.json", json.dumps(registrations, indent=4))

            passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
            url = "https://www.catalystcreativearts.com/email/submit"
            data = {"subject": "CCA Summer camp registration", "content": f"{json.dumps(form_registration, indent=4)}"}
            headers = {"Content-Type": "application/json"}

            try:
                r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
                #print("registration status_code", r.status_code)
            except:
                pass

            registration_id = int(form_registration["registration_id"])
            order_id = form_registration["order_id"]
            sql = f"UPDATE registration SET order_id = '{order_id}' WHERE rid = {registration_id}"

            #print(f"registration complete sql: {sql}")

            c = db.cursor()
            c.execute(sql)
            c.close()

            try:
                payer_info = {
                    "email": form_orders['parent_email'],
                    "name": form_orders['parent_name'],
                    "title": "registration",
                    "date": "",
                    "location": ""
                }
            except:
                payer_info = ""

            if type(payer_info) == dict:
                try:
                    #print('attempt to send to payer')
                    data = {"subject": "Thank you for your CCA Event purchase", "content": f"", "payer_info": f"{json.dumps(payer_info, indent=4)}"}
                    headers = {"Content-Type": "text/html"}
                    r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
                    generic_response = f"sendgrid response: {str(r.status_code)}"
                except:
                    generic_response = "ERROR: failed to communicate to payer by sendgrid email"
            else:
                generic_response = "ERROR: payer_info type is not dict"

            #print(generic_response)

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
            response = template.render(status="complete", registration_name=registration_name)


        elif registration_name == "paint-wars":

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

                reg_file = "data/paint-wars.json"

                f = open(reg_file, "r")
                reg_data = json.loads(f.read())

                reg_data[rid]["status"] = "complete"

                f = open(reg_file, "w")
                f.write(json.dumps(reg_data, indent=4))
                f.close()

            template = env.get_template("paint-wars.html")
            response = template.render(status="complete", registration_name=registration_name)



    ####
    elif path.endswith("/testing-123"):
        response = str(environ)
        write_file("testing-123.txt", response)


    else:

        if registration_name == "wheel-wars":
            form = RegFormWheelWars()
            template = env.get_template("wheel-wars.html")
            camper_count = "" # only for summer-school
        elif registration_name == "paint-wars":
            form = RegFormPaintWars()
            template = env.get_template("paint-wars.html")
            camper_count = "" # only for summer-school
        else:
            form = RegistrationForm()
            #template = env.get_template("summer-camp.html")
            template = env.get_template("art-camp-registration.html")

            # CAMPER COUNT:
            query = f"select camper1_name, camper2_name, camper3_name from registration where session_detail = '{session_detail}' and order_id is not NULL"
            #print("query", query)
            c = db.cursor()
            c.execute(query)
            allrows = c.fetchall()
            c.close()
            #print("allrows", allrows)

            camper_list = []
            for row in allrows:
                #print(row)
                for field in row:
                    if field != "" and field != None:
                        print("____field", field)
                        camper_list.append(field)

            #print("camper_list", camper_list)
            #print("len camper_list", len(camper_list))
            camper_count = int(len(camper_list))
            #print("camper_count", camper_count)

        response = template.render(form=form, registration_name=registration_name, session_detail=session_detail, camper_count=camper_count)

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

