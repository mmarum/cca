import os
import sys
import json
import re
import base64

#import calendar
from paper_calendar import make_cal, make_list

import datetime
import random

#from datetime import date

# https://jinja.palletsprojects.com/en/2.10.x/api/
from jinja2 import Environment, PackageLoader, select_autoescape

from custom_filters import get_inventory

env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory

# TODO: Prevent SQL_injection

# https://wtforms.readthedocs.io/en/stable/index.html
from forms import ProductsForm, EventsForm, ImageForm, RegistrationForm, BookingForm

from os import listdir
from os.path import isfile, join

# https://pillow.readthedocs.io/en/stable/
from PIL import Image

# https://github.com/PyMySQL/mysqlclient-python
# https://mysqlclient.readthedocs.io/
# https://mysqlclient.readthedocs.io/user_guide.html#some-mysql-examples
import MySQLdb

from gallery import Gallery
from writer import scrape_and_write
import time
from update_extra import UpdateExtra


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


# mysql -u catalystcreative_cca catalystcreative_arts -p
dbuser = "catalystcreative_cca"
passwd = json.loads(read_file("data/passwords.json"))[dbuser]


def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    this_now = datetime.datetime.now()

    #today = date.today() #today.year, today.month, today.day

    pages = ["crafts-gallery", "gift-card", "private-events", "about-us", "media", "reviews", "custom-built", "after-school", "summer-camp", "art-camp", "3-wednesdays-workshop", "listening-room", "wheel-wars", "paint-wars"]

    pages.sort()

    #galleries_dict = {"acrylic-painting": 1, "watercolor-painting": 2, "paint-your-pet": 3, "fused-glass": 4, "resin-crafts": 5, "fluid-art": 6, "commissioned-art": 8, "alcohol-ink": 9, "artist-guided-family-painting": 10, "handbuilt-pottery": 11, "leathercraft": 12, "water-marbling": 13, "pottery-painting": 18, "string-art": 19, "pottery-lessons": 20}

    #mysql -u catalystcreative_cca catalystcreative_66
    #SELECT lower(name), id FROM piwigz_categories order by id asc;
    galleries_dict = {
    "acrylic-painting": 1,
    "watercolor-painting": 2,
    "paint-your-pet": 3,
    "fused-glass": 4,
    "resin-crafts": 5, # was "resin-art"
    "fluid-art": 6,
    "summer-art-camp": 7,
    "commissioned-art": 8,
    #"alcohol-ink": 9,
    "artist-guided-family-painting": 10,
    "handbuilt-pottery": 11,
    "leathercraft": 12,
    "water-marbling": 13,
    #"private-events": 14,
    #"custom-counter-tops-tables": 15,
    #"about-us": 16,
    "pottery-painting": 18,
    "string-art": 19,
    "pottery-lessons": 20
    }

    galleries_list = list(galleries_dict.keys())
    galleries_dict_vals = list(galleries_dict.values())

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

    global_settings = json.loads(read_file("data/global_settings.json"))

    ####
    ####
    if environ['REQUEST_METHOD'] == "GET":

        if environ['PATH_INFO'] == '/admin/events/list':
            c = db.cursor()
            c.execute(f"SELECT * FROM events WHERE edatetime >= CURDATE() ORDER BY edatetime")
            allrows = c.fetchall()
            c.close()
            template = env.get_template("admin-events-list.html")
            response = template.render(allrows=allrows)


        elif environ['PATH_INFO'] == '/admin/orders/list':
            db.query(f"select *, ceiling(ship_date / 10000000000000) as ship_group from cart_order where status = 'complete' order by ship_group, ship_date desc, checkout_date desc")
            #db.query(f"select * from cart_order where status = 'complete' order by ship_date desc, checkout_date desc") # and ship_date is NULL
            r = db.store_result()
            allrows = r.fetch_row(maxrows=100, how=1)

            new_allrows = []

            overall_total = 0
            per_month_totals = {}

            for row in allrows:
                cart_order_id = row["cart_order_id"]
                #db.query(f"select product_id, quantity from cart_order_product where cart_order_id = {cart_order_id}")

                try:
                    content = read_file(f"../cart-api/details/{cart_order_id}.json")
                    details = json.loads(content)
                    email = details["payer"]["email_address"]
                    address = details["purchase_units"][0]["shipping"]["address"]
                    given_name = details["payer"]["name"]["given_name"]
                    surname = details["payer"]["name"]["surname"]
                    name = f"{given_name} {surname}"
                    try:
                        phone = details["payer"]["phone"]["phone_number"]["national_number"]
                    except:
                        phone = ""
                except:
                    pass

                db.query(f"select a.product_id, a.quantity, b.name, b.inventory \
                    from cart_order_product a, products b \
                    where a.product_id = b.pid and cart_order_id = {cart_order_id}")
                r = db.store_result()
                sub_allrows = r.fetch_row(maxrows=100, how=1)
                row["products"] = sub_allrows

                try:
                    row["email"] = email
                    row["address"] = address
                    row["name"] = name
                    row["phone"] = phone
                except:
                    pass

                new_allrows.append(row)

                overall_total += int(row["total"])

                checkout_month = str(row["checkout_date"]).split("-")[1]

                try:
                    per_month_totals[checkout_month] += int(row["total"])
                except:
                    per_month_totals[checkout_month] = int(row["total"])

            template = env.get_template("admin-orders-list.html")
            response = template.render(allrows=new_allrows, 
                overall_total=overall_total, per_month_totals=per_month_totals)


        elif environ['PATH_INFO'] == '/admin/events/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                eid = environ['QUERY_STRING'].split("=")[1]
                db.query(f"SELECT * FROM events WHERE eid = {eid}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = EventsForm(**row)

                c = db.cursor()
                c.execute(f"SELECT * FROM events WHERE tags like '%series={eid}%'")
                children = c.fetchall()
                c.close()
            else:
                form = EventsForm()
                children = None
            template = env.get_template("admin-events-add-edit.html")
            response = template.render(form=form, children=children)


        elif environ['PATH_INFO'] == "/admin/events/delete":
            eid = int(environ['QUERY_STRING'].split("=")[1])
            if type(eid) == int:

                # FIRST UPDATE THE HTML PAGE !!!!
                db.query(f"SELECT * FROM events WHERE eid = {eid}")
                e = db.store_result()
                event = e.fetch_row(maxrows=1, how=1)[0]
                event["quantity_sum"] = 0
                event["remaining_spots"] = 0
                template = env.get_template("event.html")
                content = template.render(event=event, deleted=True)
                write_file(f"../www/event/{eid}.html", content)

                sql = f"DELETE FROM events WHERE eid = {eid}"
                c = db.cursor()
                c.execute(sql)
                c.close()

                response = '<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'
            else:
                response = ""


        #### ####
        #### ####
        elif environ['PATH_INFO'] == '/build-individual-event':
            if environ['QUERY_STRING']:
                eid = int(environ['QUERY_STRING'].split("=")[1])
                db.query(f"SELECT * FROM events WHERE eid = {eid}")
            else:
                db.query("SELECT * FROM events WHERE edatetime >= CURTIME() \
                    and (tags <> 'invisible' or tags is null) ORDER BY edatetime")
            e = db.store_result()
            allrows = e.fetch_row(maxrows=100, how=1)

            template = env.get_template("event.html")
            upcoming_event_ids = []
            for event in allrows:
                eid = event["eid"]
                elimit = event["elimit"]

                db.query(f"select sum(quantity) as quantity_sum from orders where eid = {eid}")
                q = db.store_result()
                quantity_sum = q.fetch_row(maxrows=1, how=1)[0]["quantity_sum"]

                try:
                    event["quantity_sum"] = int(quantity_sum)
                    event["remaining_spots"] = int(elimit) - int(quantity_sum)
                except:
                    event["quantity_sum"] = 0
                    event["remaining_spots"] = int(elimit)

                upcoming_event_ids.append(eid)
                content = template.render(event=event)
                write_file(f"../www/event/{eid}.html", content)
            write_file(f"data/upcoming_event_ids.json", json.dumps(upcoming_event_ids, indent=4))
            response = "build-individual-event"
        #### ####
        #### ####


        elif environ['PATH_INFO'] == '/list/events' or environ['PATH_INFO'] == '/calendar':

            db.query("SELECT * FROM events WHERE edatetime >= CURTIME() and (tags <> 'invisible' or tags is null) and tags NOT LIKE '%pottery-lesson%' ORDER BY edatetime")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=1000, how=1)

            db.query("SELECT eid, SUM(quantity) as sum_quantity FROM orders GROUP BY eid")
            # TODO: May need to add join to events table above
            # so as to only pull future event dates
            r = db.store_result()
            orders_count = r.fetch_row(maxrows=1000, how=1)

            orders_count_object = {}
            for item in orders_count:
                key = int(item['eid'])
                val = int(item['sum_quantity'])
                orders_count_object[key] = val

            events_object = {}
            parent = {}
            for row in allrows:
                eid = row["eid"]
                events_object[eid] = {}
                events_object[eid]["date"] = int(row["edatetime"].timestamp())
                events_object[eid]["title"] = row["title"]
                events_object[eid]["price"] = row["price"]
                events_object[eid]["price_text"] = row["price_text"]

                if "series" in row["tags"]:
                    parent[eid] = re.sub('^.*series=(\d+).*$', r'\1', row["tags"])
                else:
                    parent[eid] = ""

            events_object = json.dumps(events_object)

            try:
                test = environ['QUERY_STRING'].split("=")[1]
            except:
                test = ""

            template = env.get_template("list-events.html")
            response = template.render(events=allrows, 
                orders_count=orders_count_object, 
                events_object=events_object, 
                parent=parent, 
                test=test)


        ####

        elif environ['PATH_INFO'] == '/pottery-lessons':

            db.query("SELECT * FROM events WHERE edatetime >= CURTIME() and (tags <> 'invisible' or tags is null) and tags LIKE '%pottery-lesson%' ORDER BY edatetime ASC")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=1000, how=1)

            db.query("SELECT eid, SUM(quantity) as sum_quantity FROM orders GROUP BY eid")
            r = db.store_result()
            orders_count = r.fetch_row(maxrows=1000, how=1)

            orders_count_object = {}
            for item in orders_count:
                key = int(item['eid'])
                val = int(item['sum_quantity'])
                orders_count_object[key] = val

            events_object = {}
            for row in allrows:
                eid = row["eid"]
                events_object[eid] = {}
                events_object[eid]["date"] = int(row["edatetime"].timestamp())
                events_object[eid]["title"] = row["title"]
                events_object[eid]["price"] = row["price"]
                events_object[eid]["price_text"] = row["price_text"]

            events_object = json.dumps(events_object)

            template = env.get_template("pottery-lessons.html")
            response = template.render(events=allrows, 
                orders_count=orders_count_object, 
                events_object=events_object)

        ####


        elif environ['PATH_INFO'] == '/cart':
            template = env.get_template("cart-list.html")
            response = template.render()


        elif environ['PATH_INFO'] == '/products':
            db.query("SELECT * FROM products WHERE active = 1")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=100, how=1)
            template = env.get_template("list-products.html")
            response = template.render(products=allrows)


        elif re.match('/products/[a-z-]+/[0-9]+', environ['PATH_INFO']):
            path_parts = environ['PATH_INFO'].split('/')
            product_name = path_parts[2]
            product_id = path_parts[3]
            pid = int(product_id)
            db.query(f"SELECT * FROM products WHERE pid = {pid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            template = env.get_template("product-detail.html")
            response = template.render(row=row)


        elif environ['PATH_INFO'] == '/book/event':
            eid = environ['QUERY_STRING'].split("=")[1]
            db.query(f"SELECT * FROM events WHERE eid = {eid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]

            db.query(f"SELECT count(id) as cnt FROM orders WHERE eid = {eid}")
            o = db.store_result()
            order_count = o.fetch_row(maxrows=1, how=1)[0]["cnt"]

            template = env.get_template("book-event.html")
            response = template.render(event_data=row, order_count=order_count)


        elif environ['PATH_INFO'] == '/gallery/slideshow' or environ['PATH_INFO'].lstrip('/') in galleries_list:

            if environ['PATH_INFO'] == '/gallery/slideshow':
                gid = int(environ['QUERY_STRING'].split("=")[1])
            else:
                path_info = environ['PATH_INFO'].lstrip('/')
                gid = int(galleries_dict[path_info])

            try:
                g = Gallery(gid)
                gallery = g.get_gallery()
                images = g.get_images()

                template = env.get_template("gallery-slideshow.html")
                response = template.render(gallery=gallery, images=images)
            except:
                template = env.get_template("main.html")
                response = template.render(path_info=f"{path_info} gallery does not yet exist")


        ####
        elif environ['PATH_INFO'] == '/admin/booking/list':

            view = ""
            gtlt = ">=" # default
            ascdesc = "asc"

            if environ['QUERY_STRING'] and "view" in environ['QUERY_STRING']:
                view = environ['QUERY_STRING'].split("=")[1]

                if view == "past-events":
                    gtlt = "<"
                    ascdesc = "desc"

            # TODO: This first part should be call-able separately
            # And should be called about once per minute 

            # OR EVEN BETTER:
            # Maybe this chunk should be moved to the
            # /paypal-transaction-complete section

            # List, sort, then read all files in the orders/ folder
            files = [f for f in listdir("orders/") if isfile(join("orders/", f))]

            if len(files) > 0 and view != "past-events":
                # PART-1: Load new orders into database:
                # Reminder: Orders data files are saved as event_eid_value.json
                for f in files:
                    eid = f.replace(".json", "").strip()
                    event_orders_data = json.loads(read_file(f"orders/{f}"))

                    for cca_order_id, cca_order in event_orders_data.items():

                        try:
                            order = cca_order["paypal"]

                            #print("____cca_order_id", cca_order_id)
                            #print("____order", order)
                            data_array = []
                            # We don't necessarily want all data from orders/event_eid_value.json
                            # So let's pick and choose what data we want to keep:

                            data_array.append(order['orderID'])

                            data_array.append(eid)
                            data_array.append(order['details']['create_time'])
                            data_array.append(order['details']['payer']['email_address'])
                            data_array.append(order['details']['payer']['name']['given_name'])
                            data_array.append(order['details']['payer']['name']['surname'])
                            data_array.append(order['quantity'])
                            # Notice zero after purchase_units:
                            data_array.append(order['details']['purchase_units'][0]['amount']['value'])
                            data_array.append(order['details']['purchase_units'][0]['payments']['captures'][0]['amount']['value'])

                            # FOR VARIABLE_TIME FIELD
                            try:
                                data_array.append(order['variable_time_slot'])
                            except:
                                data_array.append('no variable time slot')

                            # FOR EXTRA_DATA FIELD
                            try:
                                total_number_scarf = json.dumps({ "total_number_scarf": int(order['total_number_scarf']) })
                                data_array.append(total_number_scarf)
                            except:
                                data_array.append('not an event with scarf')

                            try:
                                data_array.append(order["details"]["purchase_units"][0]["payments"]["captures"][0]["id"])
                            except:
                                data_array.append("transaction id")

                            data_array.append(cca_order["cca_buyer_name"])
                            data_array.append(cca_order["cca_buyer_phone"])

                            # Load database:
                            fields = "order_id, eid, create_time, email, first_name, last_name, quantity, cost, paid, variable_time, extra_data, transaction_id, buyer_name, buyer_phone"
                            #vals = str(data_array).lstrip('[').rstrip(']')
                            vals = data_array
                            #sql = f"INSERT INTO orders ({fields}) VALUES ({vals})"
                            sql = f"INSERT INTO orders ({fields}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

                            c = db.cursor()
                            #c.execute(sql)
                            c.execute(sql, vals)
                            c.close()

                        except:
                            pass

                    # So that this event json doesn't get processed again:
                    try:
                        # If existing json for this event exists, add new json to it:
                        event_dict = json.loads(read_file(f"orders/loaded/{f}"))
                        event_dict.update(event_orders_data)
                        write_file(f"orders/loaded/{f}", json.dumps(event_dict, indent=4))
                        # REMOVE the file
                        os.remove(f"orders/{f}")
                    except:
                        # MOVE the file to /orders/loaded/event_eid_value.json
                        os.rename(f"orders/{f}", f"orders/loaded/{f}")

            # PART-2: Select future-event-date orders from database for admin view
            #c = db.cursor()
            query = f"SELECT e.title, e.edatetime, e.elimit, o.* \
                FROM events e, orders o WHERE e.eid = o.eid AND e.edatetime {gtlt} CURDATE() ORDER BY e.edatetime {ascdesc}"
            #c.execute(query)
            #allrows = c.fetchall()
            #c.close()

            # NOTE: changing from db.cursor / c.execute to db.query / db.store_result for use of dict in template

            db.query(query)
            r = db.store_result()
            allrows = r.fetch_row(maxrows=1000, how=1)

            # GROUP BY EVENT ID:
            new_booking_dict = {}

            for row in allrows:

                eid = row["eid"]
                title = row["title"]
                date = row["edatetime"]

                try:
                    # EVENT EXISTS IN DICT ALREADY:
                    new_booking_dict[eid]["booking"].append(row)

                except:
                    # EVENT DOES NOT YET EXIST IN DICT:
                    new_booking_dict[eid] = {}
                    new_booking_dict[eid]["id"] = eid
                    new_booking_dict[eid]["title"] = title
                    new_booking_dict[eid]["date"] = date
                    new_booking_dict[eid]["booking"] =  []
                    new_booking_dict[eid]["booking"].append(row)

 

            template = env.get_template("admin-booking-list.html")
            response = template.render(orders=allrows, new_booking_dict=new_booking_dict)


        ####
        elif environ['PATH_INFO'] == '/admin/booking/add-edit':

            c = db.cursor()
            c.execute(f"SELECT * FROM events WHERE edatetime > CURTIME() order by edatetime asc")
            allevents = c.fetchall()
            c.close()

            if len(environ['QUERY_STRING']) > 1:
                order_id = environ['QUERY_STRING'].split("=")[1]
                db.query(f"SELECT * FROM orders WHERE id = {order_id}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = BookingForm(**row)
            else:
                form = BookingForm()

            template = env.get_template("admin-booking-add-edit.html")
            response = template.render(form=form, allevents=allevents, this_now=this_now)


        elif environ['PATH_INFO'] == '/home':
            # UP-NEXT EVENT
            month = int(this_now.strftime("%m"))
            year = int(this_now.strftime("%Y"))
            html_cal = make_cal(db, month, year)

            #print(html_cal)

            db.query(f"SELECT * FROM events WHERE edatetime > CURTIME() \
                and (tags <> 'invisible' or tags is null) \
                and title != 'Private Event' \
                and description not like '%Private Event%' \
                and title not like '%Studio Closed%' \
                and title != 'Studio Closed' \
                and tags NOT LIKE '%pottery-lesson%' \
                ORDER BY edatetime limit 1")
            r = db.store_result()
            next_event = r.fetch_row(maxrows=1, how=1)[0]
            #html_cal = ""
            #next_event = ""

            # FEATURED / PINNED EVENTS
            db.query(f"SELECT * FROM events WHERE edatetime > CURTIME() and tags = 'home' and tags NOT LIKE '%pottery-lesson%' ORDER BY edatetime limit 10")
            r = db.store_result()
            events_tagged_home = r.fetch_row(maxrows=10, how=1)

            # RANDOM PRODUCT
            db.query(f"select pid, name, image_path_array, price from products where inventory > 0 and active = 1 ORDER BY RAND() LIMIT 1")
            r = db.store_result()
            random_product = r.fetch_row(maxrows=10, how=1)[0]

            # GALLERY / SLIDESHOW
            #random_number = random.randint(1,len(galleries_dict))
            random_number = random.choice(galleries_dict_vals)
            g = Gallery(random_number)
            gallery = g.get_gallery()
            images = g.get_images()

            # Event List:
            event_list_html = make_list(db)

            template = env.get_template("home.html")
            response = template.render(next_event=next_event, calendar={"html": html_cal}, 
                events_tagged_home=events_tagged_home, gallery=gallery, images=images, 
                event_list_html=event_list_html, random_product=random_product,
                global_settings=global_settings)


        elif environ['PATH_INFO'] == '/admin/pages':
            template = env.get_template("admin-pages.html")
            if environ['QUERY_STRING']:
                page_name = environ['QUERY_STRING'].split("=")[1]
                try:
                    page_content = read_file(f"data/{page_name}.html")
                except:
                    page_content = None
                response = template.render(page_name=page_name, page_content=page_content)
            else:
                response = template.render(pages=pages)


        elif environ['PATH_INFO'] == '/admin/registration':
            #c = db.cursor()
            #c.execute("SELECT * FROM registration ORDER BY session_detail")
            #allrows = c.fetchall()
            #c.close()

            view = ""
            if environ['QUERY_STRING'] and "view" in environ['QUERY_STRING']:
                view = environ['QUERY_STRING'].split("=")[1]

            if view == "all":
                special = ""
                orderby = "order_id, session_detail"
            else:
                special = "AND order_id is not NULL"
                orderby = "session_detail"

            db.query(f"SELECT * FROM registration where session_detail LIKE '%2023%' {special} ORDER BY {orderby}")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=100, how=1)

            #data = json.loads(read_file("../registration/data/wheel-wars.json"))
            data = json.loads(read_file("../registration/data/paint-wars.json"))


            # GROUP BY CAMP:
            new_reg_dict = {}

            for row in allrows:

                sd = row["session_detail"]

                try:
                    # REG EXISTS IN DICT ALREADY:
                    new_reg_dict[sd].append(row)

                except:
                    # REG DOES NOT YET EXIST IN DICT:
                    new_reg_dict[sd] = []
                    new_reg_dict[sd].append(row)

            template = env.get_template("admin-registration.html")
            response = template.render(allrows=allrows, data=data, new_reg_dict=new_reg_dict)


        #elif environ['PATH_INFO'] == '/admin/registration2':
        #    data = json.loads(read_file("../registration/data/wheel-wars.json"))
        #    template = env.get_template("admin-registration2.html")
        #    response = template.render(data=data)


        elif environ['PATH_INFO'] == '/summer-camp-registration':
            template = env.get_template("summer-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)


        elif environ['PATH_INFO'] == '/art-camp-registration':
            template = env.get_template("art-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)


        elif environ['PATH_INFO'].lstrip('/') in pages:
            page_name = environ['PATH_INFO'].lstrip('/')
            page_content = str(read_file(f"data/{page_name}.html"))

            # TODO: I need to rethink how pages are managed

            if page_name == "gift-card":
                template = env.get_template("gift-card.html")
            else:
                template = env.get_template("pages.html")
            response = template.render(page_name=page_name, page_content=page_content)


        elif environ['PATH_INFO'] == '/admin/products/list':
            c = db.cursor()
            c.execute("SELECT * FROM products order by pid desc")
            allrows = c.fetchall()
            c.close()
            template = env.get_template("admin-products-list.html")
            response = template.render(allrows=allrows, global_settings=global_settings)


        elif environ['PATH_INFO'] == '/admin/products/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                pid = environ['QUERY_STRING'].split("=")[1]
                db.query(f"SELECT * FROM products WHERE pid = {pid}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = ProductsForm(**row)
            else:
                form = ProductsForm()
            template = env.get_template("admin-products-add-edit.html")
            response = template.render(form=form)


        elif environ['PATH_INFO'] == '/admin/products/delete':
            if len(environ['QUERY_STRING']) > 1:
                pid = int(environ['QUERY_STRING'].split("=")[1])
                sql = f"DELETE FROM products WHERE pid = {pid}"
                c = db.cursor()
                c.execute(sql)
                c.close()
                sql = f"DELETE FROM cart_order_product WHERE product_id = {pid}"
                c = db.cursor()
                c.execute(sql)
                c.close()
                response = '<meta http-equiv="refresh" content="0; url=/app/admin/products/list" />'
            else:
                response = ""


        else:
            path_info = environ['PATH_INFO'].lstrip('/')
            template = env.get_template("main.html")
            response = template.render(path_info=path_info)

    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/paypal-transaction-complete":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        form_orders = json.loads(post_input)
        event_id = str(form_orders['event_id'])

        try:
            orders = json.loads(read_file(f"orders/{event_id}.json"))
        except:
            orders = []

        orders.append(form_orders)
        write_file(f"orders/{event_id}.json", json.dumps(orders, indent=4))
        response = "200"

        #scrape_and_write("calendar")


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/product-image/upload":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        # NOTICE: NOT DECODING post_input below FOR IMAGES
        post_input = environ['wsgi.input'].read(length)
        # NOTICE: BYTES STRING below FOR IMAGES
        image_pid = post_input.split(b'Content-Disposition: form-data')[1]
        pid = re.sub(b'^.*name="pid"(.*?)------.*$', r"\1", image_pid, flags=re.DOTALL).strip()
        pid = int(pid.decode('UTF-8'))
        image_data = post_input.split(b'Content-Disposition: form-data')[2]
        image_filename = re.sub(b'^.*filename="(.*?)".*$', r"\1", image_data, flags=re.DOTALL).strip()
        image_contents = re.sub(b'^.*Content-Type: image/jpeg(.*)$', r"\1", image_data, flags=re.DOTALL).strip()
        img_name = image_filename.decode('UTF-8')
        open(f"../www/img/orig/{img_name}", 'wb').write(image_contents)
        size = 350, 350
        image = Image.open(f"../www/img/orig/{img_name}")
        image.thumbnail(size)
        image.save(f"../www/img/small/{img_name}", 'JPEG')
        sql = f"UPDATE products SET image_path_array = concat(ifnull(image_path_array,''), ',{img_name}') WHERE pid = {pid}"
        c = db.cursor()
        c.execute(sql)
        c.close()
        response = f'<meta http-equiv="refresh" content="0; url=/app/admin/products/list" />'


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/image/upload":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        # NOTICE: NOT DECODING post_input below FOR IMAGES
        post_input = environ['wsgi.input'].read(length)

        #print(post_input)

        # NOTICE BYTES STRING below FOR IMAGES
        image_eid = post_input.split(b'Content-Disposition: form-data')[1]
        eid = re.sub(b'^.*name="eid"(.*?)------.*$', r"\1", image_eid, flags=re.DOTALL).strip()
        eid = int(eid.decode('UTF-8'))
        image_data = post_input.split(b'Content-Disposition: form-data')[2]
        image_filename = re.sub(b'^.*filename="(.*?)".*$', r"\1", image_data, flags=re.DOTALL).strip()
        image_contents = re.sub(b'^.*Content-Type: image/jpeg(.*)$', r"\1", image_data, flags=re.DOTALL).strip()
        img_name = image_filename.decode('UTF-8')
        if img_name and image_contents:
            open(f"../www/img/orig/{img_name}", 'wb').write(image_contents)
            size = 350, 350
            image = Image.open(f"../www/img/orig/{img_name}")
            image.thumbnail(size)
            image.save(f"../www/img/small/{img_name}", 'JPEG')
            sql = f"UPDATE events SET image = '{img_name}' WHERE eid = {eid}"
            c = db.cursor()
            c.execute(sql)
            c.close()
        response = f'<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/contact":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data_object = json.loads(read_file("data/contactus.json"))

        post_input_array = post_input.split('------')

        message_object = {}
        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit":
                message_object[post_data_key] = post_data_val

            data_object[str(this_now)] = message_object

        email = data_object[str(this_now)]["email"]

        write_file(f"data/contactus.json", json.dumps(data_object, indent=4))

        #template = env.get_template("about-us.html")
        #response = template.render(thanks=data_object[str(this_now)])

        page_content = str(read_file(f"data/about-us.html"))
        template = env.get_template("pages.html")
        page_name = "about-us"
        response = template.render(page_name=page_name, page_content=page_content, email=email)


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/admin/pages":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        post_input_array = post_input.split('------')

        data_object = {}
        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit":
                data_object[post_data_key] = post_data_val

        page_name = data_object['page_name']
        page_content = data_object['page_content']

        # Backup current version just in case cuz why not
        os.rename(f"data/{page_name}.html", f"data/{page_name}.html.bak")

        try:
            write_file(f"data/{page_name}.html", page_content)
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/pages"/>'
        except:
            os.rename(f"data/{page_name}.html.bak", f"data/{page_name}.html")
            response = "ERROR WRITING PAGE <a href='/app/admin/pages'>Go back</a>"

        scrape_and_write(page_name)


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/admin/products/add-edit":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data_object = {}
        data_array = []

        post_input_array = post_input.split('------')

        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit" and not post_data_val.startswith('-----'):
                data_object[post_data_key] = post_data_val
                data_array.append(post_data_val)

        try:
            if int(data_object['pid']) > 0:
                action = "Update"
                pid = data_object['pid']
            else:
                action = "Insert"
        except:
            action = "Insert"

        # Cleanup: Remove "pid"
        del data_object['pid']
        del data_array[0]

        # Todo: More validation
        products_form = ProductsForm(**data_object)

        # Set query based on update vs insert
        if action == "Update":
            keys_vals = ""
            for k, v in data_object.items():
                v = v.replace("'", "''")
                keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')
            sql = f"UPDATE products SET {keys_vals} WHERE pid = {pid}"
            #print(sql)
            c = db.cursor()
            c.execute(sql)
        else:
            fields = "name, description, image_path_array, inventory, price, keywords_array, active"
            vals = data_array
            sql = f"INSERT INTO products ({fields}) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            c = db.cursor()
            c.execute(sql, vals)
        c.close()

        # Next template needs to know the pid
        if action == "Insert":
            # Now retrieve the pid from the item we just added
            n = data_object['name']
            p = data_object['price']
            sql2 = f"SELECT pid FROM products WHERE name = '{n}' AND price = '{p}'"
            #print(sql2)
            d = db.cursor()
            d.execute(sql2)
            results = d.fetchone()
            pid = int(results[0])
            d.close()
        else:
            sql2 = "just an update"

        image_form = ImageForm()

        template = env.get_template("admin-products-image.html")
        response = template.render(product_data=data_object, image_form=image_form,
            sql={"sql":sql}, pid={"pid":pid}, sql2={"sql2":sql2})


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST":

        #print("HERE AAA")

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        #print("post_input", post_input)

        data_object = {}
        data_array = []

        post_input_array = post_input.split('------')

        #with open("stderr.log", "a") as logfile:
        #    logfile.write(str(f"++++{post_input}++++"))

        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and "submit" not in post_data_key and not post_data_val.startswith('-----'):
                data_object[post_data_key] = post_data_val
                data_array.append(post_data_val)

        #print("data_object", data_object)
        #print("data_array", data_array)


        # TEMPORARILY removing series input data
        #data_object_temp = data_object
        #for k, v in data_object_temp.items():
        #    if "series" in k:
        #        del data_object[k]


        # If form passes an eid value then query
        # is an update as opposed to an insert

        try:
            if int(data_object['eid']) > 0:
                action = "Update"
                eid = data_object['eid']
            else:
                action = "Insert"
        except:
            action = "Insert"

        # Cleanup: Remove "eid"
        del data_object['eid']
        del data_array[0]

        # Cleanup: Remove "append_time"
        del data_object['append_time']
        del data_array[1]

        # For the variable-field stuff:
        price_text = data_object["price_text"]
        elimit = data_object["elimit"]

        # Todo: More validation
        events_form = EventsForm(**data_object)

        # Set query based on update vs insert
        if action == "Update":
            keys_vals = ""
            for k, v in data_object.items():
                v = v.replace("'", "''")
                keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')
            sql = f"UPDATE events SET {keys_vals} WHERE eid = {eid}"

            c = db.cursor()
            c.execute(sql)
            #c.execute(sql, vals)


        else:
            # fields MUST match keys coming in via "data_array":
            fields = "edatetime, title, duration, price, elimit, location, image, description, price_text, tags, extra_data"
            #vals = str(data_array).lstrip('[').rstrip(']')
            vals = data_array
            #sql = f"INSERT INTO events ({fields}) VALUES ({vals})"
            # Number of items (%s) MUST match num of vals coming in via "data_array":
            sql = f"INSERT INTO events ({fields}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

            c = db.cursor()
            #c.execute(sql)
            c.execute(sql, vals)


        c.close()

        # Next template needs to know the eid
        if action == "Insert":
            # Now retrieve the eid from the item we just added
            e = data_object['edatetime']
            t = data_object['title'].replace("'", "''")
            sql2 = f"SELECT eid, price_text, elimit FROM events WHERE edatetime = '{e}' AND title = '{t}'"
            #print("____", sql2)
            d = db.cursor()
            d.execute(sql2)
            results = d.fetchone()
            #print("____results", results)
            #print("____type of results", type(results))
            eid = int(results[0])
            try:
                price_text = results[1]
            except:
                price_text = ""
            try:
                elimit = int(results[2])
            except:
                elimit = ""
            d.close()


            #
            # TESTING THE NEW VARIABLE-TIME STUFF:
            if "am" in price_text or "pm" in price_text:
                u = UpdateExtra(eid, price_text, elimit)
                u.set_via_admin()
                u.update_extra()
            #


        else:
            sql2 = "just an update"



        image_form = ImageForm()

        template = env.get_template("admin-events-image.html")
        response = template.render(event_data=data_object, image_form=image_form,
            sql={"sql":sql}, eid={"eid":eid}, sql2={"sql2":sql2})

        #scrape_and_write("calendar")
        #time.sleep(2)
        #scrape_and_write("home")

    ####
    ####
    else:
        response = "error"

    #response += f"<hr>{str(environ)}"

    db.close()

    return [response.encode()]

