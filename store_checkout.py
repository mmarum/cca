import os
import re
import sys
import json
import stripe
import MySQLdb
from urllib.parse import unquote, urlencode
from jinja2 import Environment, PackageLoader, select_autoescape
sys.path.insert(0, os.path.dirname(__file__))


env = Environment(
    loader=PackageLoader('store_checkout', 'templates'),
    autoescape=select_autoescape(['html'])
)

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


def get_intent_shop(form_data):
    stripe.api_key = passwords["store_api_key_prod"]

    session_id = form_data["session_id"]
    product_names = form_data["product_names"]
    customer_name = form_data["customer_name"]
    customer_phone = form_data["customer_phone"]
    total_cost = form_data["total_cost"]

    total_cost = int(float(total_cost) * 100) # Stripe counts by cents

    return stripe.PaymentIntent.create(
        amount=total_cost,
        currency="usd",
        #automatic_payment_methods={"enabled": False},
        description=product_names,
        metadata=form_data,
        payment_method_types=["card"]
    )


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
                if "a href=" in value:
                    value = clean_href(value)
                form_data[name] = value

        # HTML FORM REQUIREMENTS:
        # event_id, event_title, event_date, guest_quantity
        # customer_name, customer_phone, total_cost
        
        # OPTIONAL IN HTML FORM:
        # additional_scarf, variable_price

        return form_data


def unquote_dict(form_data):
    new_dict = {}

    #print("unquote_dict() form_data", form_data)

    for k, v in form_data.items():
        v = v.replace("+", " ")
        if v != "":
            if "a href=" in v:
                v = clean_href(v)
            new_dict[k] = unquote(v)
    return new_dict


def store_checkout(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    #print("HTTP_REFERER", environ["HTTP_REFERER"])
    #print("REQUEST_METHOD", environ['REQUEST_METHOD'])
    #print("PATH_INFO", environ['PATH_INFO'])


    #### /store-checkout/ (start)
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/":
        if site not in environ["HTTP_REFERER"]:
            return ["Error. Invalid referer".encode()]
        # This view exists so that we can pass
        # form value data to the checkout screen
        form_data = filter_form_data(environ)
        print("/store-checkout form_data", form_data)
        template = env.get_template("store-checkout.html")
        response = template.render(form_data=form_data)


    #### /store-checkout/ (complete)
    elif environ['REQUEST_METHOD'].upper() == "GET" and environ['PATH_INFO'] == "/" \
        and "payment_intent_client_secret" in environ["QUERY_STRING"]:
        template = env.get_template("store-checkout.html")
        response = template.render()


    #### /store-checkout/create-payment-intent
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/create-payment-intent":
        if site not in environ["HTTP_REFERER"]:
            return ["Error. Invalid referer".encode()]
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        post_input_dict = json.loads(post_input)
        form_data = post_input_dict["items"]
        form_data = unquote_dict(form_data)
        print("/store-checkout/create-payment-intent form_data", form_data)
        #try:
        # form_data becomes the intent object metadata

        intent = get_intent_shop(form_data=form_data)

        #print("/store-checkout/create-payment-intent intent", intent)
        intent_data = {
            "clientSecret": intent["client_secret"]
        }
        return json.dumps(intent_data)
        #except Exception as e:
        #    print("ERROR in PaymentIntent.create()", str(e))
        #    response = str(e)


    ####
    else:

        response = f"<p>ERROR: environ values:</p>{str(environ)}"
        #response = f"<p>ERROR</p>"

    return [response.encode()]

