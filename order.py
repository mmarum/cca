import os
import sys
import json
import requests
sys.path.insert(0, os.path.dirname(__file__))
from random import *

from update_extra import UpdateExtra

import MySQLdb

domain = "https://www.catalystcreativearts.com"

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


def order(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    passwd = json.loads(read_file("../app/data/passwords.json"))

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        print("order.py post_input", post_input)

        form_orders = json.loads(post_input)
        event_id = str(form_orders['event_id'])
        cca_order_id = str(form_orders['cca_order_id'])

        try:
            orders = json.loads(read_file(f"../app/orders/{event_id}.json"))
        except:
            orders = {}

        try:
            orders[cca_order_id]["paypal"] = form_orders
        except:
            rand_num = randint(1, 10000)
            orders[rand_num] = form_orders

        write_file(f"../app/orders/{event_id}.json", json.dumps(orders, indent=4))


        # VARIABLE-TIME STUFF:
        try:
            u = UpdateExtra(event_id, "", 0)
            u.set_via_purchase(form_orders['variable_time_slot'])
            u.update_extra()

            # Now rebuild the page so it reflects accurate inventory numbers
            r = requests.get(f'{domain}/app/build-individual-event?eid={event_id}', auth=(f'{user}', f'{passwd["catalystcreative"]}'))
            print("rebuilding", r.url)
            if r.status_code == 200:
                print(r.status_code)
                return r.text
            else:
                raise ValueError(f'get_page_contents fail: {path} {r.status_code}')
        except:
            print(f"NO VARIABLE TIME for {event_id}")


        ####
        try:
            payer_info = {
                "order_id": form_orders['orderID'],
                "event_id": form_orders['event_id'],
                "payer_email": form_orders['details']['payer']['email_address'],
                "payer_name": form_orders['details']['payer']['name']['given_name'],
                "amount": form_orders['details']['purchase_units'][0]['amount']['value']
            }
            print(payer_info)
        except:
            print('SOMETHING WENT WRONG WITH COLLECTING PAYER_INFO FROM FORM_ORDERS')
            payer_info = ''
        ####

        url = f"{domain}/email/submit"
        data = {"subject": "CCA Event purchase", "content": f"{json.dumps(orders, indent=4)}"}
        headers = {"Content-Type": "application/json"}
        r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd["catalystemail"]))
        print(r.status_code)

        generic_response = "generic response"
        if type(payer_info) == dict:
            try:
                print('attempt to send to payer')
                data = {"subject": "Thank you for your CCA Event purchase", "content": f"_hey_ _content_", "payer_info": f"{json.dumps(payer_info, indent=4)}"}
                headers = {"Content-Type": "text/html"}
                r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd["catalystemail"]))
                print("sendgrid resp status code", r.status_code)
                generic_reponse = "sendgrid response: {str(r.status_code)}"
            except:
                generic_reponse = "failed to communicate to payer by sendgrid email"
            print(generic_response)
        else:
            generic_response = "generic response"
            print('NO LUCK-- payer_info type is not dict')

        response = generic_reponse


    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/prep":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        form_prep = json.loads(post_input)
        event_id = str(form_prep['event_id'])
        cca_order_id = str(form_prep['cca_order_id'])
        cca_buyer_name = str(form_prep['cca_buyer_name'])
        cca_buyer_phone= str(form_prep['cca_buyer_phone'])

        try:
            orders = json.loads(read_file(f"../app/orders/{event_id}.json"))
        except:
            orders = {}

        orders[cca_order_id] = {}
        orders[cca_order_id]["cca_buyer_name"] = cca_buyer_name
        orders[cca_order_id]["cca_buyer_phone"] = cca_buyer_phone

        write_file(f"../app/orders/{event_id}.json", json.dumps(orders, indent=4))

        response = ""


    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/manual-add":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        i = json.loads(post_input)
        print("post_input", i)

        dbuser = "catalystcreative_cca"
        passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

        keys, vals = "", ""
        for k, v in i.items():
            keys += f"{k},"
            if k == "create_time":
                vals += f"NOW(),"
            else:
                vals += f"'{v}',"

        sql = f"INSERT INTO orders ({keys.rstrip(',')}) VALUES ({vals.rstrip(',')})"
        print("sql", sql)

        c = db.cursor()
        c.execute(sql)
        c.close()

        response = "OKEY DOKEY"


    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/manual-edit":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        i = json.loads(post_input)
        print("post_input", i)

        dbuser = "catalystcreative_cca"
        passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]
        db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

        oid = i["id"]
        print("oid", oid)

        update_string = ""
        for k, v in i.items():
            if k != "id" and k != "order_id" and k != "create_time":
                update_string += f"{k}='{v}',"

        sql = f"UPDATE orders SET {update_string.rstrip(',')} where id = {oid}"
        print("sql", sql)

        c = db.cursor()
        c.execute(sql)
        c.close()

        response = "OKEY DOKEY"


    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/paypal-webhook":

        # curl -X POST -H "Content-Type: application/json" --data '{"testing": "123"}' https://www.catalystcreativearts.com/order/paypal-webhook

        try:
            length = int(environ.get('CONTENT_LENGTH', '0'))
            post_input = environ['wsgi.input'].read(length).decode('UTF-8')
            i = json.loads(post_input)
            print("post_input from paypal-webhook", i)
            create_time = i["create_time"]
            write_file(f"webhook-receipts/{create_time}.json", json.dumps(i, indent=4))
            response = "POKEY DOKEY"
        except:
            print("post_input from paypal-webhook", "FAIL")
            response += f"<hr>{str(environ)}<hr>"


    else:
        response = "200"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]
