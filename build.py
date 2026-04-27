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


env = Environment(
    loader=PackageLoader('build', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))

refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'


class Build:
    def __init__(self):
        self.test = "build-123"


    def individual_event(self, query_string):
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


    def list_events_calendar(self):
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


    def pottery_lessons(self):
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


    def after_school_pottery(self):
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


    def community_events(self):
        sql = "select * from events where edatetime >= CURTIME() and (tags <> 'invisible' \
                or tags is null) and tags LIKE '%community-event%' order by edatetime ASC"
        allrows = query(sql)
        sql = "select * from events where edatetime < CURTIME() and (tags <> 'invisible' \
                or tags is null) and tags LIKE '%community-event%' order by edatetime DESC"
        past_events = query(sql)
        template = env.get_template("community-events.html")
        response = template.render(events=allrows, past_events=past_events)
        return response


    def list_products(self):
        sql = "select * from products where active = 1"
        allrows = query(sql)
        template = env.get_template("list-products.html")
        response = template.render(products=allrows)
        return response


    def product_detail(self, path):
        path_parts = path.split('/')
        product_name = path_parts[2]
        product_id = path_parts[3]
        pid = int(product_id)
        sql = f"select * from products where pid = {pid}"
        row = query(sql)[0]
        template = env.get_template("product-detail.html")
        response = template.render(row=row)
        return response


    def book_event(self, query_string):
        eid = int(query_string.split("=")[1])
        sql = f"select * from events where eid = {eid}"
        row = query(sql)[0]
        sql = f"select count(id) as cnt from orders where eid = {eid}"
        order_count = query(sql)[0]["cnt"]
        template = env.get_template("book-event.html")
        response = template.render(event_data=row, order_count=order_count)
        return response


    def gallery_slideshow(self, path, query_string, galleries_dict):
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


    def homepage_index(self, global_settings, this_now, galleries_dict_vals):
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


    def custom_pages(self, path):
        page_name = path.lstrip('/')
        page_content = str(read_file(f"data/{page_name}.html"))
        if page_name == "gift-card":
            template = env.get_template("gift-card.html")
        else:
            template = env.get_template("pages.html")
        response = template.render(page_name=page_name, page_content=page_content)
        return response


