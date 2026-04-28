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
    epoch_now = int(time.time())
    iso_now = str(datetime.datetime.now()).split(".")[0]

    pages = json.loads(read_file("data/pages-list.json"))
    pages.sort()

    galleries_dict = json.loads(read_file("data/galleries-dict.json"))
    galleries_list = list(galleries_dict.keys())
    galleries_dict_vals = list(galleries_dict.values())

    path = environ['PATH_INFO']
    req_method = environ['REQUEST_METHOD'].lower()
    qs = environ.get("QUERY_STRING", "")
    content_length = int(environ.get('CONTENT_LENGTH', '0'))
    post_input = environ['wsgi.input'].read(content_length)
    http_cookie = environ.get("HTTP_COOKIE", "")

    if path.startswith("/admin/"):

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

        admin = AdminUI(post_input, qs)

        method_name = path.split("/")[2].replace("-", "_")
        method = getattr(admin, method_name, None)

        if method:
            response = method()
        else:
            response = "admin.not_found()"

    else:

        build = Build(qs, path)

        if path == "/gallery/slideshow" or path.lstrip("/") in galleries_list:
            response = build.gallery_slideshow(galleries_dict)

        elif re.match("/products/[a-z-]+/[0-9]+", path):
            response = build.product_detail()

        elif path.lstrip("/") in pages:
            response = build.custom_pages()

        elif path == "/summer-camp-registration":
            template = env.get_template("summer-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path == "/cart":
            template = env.get_template("cart-list.html")
            response = template.render()

        elif path == "/art-camp-registration":
            template = env.get_template("art-camp-registration.html")
            form = RegistrationForm()
            response = template.render(form=form)

        elif path == "/":
            path_info = path.lstrip("/")
            template = env.get_template("main.html")
            response = template.render(path_info=path_info)

        else:

            dispatch = {
                "/build-individual-event": build.individual_event,
                "/calendar": build.list_events_calendar,
                "/pottery-lessons": build.pottery_lessons,
                "/after-school-pottery": build.after_school_pottery,
                "/community-events": build.community_events,
                "/products": build.list_products,
                "/book/event": build.book_event,
                "/index": build.homepage_index
            }
            response = dispatch.get(path, "build.not_found")()

    return [response.encode()]

