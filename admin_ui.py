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


env = Environment(
    loader=PackageLoader('admin_ui', 'templates'),
    autoescape=select_autoescape(['html'])
)

env.filters["get_inventory"] = get_inventory
env.filters["slugify"] = slugify

sys.path.insert(0, os.path.dirname(__file__))

refresh_to_signin = '<meta http-equiv="refresh" content="0; url=/app/admin/signin" />'

pages = json.loads(read_file("data/pages-list.json"))
pages.sort()


def parse_image_upload(post_input):

    m = re.search(
        b'name="[ep]id"\\r\\n\\r\\n([^\\r\\n]+)',
        post_input
    )
    if m:
        this_id = m.group(1).decode()

    m = re.search(
        b'filename="([^"]+)"',
        post_input
    )
    if m:
        img_name = m.group(1).decode()

    m = re.search(
        b'name="image".*?\\r\\n\\r\\n(.*?)\\r\\n------WebKitFormBoundary',
        post_input,
        flags=re.DOTALL
    )
    if m:
        img_contents = m.group(1)

    return this_id, img_name, img_contents


class AdminUI:
    def __init__(self, post_input, qs):
        self.post_input = post_input
        self.qs = qs
        self.global_settings = json.loads(read_file("data/global_settings.json"))
        self.datetime_now = datetime.datetime.now()


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


    def events_add_edit(self):
        if len(self.qs) > 1:
            eid = int(self.qs.split("=")[1])
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


    def events_delete(self):
        eid = int(self.qs.split("=")[1])
        sql = f"select * from events where eid = {eid}"
        event = query(sql)[0]
        event["quantity_sum"] = 0
        event["remaining_spots"] = 0
        template = env.get_template("event.html")
        content = template.render(event=event, deleted=True)
        write_file(f"../www/event/{eid}.html", content)
        sql = f"delete from events where eid = {eid}"
        query(sql)
        response = '<meta http-equiv="refresh" content="0; url=/app/admin/events-list" />'
        return response


    def booking_list(self):
        view = ""
        gtlt = ">=" # default
        ascdesc = "asc"

        if self.qs and "view" in self.qs:
            view = self.qs.split("=")[1]

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


    def booking_add_edit(self):
        sql = f"select * from events where edatetime > CURTIME() order by edatetime asc"
        allevents = query(sql)
        if len(self.qs) > 1:
            order_id = int(self.qs.split("=")[1])
            sql = f"select * from orders where id = {order_id}"
            row = query(sql)[0]
            form = BookingForm(**row)
        else:
            form = BookingForm()
        template = env.get_template("admin-booking-add-edit.html")
        response = template.render(form=form, allevents=allevents, this_now=self.datetime_now)
        return response


    def pages(self):
        template = env.get_template("admin-pages.html")
        if self.qs:
            page_name = self.qs.split("=")[1]
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
        return response


    def registration_list(self):
        view = ""
        if self.qs and "view" in self.qs:
            view = self.qs.split("=")[1]

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


    def registration_add_edit(self):
        if len(self.qs) > 1:
            rid = int(self.qs.split("=")[1])
            sql = f"select * from registration where rid = {rid}"
            this_reg_data = query(sql)[0]
            form = RegistrationForm(**this_reg_data)
        else:
            form = RegistrationForm()
        template = env.get_template("admin-registration-add-edit.html")
        response = template.render(form=form)
        return response


    def products_list(self):
        sql = "select * from products order by pid desc"
        allrows = query(sql)
        template = env.get_template("admin-products-list.html")
        response = template.render(allrows=allrows, global_settings=self.global_settings)
        return response


    def products_add_edit(self):
        if len(self.qs) > 1:
            pid = int(self.qs.split("=")[1])
            sql = f"select * from products where pid = {pid}"
            row = query(sql)[0]
            form = ProductsForm(**row)
        else:
            form = ProductsForm()
        template = env.get_template("admin-products-add-edit.html")
        response = template.render(form=form)
        return response


    def products_delete(self):
        if len(self.qs) > 1:
            pid = int(self.qs.split("=")[1])
            sql = f"delete from products where pid = {pid}"
            query(sql)
            sql = f"delete from cart_order_product where product_id = {pid}"
            query(sql)
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/products-list" />'
        else:
            response = ""
        return response


    """
    def paypal_transaction_complete(self):
        form_orders = json.loads(self.post_input.decode('UTF-8'))
        event_id = str(form_orders['event_id'])
        try:
            orders = json.loads(read_file(f"orders/{event_id}.json"))
        except:
            orders = []
        orders.append(form_orders)
        write_file(f"orders/{event_id}.json", json.dumps(orders, indent=4))
        response = "200"
        #scrape_and_write("calendar")
        return response
    """


    def product_image_upload(self):
        pid, img_name, img_contents = parse_image_upload(self.post_input)
        if img_name and img_contents:
            open(f"../www/img/orig/{img_name}", 'wb').write(img_contents)
            size = 350, 350
            image = Image.open(f"../www/img/orig/{img_name}")
            image.thumbnail(size)
            image.save(f"../www/img/small/{img_name}", 'JPEG')
            sql = f"update products set image_path_array = concat(ifnull(image_path_array,''), ',{img_name}') where pid = {pid}"
            query(sql)
        response = f'<meta http-equiv="refresh" content="0; url=/app/admin/products-list" />'
        return response


    def event_image_upload(self):
        eid, img_name, img_contents = parse_image_upload(self.post_input)
        if img_name and img_contents:
            open(f"../www/img/orig/{img_name}", 'wb').write(img_contents)
            size = 350, 350
            image = Image.open(f"../www/img/orig/{img_name}")
            image.thumbnail(size)
            image.save(f"../www/img/small/{img_name}", 'JPEG')
            sql = f"update events set image = '{img_name}' where eid = {eid}"
            query(sql)
        response = f'<meta http-equiv="refresh" content="0; url=/app/admin/events-list" />'
        return response


    """
    def contact(self):
        contactus_dict = json.loads(read_file("data/contactus.json"))
        output = post_input_mgr_2(self.post_input.decode('UTF-8'))
        contactus_dict[str(self.datetime_now)] = output["data_object"]
        email = contactus_dict[str(self.datetime_now)]["email"]
        write_file(f"data/contactus.json", json.dumps(contactus_dict, indent=4))
        page_content = str(read_file(f"data/about-us.html"))
        template = env.get_template("pages.html")
        page_name = "about-us"
        response = template.render(page_name=page_name, page_content=page_content, email=email)
        return response
    """


    def pages_submit(self):
        output = post_input_mgr_2(self.post_input.decode('UTF-8'))
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
        #scrape_and_write(page_name)
        return response


    def products_add_edit_submit(self):
        output = post_input_mgr_2(self.post_input.decode('UTF-8'))
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
        return response


    def registration_add_edit_submit(self):
        output = post_input_mgr_2(self.post_input.decode('UTF-8'))
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
        return response


    def events_add_edit_submit(self):
        output = post_input_mgr_2(self.post_input.decode('UTF-8'))
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
        return response

