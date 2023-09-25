import os
import io
import re
import sys
import json
import stripe
import MySQLdb
sys.path.insert(0, os.path.dirname(__file__))


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


passwords = json.loads(read_file("../app/data/passwords.json"))
dbname = "catalystcreative_arts"
dbuser = "catalystcreative_cca"
dbpass = passwords[dbuser]
site = "https://www.catalystcreativearts.com"


stripe.api_key = passwords["stripe_api_key_prod"]
endpoint_secret = passwords["stripe_webhook_secret"]


def insert_event_db(data):
    transaction_id = data["id"]
    email = data["receipt_email"]
    amount_received = data["amount_received"]
    paid = str(int(amount_received / 100)) + ".00"
    metadata = data["metadata"]
    event_id = metadata.get("event_id", "")
    quantity = metadata.get("guest_quantity", "")
    customer_name = metadata.get("customer_name", "")
    customer_phone = metadata.get("customer_phone", "")
    variable_price = metadata.get("variable_price", "")
    additional_scarf = metadata.get("additional_scarf", "")

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=dbpass, db=dbname)
    sql = f"insert into orders (order_id, eid, create_time, email, quantity, paid, variable_time, extra_data, transaction_id, buyer_name, buyer_phone) \
        values ('{transaction_id}', '{event_id}', NOW(), '{email}', '{quantity}', '{paid}', '{variable_price}', '{additional_scarf}', '{transaction_id}', '{customer_name}', '{customer_phone}')"
    print("sql", sql)
    c = db.cursor()
    c.execute(sql)
    c.close()


def insert_reg_db(data):

    order_id = data["id"]
    parent_email = data["receipt_email"]
    amount_received = data["amount_received"]
    paid = str(int(amount_received / 100)) + ".00"
    metadata = data["metadata"]

    event_id = metadata.get("event_id", "")
    quantity = metadata.get("guest_quantity", "")
    customer_name = metadata.get("customer_name", "")
    customer_phone = metadata.get("customer_phone", "")
    
    camper1_name = metadata.get("camper1_name", "")
    camper2_name = metadata.get("camper2_name", "")
    camper3_name = metadata.get("camper3_name", "")
    camper1_age = metadata.get("camper1_age", "")
    camper2_age = metadata.get("camper2_age", "")
    camper3_age = metadata.get("camper2_age", "")
    parent_address = metadata.get("parent_address", "")
    parent_city = metadata.get("parent_city", "")
    parent_state = metadata.get("parent_state", "")
    parent_zip = metadata.get("parent_zip", "")
    parent_em_name = metadata.get("parent_em_name", "")
    parent_em_phone = metadata.get("parent_em_phone", "")
    pickup1_name = metadata.get("pickup1_name", "")
    pickup1_phone = metadata.get("pickup1_phone", "")
    pickup2_name = metadata.get("pickup2_name", "")
    pickup2_phone = metadata.get("pickup2_phone", "")
    session_detail = metadata.get("session_detail", "")

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=dbpass, db=dbname)
    sql = f"insert into registration (order_id, camper1_name, camper1_age, camper2_name, camper2_age, camper3_name, camper3_age, parent_name, \
        parent_address, parent_city, parent_state, parent_zip, parent_email, parent_phone, parent_em_name, parent_em_phone, pickup1_name, pickup1_phone, pickup2_name, pickup2_phone, session_detail) \
        values ('{order_id}', '{camper1_name}', '{camper1_age}', '{camper2_name}', '{camper2_age}', '{camper3_name}', '{camper3_age}', \
        '{customer_name}', '{parent_address}', '{parent_city}', '{parent_state}', '{parent_zip}', '{parent_email}', '{customer_phone}', '{parent_em_name}', '{parent_em_phone}', '{pickup1_name}', \
        '{pickup1_phone}', '{pickup2_name}', '{pickup2_phone}', '{session_detail}')"
    print("sql", sql)
    c = db.cursor()
    c.execute(sql)
    c.close()


def wrapper(response):
    response = json.dumps(response, indent=4)
    return [response.encode()]


def webhook(environ, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    #print("HTTP_REFERER", environ["HTTP_REFERER"])
    #print("REQUEST_METHOD", environ['REQUEST_METHOD'])
    #print("PATH_INFO", environ['PATH_INFO'])

    #### 
    if environ['REQUEST_METHOD'].upper() == "POST" and environ['PATH_INFO'] == "/":

        #print("POST environ", environ)
        length = int(environ.get('CONTENT_LENGTH', '0'))
        payload = environ['wsgi.input'].read(length).decode('UTF-8')
        #print("payload", payload)
        event = None

        try:
            event = json.loads(payload)
        except:
            print('Webhook error while parsing basic request')
            response = { "success": "False" }
            return wrapper(response)

        if endpoint_secret:
            sig_header = environ['HTTP_STRIPE_SIGNATURE']
            #print("sig_header", sig_header)
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, endpoint_secret
                )
                print('Webhook signature verification success')
            except stripe.error.SignatureVerificationError as e:
                print('Webhook signature verification failed. ' + str(e))
                response = { "success": "False" }
                return wrapper(response)

        # Handle the event
        if event and event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']  # contains a stripe.PaymentIntent
            print('Payment for {} succeeded'.format(payment_intent['amount']))

            event_title = payment_intent["metadata"]["event_title"]

            print("Handle the event: event_title", event_title)

            if event_title == "Art Camp Registration 2023":
                insert_reg_db(payment_intent)
            else:
                insert_event_db(payment_intent)

        else:
            print('Unexpected event type {}'.format(event['type']))

        response = { "success": "True" }


    ####
    elif environ['REQUEST_METHOD'].upper() == "GET" and environ['PATH_INFO'] == "/":

        print(environ)


    return wrapper(response)

