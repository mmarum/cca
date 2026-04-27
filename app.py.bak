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

from admin_ui import AdminUI
from build import Build


env = Environment(
    loader=PackageLoader('app', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))

refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'


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

        admin = AdminUI()

    else:

        build = Build()


    if req_method == "get":

        if path == "/admin/events/list":
            response = admin.events_list()

        elif path == "/admin/orders/list":
            response = admin.orders_list()

        elif path == "/admin/events/add-edit":
            response = admin.events_add_edit(query_string)

        elif path == "/admin/events/delete":
            response = admin.events_delete(query_string)

        elif path == "/admin/booking/list":
            response = admin.booking_list(query_string)

        elif path == "/admin/booking/add-edit":
            response = admin.booking_add_edit(query_string, this_now)

        elif path == "/admin/pages":
            response = admin.pages(query_string)

        elif path == "/admin/signup":
            response = admin.signup()

        elif path == "/admin/guests":
            response = admin.guests()

        elif path == "/admin/registration/list":
            response = admin.registration_list(query_string)

        elif path == "/admin/registration/add-edit":
            response = admin.registration_add_edit(query_string)

        elif path == "/admin/products/list":
            response = admin.products_list(global_settings)

        elif path == "/admin/products/add-edit":
            response = admin.products_add_edit(query_string)

        elif path == "/admin/products/delete":
            response = admin.products_delete(query_string)

        elif path == "/build-individual-event":
            response = build.individual_event(query_string)

        elif path == "/list/events" or path == "/calendar":
            response = build.list_events_calendar()

        elif path == "/pottery-lessons":
            response = build.pottery_lessons()

        elif path == "/after-school-pottery":
            response = build.after_school_pottery()

        elif path == "/community-events":
            response = build.community_events()

        elif path == "/cart":
            template = env.get_template("cart-list.html")
            response = template.render()

        elif path == "/products":
            reponse = build.list_products()

        elif re.match("/products/[a-z-]+/[0-9]+", path):
            response = build.product_detail(path)

        elif path == "/book/event":
            response = build.book_event(query_string)

        elif path == "/gallery/slideshow" or path.lstrip("/") in galleries_list:
            response = build.gallery_slideshow(path, query_string, galleries_dict)

        elif path == "/index":
            response = build.homepage_index(global_settings, this_now, galleries_dict_vals)

        elif path == "/summer-camp-registration":
            template = env.get_template("summer-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path == "/art-camp-registration":
            template = env.get_template("art-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path.lstrip("/") in pages:
            response = build.custom_pages(path)

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

