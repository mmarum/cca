import os
import sys
import json
import re
import base64

#import calendar
from paper_calendar import make_cal

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
from forms import ProductsForm, EventsForm, ImageForm, RegistrationForm

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

    pages = ["private-events", "about-us", "custom-built", "after-school", "summer-camp", "wheel-wars", "3-wednesdays-workshop"]

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
    "alcohol-ink": 9,
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

    ####
    ####
    if environ['REQUEST_METHOD'] == "GET":

        if environ['PATH_INFO'] == '/admin/events/list':
            c = db.cursor()
            c.execute("SELECT * FROM events WHERE edatetime >= CURDATE() ORDER BY edatetime")
            allrows = c.fetchall()
            c.close()
            template = env.get_template("admin-events-list.html")
            response = template.render(allrows=allrows)


        elif environ['PATH_INFO'] == '/admin/events/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                eid = environ['QUERY_STRING'].split("=")[1]
                db.query(f"SELECT * FROM events WHERE eid = {eid}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = EventsForm(**row)
            else:
                form = EventsForm()
            template = env.get_template("admin-events-add-edit.html")
            response = template.render(form=form)


        elif environ['PATH_INFO'] == "/admin/events/delete":
            eid = int(environ['QUERY_STRING'].split("=")[1])
            if type(eid) == int:
                sql = f"DELETE FROM events WHERE eid = {eid}"
                c = db.cursor()
                c.execute(sql)
                c.close()
                response = '<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'
            else:
                response = ""


        elif environ['PATH_INFO'] == '/list/events' or environ['PATH_INFO'] == '/calendar':

            db.query("SELECT * FROM events WHERE edatetime >= CURTIME() and (pinned <> 'invisible' or pinned is null) ORDER BY edatetime")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=100, how=1)

            db.query("SELECT eid, SUM(quantity) as sum_quantity FROM orders GROUP BY eid")
            # TODO: May need to add join to events table above
            # so as to only pull future event dates
            r = db.store_result()
            orders_count = r.fetch_row(maxrows=100, how=1)

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

            try:
                test = environ['QUERY_STRING'].split("=")[1]
            except:
                test = ""

            template = env.get_template("list-events.html")
            response = template.render(events=allrows, 
                orders_count=orders_count_object, events_object=events_object, 
                test=test)


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
        elif environ['PATH_INFO'] == '/admin/booking':

            view = ""
            gtlt = ">=" # default

            if environ['QUERY_STRING'] and "view" in environ['QUERY_STRING']:
                view = environ['QUERY_STRING'].split("=")[1]

                if view == "past-events":
                    gtlt = "<"

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

                    for order in event_orders_data:
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
                        data_array.append(order['variable_time_slot'])

                        # Load database:
                        fields = "order_id, eid, create_time, email, first_name, last_name, quantity, cost, paid, variable_time"
                        #vals = str(data_array).lstrip('[').rstrip(']')
                        vals = data_array
                        #sql = f"INSERT INTO orders ({fields}) VALUES ({vals})"
                        sql = f"INSERT INTO orders ({fields}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

                        c = db.cursor()
                        #c.execute(sql)
                        c.execute(sql, vals)
                        c.close()

                    # Now move the file to /orders/loaded/event_eid_value.json
                    # So that it doesn't get processed again
                    os.rename(f"orders/{f}", f"orders/loaded/{f}")

            # PART-2: Select future-event-date orders from database for admin view
            c = db.cursor()
            c.execute(f"SELECT e.title, e.edatetime, e.elimit, o.* FROM events e, orders o WHERE e.eid = o.eid AND e.edatetime {gtlt} CURDATE() ORDER BY e.edatetime")
            allrows = c.fetchall()
            c.close()

            template = env.get_template("admin-booking.html")
            response = template.render(orders=allrows)


        elif environ['PATH_INFO'] == '/home':
            # UP-NEXT EVENT
            month = int(this_now.strftime("%m"))
            year = int(this_now.strftime("%Y"))
            html_cal = make_cal(db, month, year)

            #print(html_cal)

            db.query(f"SELECT * FROM events WHERE edatetime > CURTIME() and (pinned <> 'invisible' or pinned is null) ORDER BY edatetime limit 1")
            r = db.store_result()
            next_event = r.fetch_row(maxrows=1, how=1)[0]
            #html_cal = ""
            #next_event = ""

            # FEATURED / PINNED EVENTS
            db.query(f"SELECT * FROM events WHERE edatetime > CURTIME() and pinned = 'home' ORDER BY edatetime limit 10")
            r = db.store_result()
            pinned_events = r.fetch_row(maxrows=10, how=1)

            # GALLERY / SLIDESHOW
            #random_number = random.randint(1,len(galleries_dict))
            random_number = random.choice(galleries_dict_vals)
            g = Gallery(random_number)
            gallery = g.get_gallery()
            images = g.get_images()

            template = env.get_template("home.html")
            response = template.render(next_event=next_event, calendar={"html": html_cal}, 
                pinned_events=pinned_events, gallery=gallery, images=images)


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
            c = db.cursor()
            c.execute("SELECT * FROM registration ORDER BY rid desc")
            allrows = c.fetchall()
            c.close()
            template = env.get_template("admin-registration.html")
            response = template.render(allrows=allrows)


        elif environ['PATH_INFO'] == '/admin/registration2':
            data = json.loads(read_file("../registration/data/wheel-wars.json"))
            template = env.get_template("admin-registration2.html")
            response = template.render(data=data)


        elif environ['PATH_INFO'] == '/summer-camp-registration':
            template = env.get_template("summer-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)


        elif environ['PATH_INFO'].lstrip('/') in pages:
            page_name = environ['PATH_INFO'].lstrip('/')
            page_content = str(read_file(f"data/{page_name}.html"))
            template = env.get_template("pages.html")
            response = template.render(page_name=page_name, page_content=page_content)


        elif environ['PATH_INFO'] == '/admin/products/list':
            c = db.cursor()
            c.execute("SELECT * FROM products")
            allrows = c.fetchall()
            c.close()
            template = env.get_template("admin-products-list.html")
            response = template.render(allrows=allrows)


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
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/image/upload":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        # NOTICE: NOT DECODING post_input below FOR IMAGES
        post_input = environ['wsgi.input'].read(length)

        # NOTICE BYTES STRING below FOR IMAGES
        #image_eid = post_input.split(b'------')[1]
        image_eid = post_input.split(b'Content-Disposition: form-data')[1]

        print(f"image_eid: {image_eid}")

        eid = re.sub(b'^.*name="eid"(.*?)------.*$', r"\1", image_eid, flags=re.DOTALL).strip()

        print(f"eid: {eid}")

        eid = int(eid.decode('UTF-8'))

        print(f"eid: {eid}")

        if eid == 0:
            image_pid = post_input.split(b'Content-Disposition: form-data')[4]
            if 'name="pid"' in image_pid.decode('UTF-8'):
                pid = re.sub(b'^.*name="pid"(.*?)------.*$', r"\1", image_pid, flags=re.DOTALL).strip()
                pid = int(pid.decode('UTF-8'))
            else:
                pid = 0
        else:
            pid = 0

        #with open("stderr.log", "a") as logfile:
        #    logfile.write(str(f"post_input: {post_input}++++\nimage_eid: {image_eid}++++\neid: {eid}++++\n"))

        #image_data = post_input.split(b'------')[2]
        image_data = post_input.split(b'Content-Disposition: form-data')[2]
        image_filename = re.sub(b'^.*filename="(.*?)".*$', r"\1", image_data, flags=re.DOTALL).strip()
        image_contents = re.sub(b'^.*Content-Type: image/jpeg(.*)$', r"\1", image_data, flags=re.DOTALL).strip()

        img_name = image_filename.decode('UTF-8')

        print(f"img_name: {img_name}")

        if img_name and image_contents:
            open(f"../www/img/orig/{img_name}", 'wb').write(image_contents)

            # Now create a thumbnail of the original
            size = 350, 350
            image = Image.open(f"../www/img/orig/{img_name}")
            image.thumbnail(size)
            image.save(f"../www/img/small/{img_name}", 'JPEG')

            if pid > 0:
                #sql = f"UPDATE products SET image_path_array = '{img_name}' WHERE eid = {eid}"
                # Because image_path_array is a list containgin multiple values:
                print(f"img_name: {img_name}")
                print(f"pid: {pid}")
                sql = f"UPDATE products SET image_path_array = concat(ifnull(image_path_array,''), ',{img_name}') WHERE pid = {pid}"
                print(f"sql is: {sql}")
                redirect_path = "products"
            else:
                sql = f"UPDATE events SET image = '{img_name}' WHERE eid = {eid}"
                redirect_path = "events"

            c = db.cursor()
            c.execute(sql)
            c.close()

        response = f'<meta http-equiv="refresh" content="0; url=/app/admin/{redirect_path}/list" />'

        #scrape_and_write("calendar")
        #time.sleep(2)
        #scrape_and_write("home")


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

        write_file(f"data/{page_name}.html", page_content)
        response = '<meta http-equiv="refresh" content="0; url=/app/admin/pages"/>'

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
            pid = int(results = results[0])
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

        print("HERE AAA")

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        print("post_input", post_input)

        data_object = {}
        data_array = []

        post_input_array = post_input.split('------')

        #with open("stderr.log", "a") as logfile:
        #    logfile.write(str(f"++++{post_input}++++"))

        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit" and not post_data_val.startswith('-----'):
                data_object[post_data_key] = post_data_val
                data_array.append(post_data_val)

        print("data_object", data_object)
        print("data_array", data_array)


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
            fields = "edatetime, title, duration, price, elimit, location, image, description, price_text, pinned, extra_data"
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
            print("____", sql2)
            d = db.cursor()
            d.execute(sql2)
            results = d.fetchone()
            print("____results", results)
            print("____type of results", type(results))
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

        template = env.get_template("admin-image.html")
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

