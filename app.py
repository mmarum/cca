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
from os import listdir
from sql_mgr import query
from gallery import Gallery
from urllib.parse import unquote
from os.path import isfile, join
from writer import scrape_and_write
from update_extra import UpdateExtra
from custom_filters import get_inventory, slugify
from paper_calendar import make_cal, make_list
from jinja2 import Environment, PackageLoader, select_autoescape
from forms import ProductsForm, EventsForm, ImageForm, \
    RegistrationForm, BookingForm, SignupForm
from blauth import logged_in, login
from tools import read_file, write_file, post_input_mgr_1, post_input_mgr_2
from parse_multipart import parse_multipart


env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))

refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'


def admin_events_list():
    sql = f"select * from events where edatetime >= CURDATE() order by edatetime"
    rows = query(sql)
    template = env.get_template("admin-events-list.html")
    response = template.render(rows=rows)
    return response


def admin_orders_list():
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
    return response


def admin_events_add_edit(query_string):
    if len(query_string) > 1:
        eid = int(query_string.split("=")[1])
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
    return response


def admin_events_delete(query_string):
    eid = int(query_string.split("=")[1])
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
    return response


def admin_booking_list(query_string):
    view = ""
    gtlt = ">=" # default
    ascdesc = "asc"

    if query_string and "view" in query_string:
        view = query_string.split("=")[1]

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
    return response


def admin_booking_add_edit(query_string, this_now):
    sql = f"select * from events where edatetime > CURTIME() order by edatetime asc"
    allevents = query(sql)
    if len(query_string) > 1:
        order_id = int(query_string.split("=")[1])
        sql = f"select * from orders where id = {order_id}"
        row = query(sql)[0]
        form = BookingForm(**row)
    else:
        form = BookingForm()
    template = env.get_template("admin-booking-add-edit.html")
    response = template.render(form=form, allevents=allevents, this_now=this_now)
    return response


def admin_pages(query_string):
    template = env.get_template("admin-pages.html")
    if query_string:
        page_name = query_string.split("=")[1]
        try:
            page_content = read_file(f"data/{page_name}.html")
        except:
            page_content = None
        response = template.render(page_name=page_name, page_content=page_content)
    else:
        response = template.render(pages=pages)
    return response


def admin_signup():
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
    return response


def admin_guests():
    sql = "select distinct parent_name, parent_email, parent_phone, \
        session_detail from registration order by session_detail"
    registration_data = query(sql)

    # group by session:
    registration_data_dict = {}
    for guest_row in registration_data:
        name, email, phone, session = guest_row

        # format phone numbers:
        if re.match(r'\d{10}', phone):
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
    response = template.render(registration_data=registration_data_dict, 
        signup_data=signup_data)


def admin_registration_list(query_string):
    view = ""
    if query_string and "view" in query_string:
        view = query_string.split("=")[1]

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
    return response


def admin_registration_add_edit(query_string):
    if len(query_string) > 1:
        rid = int(query_string.split("=")[1])
        sql = f"select * from registration where rid = {rid}"
        this_reg_data = query(sql)[0]
        form = RegistrationForm(**this_reg_data)
    else:
        form = RegistrationForm()
    template = env.get_template("admin-registration-add-edit.html")
    response = template.render(form=form)
    return response


def admin_products_list(global_settings):
    sql = "select * from products order by pid desc"
    allrows = query(sql)
    template = env.get_template("admin-products-list.html")
    response = template.render(allrows=allrows, global_settings=global_settings)
    return response


def admin_products_add_edit(query_string):
    if len(query_string) > 1:
        pid = int(query_string.split("=")[1])
        sql = f"select * from products where pid = {pid}"
        row = query(sql)[0]
        form = ProductsForm(**row)
    else:
        form = ProductsForm()
    template = env.get_template("admin-products-add-edit.html")
    response = template.render(form=form)
    return response

def admin_products_delete(query_string):
    if len(query_string) > 1:
        pid = int(query_string.split("=")[1])
        sql = f"delete from products where pid = {pid}"
        query(sql)
        sql = f"delete from cart_order_product where product_id = {pid}"
        query(sql)
        response = '<meta http-equiv="refresh" content="0; url=/app/admin/products/list" />'
    else:
        response = ""
    return response


def build_individual_event(query_string):
    if query_string:
        eid = int(query_string.split("=")[1])
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
    return response


def list_events_calendar():
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
            parent[eid] = re.sub(r'^.*series=(\d+).*$', r'\1', row["tags"])
        else:
            parent[eid] = ""

    events_object = json.dumps(events_object)
    try:
        test = query_string.split("=")[1]
    except:
        test = ""

    template = env.get_template("list-events.html")
    response = template.render(events=allrows, 
        orders_count=orders_count_object, 
        events_object=events_object, 
        parent=parent, 
        test=test)
    return response


def pottery_lessons():
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
    template = env.get_template("pottery-lessons.html")
    response = template.render(events=allrows, 
        orders_count=orders_count_object, 
        events_object=events_object)
    return response


def after_school_pottery():
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
    return response


def community_events():
    sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' \
            or tags is null) and tags LIKE '%community-event%' order by edatetime ASC"
    allrows = query(sql)
    sql = "select * from events where edatetime < CURTIME() and (tags <> 'invisible' \
            or tags is null) and tags LIKE '%community-event%' order by edatetime DESC"
    past_events = query(sql)
    template = env.get_template("community-events.html")
    response = template.render(events=allrows, past_events=past_events)
    return response


def list_products():
    sql = "select * from products where active = 1"
    allrows = query(sql)
    template = env.get_template("list-products.html")
    response = template.render(products=allrows)
    return response


def product_detail(path):
    path_parts = path.split('/')
    product_name = path_parts[2]
    product_id = path_parts[3]
    pid = int(product_id)
    sql = f"select * from products where pid = {pid}"
    row = query(sql)[0]
    template = env.get_template("product-detail.html")
    response = template.render(row=row)
    return response


def book_event(query_string):
    eid = int(query_string.split("=")[1])
    sql = f"select * from events where eid = {eid}"
    row = query(sql)[0]
    sql = f"select count(id) as cnt from orders where eid = {eid}"
    order_count = query(sql)[0]["cnt"]
    template = env.get_template("book-event.html")
    response = template.render(event_data=row, order_count=order_count)
    return response


def gallery_slideshow(path, query_string, galleries_dict):
    if path == '/gallery/slideshow':
        gid = int(query_string.split("=")[1])
    else:
        path_info = path.lstrip('/')
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
    return response


def homepage_index(global_settings, this_now, galleries_dict_vals):
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
    return response


def custom_pages(path):
    page_name = path.lstrip('/')
    page_content = str(read_file(f"data/{page_name}.html"))
    if page_name == "gift-card":
        template = env.get_template("gift-card.html")
    else:
        template = env.get_template("pages.html")
    response = template.render(page_name=page_name, page_content=page_content)
    return response


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
    req_method = environ['REQUEST_METHOD'].lower()
    query_string = environ['QUERY_STRING']
    content_length = int(environ.get('CONTENT_LENGTH', '0'))
    post_input = environ['wsgi.input'].read(content_length)
    http_cookie = environ.get("HTTP_COOKIE", "")


    if "admin" in path:
        if path == '/admin/signin':
            data_object=None
            login_result=None
            if req_method == "post":
                data_object = post_input_mgr_1(post_input.decode('UTF-8'))
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

    if req_method == "get":

        if path == "/admin/events/list":
            response = admin_events_list()

        elif path == "/admin/orders/list":
            response = admin_orders_list()

        elif path == "/admin/events/add-edit":
            response = admin_events_add_edit(query_string)

        elif path == "/admin/events/delete":
            response = admin_events_delete(query_string)

        elif path == "/admin/booking/list":
            response = admin_booking_list(query_string)

        elif path == "/admin/booking/add-edit":
            response = admin_booking_add_edit(query_string, this_now)

        elif path == "/admin/pages":
            response = admin_pages(query_string)

        elif path == "/admin/signup":
            response = admin_signup()

        elif path == "/admin/guests":
            response = admin_guests()

        elif path == "/admin/registration/list":
            response = admin_registration_list(query_string)

        elif path == "/admin/registration/add-edit":
            response = admin_registration_add_edit(query_string)

        elif path == "/admin/products/list":
            response = admin_products_list(global_settings)

        elif path == "/admin/products/add-edit":
            response = admin_products_add_edit(query_string)

        elif path == "/admin/products/delete":
            response = admin_products_delete(query_string)

        elif path == "/build-individual-event":
            response = build_individual_event(query_string)

        elif path == "/list/events" or path == "/calendar":
            response = list_events_calendar()

        elif path == "/pottery-lessons":
            response = pottery_lessons()

        elif path == "/after-school-pottery":
            response = after_school_pottery()

        elif path == "/community-events":
            response = community_events()

        elif path == "/cart":
            template = env.get_template("cart-list.html")
            response = template.render()

        elif path == "/products":
            reponse = list_products()

        elif re.match("/products/[a-z-]+/[0-9]+", path):
            response = product_detail(path)

        elif path == "/book/event":
            response = book_event(query_string)

        elif path == "/gallery/slideshow" or path.lstrip("/") in galleries_list:
            response = gallery_slideshow(path, query_string, galleries_dict)

        elif path == "/index":
            response = homepage_index(global_settings, this_now, galleries_dict_vals)

        elif path == "/summer-camp-registration":
            template = env.get_template("summer-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path == "/art-camp-registration":
            template = env.get_template("art-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path.lstrip("/") in pages:
            response = custom_pages(path)

        else:
            path_info = path.lstrip("/")
            template = env.get_template("main.html")
            response = template.render(path_info=path_info)

    elif req_method == "post":

        if path == "/paypal-transaction-complete":
            form_orders = json.loads(post_input.decode('UTF-8'))
            event_id = str(form_orders['event_id'])
            try:
                orders = json.loads(read_file(f"orders/{event_id}.json"))
            except:
                orders = []
            orders.append(form_orders)
            write_file(f"orders/{event_id}.json", json.dumps(orders, indent=4))
            response = "200"
            #scrape_and_write("calendar")


        elif path == "/product-image/upload":
            # NOTICE: NOT DECODING post_input below FOR IMAGES
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


        elif path == "/image/upload":

            print("/image/upload")

            m = re.search(
                b'name="eid"\\r\\n\\r\\n([^\\r\\n]+)',
                post_input
            )
            if m:
                eid = m.group(1).decode()
                print(eid)

            m = re.search(
                b'filename="([^"]+)"',
               post_input 
            )
            if m:
                img_name = m.group(1).decode()
                print(img_name)

            m = re.search(
                b'name="image".*?\\r\\n\\r\\n(.*?)\\r\\n------WebKitFormBoundary',
                post_input,
                flags=re.DOTALL
            )
            if m:
                img_contents = m.group(1)
                #print(image_body)

            if img_name and img_contents:
                open(f"../www/img/orig/{img_name}", 'wb').write(img_contents)
                size = 350, 350
                image = Image.open(f"../www/img/orig/{img_name}")
                image.thumbnail(size)
                image.save(f"../www/img/small/{img_name}", 'JPEG')
                sql = f"update events set image = '{img_name}' where eid = {eid}"
                query(sql)
            response = f'<meta http-equiv="refresh" content="0; url=/app/admin/products/list" />'

            """
            fields, files = parse_multipart(environ)
            eid = fields.get("eid")
            uploaded_image = files.get("image") # or whatever your field name is
            # Example: save file
            if uploaded_image:
                with open("/tmp/uploaded.jpg", "wb") as f:
                    f.write(uploaded_image["content"])
            """


        elif path == "/contact":
            contactus_dict = json.loads(read_file("data/contactus.json"))
            output = post_input_mgr_2(post_input.decode('UTF-8'))
            contactus_dict[str(this_now)] = output["data_object"]
            email = contactus_dict[str(this_now)]["email"]
            write_file(f"data/contactus.json", json.dumps(contactus_dict, indent=4))
            page_content = str(read_file(f"data/about-us.html"))
            template = env.get_template("pages.html")
            page_name = "about-us"
            response = template.render(page_name=page_name, page_content=page_content, email=email)


        elif path == "/admin/pages":
            output = post_input_mgr_2(post_input.decode('UTF-8'))
            data_object = output["data_object"]
            page_name = data_object["page_name"]
            page_content = data_object["page_content"]
            os.rename(f"data/{page_name}.html", f"data/{page_name}.html.bak")
            try:
                write_file(f"data/{page_name}.html", page_content)
                response = '<meta http-equiv="refresh" content="0; url=/app/admin/pages"/>'
            except:
                os.rename(f"data/{page_name}.html.bak", f"data/{page_name}.html")
                response = "ERROR WRITING PAGE <a href='/app/admin/pages'>Go back</a>"
            scrape_and_write(page_name)


        elif path == "/admin/products/add-edit":
            output = post_input_mgr_2(post_input.decode('UTF-8'))
            data_object = output["data_object"]
            data_array = output["data_array"]
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
                    val = val.replace("'", "''")
                    vals += f"'{val}',"
                vals = vals.rstrip(",")
                sql = f"insert into products ({fields}) values ({vals})"
                pid = query(sql)

            image_form = ImageForm()
            template = env.get_template("admin-products-image.html")
            response = template.render(product_data=data_object, image_form=image_form,
                sql={"sql":sql}, pid={"pid":pid})


        elif path == "/admin/registration/add-edit":
            output = post_input_mgr_2(post_input.decode('UTF-8'))
            data_object = output["data_object"]
            data_array = output["data_array"]

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
                    v = v.replace("'", "''")
                    values += f"'{v}',"
                values = values.rstrip(",")
                sql = f"insert into registration ({ fields }) values ({ values })"

            query(sql)
            template = env.get_template("admin-registration-add-edit.html")
            response = template.render(sql=sql)


        else:

            print("DEFAULT POST SECTION")

            output = post_input_mgr_2(post_input.decode('UTF-8'))
            data_object = output["data_object"]
            data_array = output["data_array"]

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
                for v in data_array:
                    v = v.replace("'", "''")
                    vals += f"'{v}',"
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

    return [response.encode()]

