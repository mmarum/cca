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
    #loader=PackageLoader('app', 'templates'),
    loader=PackageLoader('admin_ui', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))

refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'


class AdminUI:
    def __init__(self):
        self.test = "test123"


    def events_list(self):
        sql = f"select * from events where edatetime >= CURDATE() order by edatetime"
        rows = query(sql)
        template = env.get_template("admin-events-list.html")
        response = template.render(rows=rows)
        return response


    def orders_list(self):
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


    def events_add_edit(self, query_string):
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


    def events_delete(self, query_string):
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


    def booking_list(self, query_string):
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


    def booking_add_edit(self, query_string, this_now):
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


    def pages(self, query_string):
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


    def signup(self):
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


    def guests(self):
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


    def registration_list(self, query_string):
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


    def registration_add_edit(self, query_string):
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


    def products_list(self, global_settings):
        sql = "select * from products order by pid desc"
        allrows = query(sql)
        template = env.get_template("admin-products-list.html")
        response = template.render(allrows=allrows, global_settings=global_settings)
        return response


    def products_add_edit(self, query_string):
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

    def products_delete(self, query_string):
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

