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
    loader=PackageLoader('checkout', 'templates'),
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


def get_intent(form_data):
    stripe.api_key = passwords["stripe_api_key_prod"]

    event_title = form_data["event_title"]
    event_date = form_data["event_date"]
    description = f"{event_title} {event_date}"

    if "Art Camp Registration" in event_title:
        calculated_amount = calculate_reg_amount(form_data)
    else:
        calculated_amount = calculate_order_amount(form_data)

    return stripe.PaymentIntent.create(
        amount=calculated_amount,
        currency="usd",
        #automatic_payment_methods={"enabled": False},
        description=description,
        metadata=form_data,
        payment_method_types=["card"]
    )


def clean_text(text):
    return text.replace(";", "")


def calculate_reg_amount(form_data):
    """
    $230 per camper. $210 per additional sibling.
    """

    guest_quantity = int(form_data["guest_quantity"])
    print("guest_quantity", guest_quantity)
    total_cost = int(form_data["total_cost"])
    print("total_cost", total_cost)

    if guest_quantity == 1:
        return int(230 * 100) # Stripe counts by cents

    elif guest_quantity == 2:
        return int(440 * 100)

    elif guest_quantity == 3:
        return int(650 * 100)



def calculate_order_amount(form_data):
    """
    calculate_order_amount() should do:

    1) take event_id plus any other event options 
    (guest_quantity, variable_price, additional_scarf) 
    and figure out a price from the database

    2) compare that ^^ price to the price passed in the form. 
    If they're equal, it passes sanity check, 
    and that is the price returned by the function.
    """

    # Required:
    event_id = int(form_data["event_id"])
    print("event_id", event_id)
    guest_quantity = int(form_data["guest_quantity"])
    print("guest_quantity", guest_quantity)
    total_cost = int(form_data["total_cost"])
    print("total_cost", total_cost)

    # Optional:
    try:
        variable_price = clean_text(form_data["variable_price"])
    except:
        variable_price = ""
    print("variable_price", variable_price)

    try:
        additional_scarf = int(form_data["additional_scarf"])
    except:
        additional_scarf = ""
    print("additional_scarf", additional_scarf)

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=dbpass, db=dbname)
    sql = f"select price, price_text from events where eid = {event_id}"
    print("sql", sql)
    db.query(sql)
    r = db.store_result()
    row = r.fetch_row(maxrows=1, how=1)
    print("row", row)

    price_from_db = int(row[0]["price"])
    print("price_from_db", price_from_db)

    price_text_from_db = row[0]["price_text"] #.replace("@", " ")
    print("price_text_from_db", price_text_from_db)

    # variable_price:
    if price_text_from_db != "":
        if variable_price in price_text_from_db:
            var_price = int(variable_price.split("$")[1])
            print("var_price", var_price)
            if int(var_price * guest_quantity) == total_cost:
                return int(total_cost * 100) # Stripe counts by cents
            else:
                raise Exception("var_price (from form) DOES NOT EQUAL total_from_db")
        else:
            raise Exception("variable_price (from form) IS NOT IN price_text_from_db")

    # additional_scarf:
    elif additional_scarf != "":
        total_minus_extras_from_db = int(price_from_db * guest_quantity)

        extra_scarf_cost = 30

        extra_costs_subtotal = int(additional_scarf * extra_scarf_cost)
        total_with_extra_scarf = total_minus_extras_from_db + extra_costs_subtotal
        print("total_with_extra_scarf", total_with_extra_scarf)
        if total_cost == total_with_extra_scarf:
            return int(total_with_extra_scarf * 100) # Stripe counts by cents
        else:
            raise Exception("total_cost (from form) DOES NOT EQUAL total_with_extra_scarf (extra scarves)")

    # all others:
    else:
        total_from_db = int(price_from_db * guest_quantity)
        print("total_from_db", total_from_db)
        if total_cost == total_from_db:
            return int(total_from_db * 100) # Stripe counts by cents
        else:
            raise Exception("total_cost (from form) DOES NOT EQUAL total_from_db")


def clean_href(v):
    v = v.replace("</a>", "")
    v = re.sub("<a href=.*?>", "", v)
    return v


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


def checkout(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    #print("HTTP_REFERER", environ["HTTP_REFERER"])
    #print("REQUEST_METHOD", environ['REQUEST_METHOD'])
    #print("PATH_INFO", environ['PATH_INFO'])


    #### /checkout/ (start)
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/":
        if site not in environ["HTTP_REFERER"]:
            return ["Error. Invalid referer".encode()]
        # This view exists so that we can pass
        # form value data to the checkout screen
        form_data = filter_form_data(environ)
        print("/checkout form_data", form_data)
        template = env.get_template("checkout.html")
        response = template.render(form_data=form_data)


    #### /checkout/ (complete)
    elif environ['REQUEST_METHOD'].upper() == "GET" and environ['PATH_INFO'] == "/" \
        and "payment_intent_client_secret" in environ["QUERY_STRING"]:
        print("/checkout/ (complete)")
        template = env.get_template("checkout.html")
        response = template.render()


    #### /checkout/create-payment-intent
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/create-payment-intent":
        if site not in environ["HTTP_REFERER"]:
            return ["Error. Invalid referer".encode()]
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        post_input_dict = json.loads(post_input)
        form_data = post_input_dict["items"]
        form_data = unquote_dict(form_data)
        print("/checkout/create-payment-intent form_data", form_data)
        #try:
        # form_data becomes the intent object metadata

        intent = get_intent(form_data=form_data)

        #print("/checkout/create-payment-intent intent", intent)
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

