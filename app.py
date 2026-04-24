import os
import re
import sys
import json
import time
import base64
import random
import datetime
import collections

from PIL import Image
from sql_mgr import query
from urllib.parse import unquote
from os import listdir
from gallery import Gallery
from os.path import isfile, join
from writer import scrape_and_write
from update_extra import UpdateExtra
from custom_filters import get_inventory, slugify
from paper_calendar import make_cal, make_list
from jinja2 import Environment, PackageLoader, select_autoescape
from forms import ProductsForm, EventsForm, ImageForm, \
    RegistrationForm, BookingForm, SignupForm
from blauth import logged_in, login
from tools import read_file, write_file, manage_post_input



refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'

env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))


def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    this_now = datetime.datetime.now()
    epoch_now = int(time.time())
    iso_now = str(datetime.datetime.now()).split(".")[0]

    pages = json.loads(read_file("data/pages-list.json"))
    pages.sort()

    galleries_dict = json.loads(read_file("data/galleries-dict.json"))
    galleries_list = list(galleries_dict.keys())
    galleries_dict_vals = list(galleries_dict.values())

    global_settings = json.loads(read_file("data/global_settings.json"))
    path = environ['PATH_INFO']
    http_cookie = environ.get("HTTP_COOKIE", "")


    if "admin" in environ['PATH_INFO']:
        if path == '/admin/signin':
            data_object=None
            login_result=None
            if environ['REQUEST_METHOD'] == "POST":
                length = int(environ.get('CONTENT_LENGTH', '0'))
                post_input = environ['wsgi.input'].read(length).decode('UTF-8')
                data_object = manage_post_input(post_input)
                login_result = login(data_object)
            template = env.get_template("admin-signin.html")
            response = template.render(data_object=data_object, login_result=login_result)
            return [response.encode()]
        elif path == '/admin/signout':
            template = env.get_template("admin-signout.html")
            response = template.render()
            return [response.encode()]
        elif logged_in(http_cookie) == False:
            return [refresh_to_signin.encode()]

    ####
    ####
    if environ['REQUEST_METHOD'] == "GET":

        if path == '/admin/events/list':

            sql = f"select * from events where edatetime >= CURDATE() order by edatetime"
            rows = query(sql)
            template = env.get_template("admin-events-list.html")
            response = template.render(rows=rows)
            return [response.encode()]


        elif path == '/admin/orders/list':

            base_sql = "select a.cart_order_id, a.create_date, a.checkout_date, \
                a.paypal_order_id, a.total, a.ship_date, a.session_id, b.quantity, \
                c.pid, c.name, c.image_path_array, c.inventory, c.price \
                from cart_order a, cart_order_product b, products c \
                where a.cart_order_id = b.cart_order_id \
                and b.product_id = c.pid"

            sql = f"{base_sql} and checkout_date >= '2023-09-23' and status = 'complete' and ship_date is NULL"
            unshipped = query(sql)

            shipping_info = {}
            for d in unshipped:
                order_id = d["paypal_order_id"]
                try:
                    webhook_metada = json.loads(read_file(f"../store-checkout/purchases/{order_id}.json"))
                    shipping_info[order_id] = webhook_metada
                except:
                    pass

            sql = f"{base_sql} and checkout_date >= '2023-09-23' and status = 'complete' and ship_date is not NULL"
            shipped = query(sql)
            sql = f"{base_sql} and create_date >= '2023-09-23' and status is NULL order by a.create_date desc"
            unpurchased = query(sql)
            template = env.get_template("admin-orders-list.html")
            response = template.render(unshipped=unshipped, shipped=shipped, unpurchased=unpurchased, shipping_info=shipping_info)


        elif environ['PATH_INFO'] == '/admin/events/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                eid = environ['QUERY_STRING'].split("=")[1]
                sql = f"select * from events where eid = {eid}"
                row = query(sql)[0]
                form = EventsForm(**row)
                sql = f"select * from events where tags like '%series={eid}%'"
                children = query(sql)
            else:
                form = EventsForm()
                children = None
            template = env.get_template("admin-events-add-edit.html")
            response = template.render(form=form, children=children)


        elif environ['PATH_INFO'] == "/admin/events/delete":
            eid = int(environ['QUERY_STRING'].split("=")[1])
            if type(eid) != int:
                response = ""
            sql = f"select * from events where eid = {eid}"
            event = query(sql)[0]
            event["quantity_sum"] = 0
            event["remaining_spots"] = 0
            template = env.get_template("event.html")
            content = template.render(event=event, deleted=True)
            write_file(f"../www/event/{eid}.html", content)
            sql = f"delete from events where eid = {eid}"
            query(sql)
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'


        #### ####
        #### ####
        elif environ['PATH_INFO'] == '/build-individual-event':
            if environ['QUERY_STRING']:
                eid = int(environ['QUERY_STRING'].split("=")[1])
                sql = f"select * from events where eid = {eid}"
            else:
                sql = "select * from events where edatetime >= CURTIME() order by edatetime"
                #    #and (tags <> 'invisible' or tags is null) order by edatetime")
            allrows = query(sql)

            template = env.get_template("event.html")
            upcoming_event_ids = []
            for event in allrows:
                eid = event["eid"]
                elimit = event["elimit"]

                sql = f"select sum(quantity) as quantity_sum from orders where eid = {eid}"
                quantity_sum = query(sql)[0]["quantity_sum"]

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

            sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' \
                    or tags is null) and tags NOT LIKE '%pottery-lesson%' order by edatetime"
            allrows = query(sql)

            sql = "select eid, SUM(quantity) as sum_quantity from orders GROUP BY eid"
            # TODO: May need to add join to events table above
            # so as to only pull future event dates
            orders_count = query(sql)

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

            sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' \
                    or tags is null) and (tags LIKE '%pottery-lesson%' OR tags like '%PL4%') order by edatetime ASC"
            allrows = query(sql)

            sql = "select eid, SUM(quantity) as sum_quantity from orders GROUP BY eid"
            orders_count = query(sql)

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
                events_object[eid]["tags"] = row["tags"]

            events_object = json.dumps(events_object)

            #template = env.get_template("pottery-lessons-test.html")
            template = env.get_template("pottery-lessons.html")
            response = template.render(events=allrows, 
                orders_count=orders_count_object, 
                events_object=events_object)

        ####


        elif environ['PATH_INFO'] == '/after-school-pottery':


            sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' \
                    or tags is null) and (tags LIKE '%after-school-pottery%') order by edatetime ASC"
            allrows = query(sql)

            sql = "select eid, SUM(quantity) as sum_quantity from orders GROUP BY eid"
            orders_count = query(sql)

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
                events_object[eid]["tags"] = row["tags"]

            events_object = json.dumps(events_object)
            template = env.get_template("after-school-pottery.html")
            response = template.render(events=allrows, 
                orders_count=orders_count_object, 
                events_object=events_object)


        ####


        elif environ['PATH_INFO'] == '/community-events':
            sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' or tags is null) and tags LIKE '%community-event%' order by edatetime ASC"
            allrows = query(sql)
            sql = "select * from events where edatetime < CURTIME() and (tags <> 'invisible' or tags is null) and tags LIKE '%community-event%' order by edatetime DESC"
            past_events = query(sql)
            template = env.get_template("community-events.html")
            response = template.render(events=allrows, past_events=past_events)

        ####


        elif environ['PATH_INFO'] == '/cart':
            template = env.get_template("cart-list.html")
            response = template.render()


        elif environ['PATH_INFO'] == '/products':
            sql = "select * from products where active = 1"
            allrows = query(sql)
            template = env.get_template("list-products.html")
            response = template.render(products=allrows)


        elif re.match('/products/[a-z-]+/[0-9]+', environ['PATH_INFO']):
            path_parts = environ['PATH_INFO'].split('/')
            product_name = path_parts[2]
            product_id = path_parts[3]
            pid = int(product_id)
            sql = f"select * from products where pid = {pid}"
            row = query(sql)[0]
            template = env.get_template("product-detail.html")
            response = template.render(row=row)


        elif environ['PATH_INFO'] == '/book/event':
            eid = environ['QUERY_STRING'].split("=")[1]
            sql = f"select * from events where eid = {eid}"
            row = query(sql)[0]
            sql = f"select count(id) as cnt from orders where eid = {eid}"
            order_count = query(sql)[0]["cnt"]
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
                            #sql = f"insert into orders ({fields}) values ({vals})"
                            sql = f"insert into orders ({fields}) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                            query(sql)

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

            sql = f"select e.title, e.edatetime, e.elimit, o.* \
                from events e, orders o where e.eid = o.eid AND \
                e.edatetime {gtlt} CURDATE() order by e.edatetime {ascdesc}"

            allrows = query(sql)

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

            sql = f"select * from events where edatetime > CURTIME() order by edatetime asc"
            allevents = query(sql)

            if len(environ['QUERY_STRING']) > 1:
                order_id = environ['QUERY_STRING'].split("=")[1]
                sql = f"select * from orders where id = {order_id}"
                row = query(sql)[0]
                form = BookingForm(**row)
            else:
                form = BookingForm()

            template = env.get_template("admin-booking-add-edit.html")
            response = template.render(form=form, allevents=allevents, this_now=this_now)


        elif environ['PATH_INFO'] == '/index':
            # UP-NEXT EVENT
            month = int(this_now.strftime("%m"))
            year = int(this_now.strftime("%Y"))
            html_cal = make_cal(month, year)

            sql = f"select * from events where edatetime > CURTIME() \
                and (tags <> 'invisible' or tags is null) \
                and title != 'Private Event' \
                and description not like '%Private Event%' \
                and title not like '%Studio Closed%' \
                and title != 'Studio Closed' \
                and tags NOT LIKE '%pottery-lesson%' \
                order by edatetime limit 1"

            next_event = query(sql)[0]

            # FEATURED / PINNED EVENTS
            sql = f"select * from events \
                where edatetime > CURTIME() \
                and tags = 'home' and tags NOT LIKE '%pottery-lesson%' \
                order by edatetime limit 10"

            events_tagged_home = query(sql)

            # RANDOM PRODUCT
            sql = f"select pid, name, image_path_array, price \
                from products where inventory > 0 \
                and active = 1 order by RAND() LIMIT 1"

            try:
                random_product = query(sql)[0]
            except:
                random_product = None

            # GALLERY / SLIDESHOW
            #random_number = random.randint(1,len(galleries_dict))
            random_number = random.choice(galleries_dict_vals)
            g = Gallery(random_number)
            gallery = g.get_gallery()
            images = g.get_images()

            # Event List:
            event_list_html = make_list()

            # RANDOM CRAFTS GALLERY
            good_cats = '"Acrylic Painting", "Artist Guided Family Painting", \
                "Fluid Art", "Handbuilt Pottery", "Fused Glass", "Leathercraft", \
                "Resin Crafts", "Water Marbling", "Pottery Painting"'

            sql = f"select a.path, c.name \
                from piwigz_images a, piwigz_image_category b, piwigz_categories c \
                where a.id = b.image_id \
                and b.category_id = c.id \
                and c.name in ({good_cats}) \
                order by RAND() \
                LIMIT 1"

            random_gallery = query(sql)[0]

            rg_img_path = random_gallery["path"]
            rg_category = random_gallery["name"]

            rg_img_path = rg_img_path.replace("./", "/gallery/")
            rg_img_path = rg_img_path.replace(".", "_small.")

            rg_category = rg_category.lower()
            rg_category = rg_category.replace(" ", "-")

            random_gallery["image_file"] = rg_img_path
            random_gallery["category_path"] = rg_category

            template = env.get_template("home.html")
            response = template.render(next_event=next_event, calendar={"html": html_cal}, 
                events_tagged_home=events_tagged_home, gallery=gallery, images=images, 
                event_list_html=event_list_html, random_product=random_product,
                global_settings=global_settings, random_gallery=random_gallery)


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


        elif environ['PATH_INFO'] == '/admin/signup':
            signups = []
            path = "../signup/data/"
            files = [f for f in listdir(path) if isfile(join(path, f))]
            for file in files:
                data = {}
                contents = json.loads(read_file(f"{path}{file}"))
                key = file.replace(".json", "")
                data[key] = contents
                signups.append(data)
            template = env.get_template("admin-signup-list.html")
            response = template.render(signups=signups)


        elif environ['PATH_INFO'] == '/admin/guests':
            sql = "select distinct parent_name, parent_email, parent_phone, session_detail from registration order by session_detail"
            registration_data = query(sql)

            # group by session:
            registration_data_dict = {}
            for guest_row in registration_data:
                name, email, phone, session = guest_row

                # format phone numbers:
                if re.match('\d{10}', phone):
                    phone = f"({phone[:3]}){phone[3:6]}-{phone[6:]}"

                try:
                    registration_data_dict[session].append([name, email, phone])
                except:
                    registration_data_dict[session] = []
                    registration_data_dict[session].append([name, email, phone])

            signup_data = {}
            for m in ["signup", "registration"]:
                path = f"../{m}/data/"
                files = [f for f in listdir(path) if isfile(join(path, f))]
                for file in files:
                    if not file.endswith("json"):
                        continue
                    contents = json.loads(read_file(f"{path}{file}"))
                    signup_data[file.replace(".json", "")] = contents

            template = env.get_template("admin-guests.html")
            response = template.render(registration_data=registration_data_dict, signup_data=signup_data)




        elif environ['PATH_INFO'] == '/admin/registration/list':

            view = ""
            if environ['QUERY_STRING'] and "view" in environ['QUERY_STRING']:
                view = environ['QUERY_STRING'].split("=")[1]

            if view == "all":
                special = ""
                orderby = "order_id, session_detail"
            else:
                special = "AND order_id is not NULL"
                orderby = "session_detail"

            sql = f"select * from registration where session_detail LIKE '%2026%' {special} order by {orderby}"
            allrows = query(sql)

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

            template = env.get_template("admin-registration-list.html")
            response = template.render(new_reg_dict=new_reg_dict)



        elif environ['PATH_INFO'] == '/admin/registration/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                rid = environ['QUERY_STRING'].split("=")[1]
                sql = f"select * from registration where rid = {rid}"
                this_reg_data = query(sql)[0]
                #print("this_reg_data", this_reg_data)
                form = RegistrationForm(**this_reg_data)
            else:
                form = RegistrationForm()
            template = env.get_template("admin-registration-add-edit.html")
            response = template.render(form=form)



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

            sql = "select * from products order by pid desc"
            allrows = query(sql)

            template = env.get_template("admin-products-list.html")
            response = template.render(allrows=allrows, global_settings=global_settings)


        elif environ['PATH_INFO'] == '/admin/products/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                pid = environ['QUERY_STRING'].split("=")[1]
                sql = f"select * from products where pid = {pid}"
                row = query(sql)[0]
                form = ProductsForm(**row)
            else:
                form = ProductsForm()
            template = env.get_template("admin-products-add-edit.html")
            response = template.render(form=form)


        elif environ['PATH_INFO'] == '/admin/products/delete':
            if len(environ['QUERY_STRING']) > 1:
                pid = int(environ['QUERY_STRING'].split("=")[1])
                sql = f"delete from products where pid = {pid}"
                query(sql)
                sql = f"delete from cart_order_product where product_id = {pid}"
                query(sql)
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
        sql = f"update products set image_path_array = concat(ifnull(image_path_array,''), ',{img_name}') where pid = {pid}"
        query(sql)
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
            sql = f"update events set image = '{img_name}' where eid = {eid}"
            query(sql)
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
            sql = f"update products set {keys_vals} where pid = {pid}"
            query(sql)

        else:
            fields = "name, description, image_path_array, inventory, price, keywords_array, active"
            vals = ""
            for val in data_array:
                vals += f"'{val}',"
            vals = vals.rstrip(",")
            sql = f"insert into products ({fields}) values ({vals})"
            pid = query(sql)

        image_form = ImageForm()
        template = env.get_template("admin-products-image.html")
        response = template.render(product_data=data_object, image_form=image_form,
            sql={"sql":sql}, pid={"pid":pid})


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/admin/registration/add-edit":
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
            if int(data_object['rid']) > 0:
                action = "Update"
                rid = data_object['rid']
            else:
                action = "Insert"
        except:
            action = "Insert"

        # Cleanup: Remove "rid"
        del data_object['rid']
        del data_array[0]

        if action == "Update":

            keys_vals = ""
            for k, v in data_object.items():
                v = v.replace("'", "''")
                keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')
            sql = f"update registration set {keys_vals} where rid = {rid}"

        elif action == "Insert":

            fields = ""
            for k in data_object.keys():
                fields += f"{k},"
            fields = fields.rstrip(",")
            del data_array[0]
            values = ""
            for v in data_array:
                values += f"'{v}',"
            values = values.rstrip(",")
            sql = f"insert into registration ({ fields }) values ({ values })"

        query(sql)
        template = env.get_template("admin-registration-add-edit.html")
        response = template.render(sql=sql)


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
            sql = f"update events set {keys_vals} where eid = {eid}"
            query(sql)

        elif action == "Insert":
            fields = "edatetime, title, duration, price, elimit, location, image, description, price_text, tags, extra_data"
            vals = ""
            for val in data_array:
                vals += f"'{val}',"
            vals = vals.rstrip(",")
            sql = f"insert into events ({fields}) values ({vals})"
            eid = query(sql)

        image_form = ImageForm()
        template = env.get_template("admin-events-image.html")
        response = template.render(event_data=data_object, image_form=image_form,
            sql={"sql":sql}, eid={"eid":eid})

        #scrape_and_write("calendar")
        #time.sleep(2)
        #scrape_and_write("home")

    ####
    ####
    else:
        response = "error"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

