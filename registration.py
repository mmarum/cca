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


    print("path", path)


    # CHECK CAMP
    camp_type = path.split("/")[1]
    print("camp_type", camp_type)
    valid_camps = json.loads(read_file("../app/data/valid-camps.json"))
    if camp_type not in valid_camps:
        raise ValueError(f"Error: Path does not represent valid camp type. \
                camp_type: {camp_type}, valid_camps: {str(valid_camps)}")


    # CHECK SESSION
    session_detail = path.split("/")[2]
    print("session_detail", session_detail)
    valid_sessions = json.loads(read_file("../app/data/valid-sessions.json"))
    if session_detail not in valid_sessions:
        raise ValueError(f"Error: Path does not represent valid session detail. \
                session_detail: {session_detail}, valid_sessions: {str(valid_sessions)}")


    if path.endswith("/confirm"):
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

                if "'" in val:
                    val = val.replace("'", "''")

                vals.append(val)
            except:
                pass

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
  

        # UPDATE
        if action == "update":

            if "art-camp" in camp_type or "after-school" in camp_type:
                rid = int(post_input_dict["rid"])
                keys_vals = ""
                for k, v in post_input_dict.items():
                    if "'" in v:
                        v = v.replace("'", "''")
                    if k != "submit":
                        keys_vals += str(f"{k}='{v}', ")
                keys_vals = keys_vals.rstrip(', ')
                sql = f"UPDATE registration SET {keys_vals} WHERE rid = {rid}"
                c = db.cursor()
                c.execute(sql)
                c.close()
                template = env.get_template(f"{camp_type}-registration.html")

            elif "wheel-wars" in camp_type or "paint-wars" in camp_type:
                rid = str(post_input_dict["rid"])
                if rid and rid != "":
                    reg_file = f"data/{camp_type}.json"
                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())
                    reg_data[rid] = post_input_dict
                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()
                template = env.get_template(f"{camp_type}-registration.html")

            response = template.render(data=post_input_dict, rid=rid, camp_type=camp_type)


        # INSERT
        else:

            if "art-camp" in camp_type or "after-school" in camp_type:

                # Removing rid becuase this is an insert
                del fields[0]
                del vals[0]

                # Removing submit because not for the db
                fields.remove('submit')
                vals.remove('Continue')

                fields = str(fields).lstrip('[').rstrip(']').replace("'", "")
                vals = str(vals).lstrip('[').rstrip(']')
                sql = f"INSERT INTO registration ({fields}) VALUES ({vals})"

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

                template = env.get_template(f"{camp_type}-registration.html")
                response = template.render(data=post_input_dict, rid=rid, camp_type=camp_type)

            elif "wheel-wars" in camp_type or "paint-wars" in camp_type:

                post_input_dict["camp_type"] = camp_type
                post_input_dict["event_date"] = "Event Date TBD"

                if post_input_dict["rid"] == "":

                    epoch_now = int(time.time())
                    rid = epoch_now
                    post_input_dict["rid"] = rid

                    reg_file = f"data/{camp_type}.json"

                    f = open(reg_file, "r")
                    reg_data = json.loads(f.read())

                    reg_data[rid] = post_input_dict

                    f = open(reg_file, "w")
                    f.write(json.dumps(reg_data, indent=4))
                    f.close()

                template = env.get_template(f"{camp_type}-registration.html")
                response = template.render(data=post_input_dict, rid=post_input_dict["rid"], camp_type=camp_type)


    elif path.endswith("/edit"):

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

        if "wheel-wars" in camp_type or "paint-wars" in camp_type:
            reg_data = json.loads(read_file(f"data/{camp_type}.json"))
            this_reg_data = reg_data[rid]
            if "wheel-wars" in camp_type:
                form = RegFormWheelWars(**this_reg_data)
            if "paint-wars" in camp_type:
                form = RegFormPaintWars(**this_reg_data)
            template = env.get_template(f"{camp_type}-registration.html")

        elif "art-camp" in camp_type:
            db.query(f"SELECT * FROM registration WHERE rid = {rid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            form = RegistrationForm(**row)
            template = env.get_template(f"{camp_type}-registration.html")

        response = template.render(form=form, camp_type=camp_type)


    elif path.endswith("/complete"):

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        if "art-camp" in camp_type or "after-school" in camp_type:

            form_registration = json.loads(post_input)
            form_orders = form_registration.copy()

            try:
                sessions = json.loads(read_file(f"../app/registration/sessions.json"))
            except:
                sessions = []
            sessions.append(form_registration)
            write_file(f"../app/registration/sessions.json", json.dumps(sessions, indent=4))

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

            response = "200"

        elif "wheel-wars" in camp_type or "paint-wars" in camp_type:

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

                    if "'" in val:
                        val = val.replace("'", "''")

                    vals.append(val)
                except:
                    pass

            rid = str(post_input_dict["rid"])

            if rid and rid != "":

                reg_file = f"data/{camp_type}.json"

                f = open(reg_file, "r")
                reg_data = json.loads(f.read())

                reg_data[rid]["status"] = "complete"

                f = open(reg_file, "w")
                f.write(json.dumps(reg_data, indent=4))
                f.close()

            template = env.get_template(f"{camp_type}-registration.html")
            response = template.render(status="complete", camp_type=camp_type)


    ####
    elif path.endswith("/testing-123"):
        response = str(environ)
        write_file("testing-123.txt", response)


    else:

        if "wheel-wars" in camp_type:
            form = RegFormWheelWars()
            template = env.get_template(f"{camp_type}-registration.html")
            camper_count = "" # only for summer-school

        elif "paint-wars" in camp_type:
            form = RegFormPaintWars()
            template = env.get_template(f"{camp_type}-registration.html")
            camper_count = "" # only for summer-school

        else:
            form = RegistrationForm()
            template = env.get_template(f"{camp_type}-registration.html")

            # CAMPER COUNT:
            query = f"select camper1_name, camper2_name, camper3_name from registration where session_detail = '{session_detail}' and order_id is not NULL"
            c = db.cursor()
            c.execute(query)
            allrows = c.fetchall()
            c.close()

            camper_list = []
            for row in allrows:
                for field in row:
                    if field != "" and field != None:
                        print("____field", field)
                        camper_list.append(field)

            camper_count = int(len(camper_list))

        response = template.render(form=form, camp_type=camp_type, session_detail=session_detail, camper_count=camper_count)

    return [response.encode()]

