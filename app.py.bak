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

        admin = AdminUI(post_input)

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


        # TODO: Update all of the following paths to start with admin
        # Once that's done get rid of next line
        admin = AdminUI(post_input)


        if path == "/paypal-transaction-complete":
            response = admin.paypal_transaction_complete()

        elif path == "/product-image/upload":
            response = admin.product_image_upload()

        elif path == "/image/upload":
            response = admin.image_upload()

        elif path == "/contact":
            response = admin.contact()

        elif path == "/admin/pages":
            response = admin.admin_pages()

        elif path == "/admin/products/add-edit":
            response = admin.admin_products/add_edit()

        elif path == "/admin/registration/add-edit":
            response = admin.admin_registration_add_edit()

        else:
            response = admin.default_admin_post()


    return [response.encode()]

