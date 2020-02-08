import os
import sys
import json
#import urllib.parse
import re
import base64
import calendar

# https://jinja.palletsprojects.com/en/2.10.x/api/
from jinja2 import Template

# https://wtforms.readthedocs.io/en/stable/index.html
from forms import EventsForm, ImageForm

from os import listdir
from os.path import isfile, join

# https://pillow.readthedocs.io/en/stable/
from PIL import Image

# https://github.com/PyMySQL/mysqlclient-python
# https://mysqlclient.readthedocs.io/
# https://mysqlclient.readthedocs.io/user_guide.html#some-mysql-examples
import MySQLdb

#from MySQLdb import _mysql
#db = mysql.connect(host="localhost", user=dbuser, passwd=passwd, db="jedmarum_events")
#db.query("""select * from events""")
#r=db.store_result()
#r.fetch_row(maxrows=100, how=1)

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


# mysql -u jedmarum_cca jedmarum_events -p
dbuser = "jedmarum_cca"
passwd = json.loads(read_file("data/passwords.json"))[dbuser]


db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="jedmarum_events")

 
def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    ####
    ####
    if environ['REQUEST_METHOD'] == "GET":

        data = json.loads(read_file("data/events.json"))

        if environ['PATH_INFO'] == '/admin/events/list':
            c = db.cursor()
            c.execute("select * from events")
            allrows = c.fetchall()
            t = Template(read_file("templates/admin-events-list.html"))
            response = t.render(allrows=allrows)

        elif environ['PATH_INFO'] == '/admin/events/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                eid = environ['QUERY_STRING'].split("=")[1]
                db.query(f"select * from events where eid = {eid}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = EventsForm(**row)
            else:
                form = EventsForm()
            t = Template(read_file("templates/admin-events-add-edit.html"))
            response = t.render(form=form)

        elif environ['PATH_INFO'] == "/admin/events/delete":
            eid = environ['QUERY_STRING'].split("=")[1]
            del data[eid]
            write_file("data/events.json", json.dumps(data, indent=4))
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'

        elif environ['PATH_INFO'] == '/list/events':
            t = Template(read_file("templates/list-events.html"))
            response = t.render(data=data)

        elif environ['PATH_INFO'] == '/book/event':
            eid = environ['QUERY_STRING'].split("=")[1]
            t = Template(read_file("templates/book-event.html"))
            response = t.render(event_data=data[eid])

        elif environ['PATH_INFO'] == '/admin/booking':
            # List, sort, then read all files in the orders/ folder
            files = [f for f in listdir("orders/") if isfile(join("orders/", f))]

            # Reminder: Orders data files are saved as event_eid_value.json
            orders_data = {}
            for f in files:
                eid = f.replace(".json", "").strip()
                event_orders_data = json.loads(read_file(f"orders/{f}"))

                orders_data[eid] = {}
                for order in event_orders_data:
                    order_id = order['orderID']

                    # We don't necessarily want all data from orders/event_eid_value.json
                    # So let's pick and choose what data we want to keep:

                    this_order = {}
                    this_order['order_id'] = order['orderID']
                    this_order['create_time'] = order['details']['create_time']
                    this_order['email_address'] = order['details']['payer']['email_address']
                    this_order['first_name'] = order['details']['payer']['name']['given_name']
                    this_order['last_name'] = order['details']['payer']['name']['surname']

                    # Notice zero after purchase_units
                    this_order['amount'] = order['details']['purchase_units'][0]['amount']['value']

                    orders_data[eid][order_id] = this_order

            t = Template(read_file("templates/admin-booking.html"))
            response = t.render(data=data, orders_data=orders_data)

        elif environ['PATH_INFO'] == '/calendar':

            myCal = calendar.HTMLCalendar(calendar.SUNDAY)
            htmlStr = myCal.formatmonth(2020, 2)
            htmlStr = htmlStr.replace("&nbsp;"," ")

            event_dates = set()
            for key, val in data.items(): 
                this_event_date = val["date"].split("/")[1].strip("0")
                event_dates.add(this_event_date)
                htmlStr = htmlStr.replace(f'">{this_event_date}<', f' event"><a href="#" >{this_event_date}</a><')

            html = { "html": htmlStr }

            t = Template(read_file("templates/calendar.html"))
            response = t.render(data=data, html=html, event_dates=event_dates)
            #response = htmlStr


        else:
            t = Template(read_file("templates/main.html"))
            response = t.render()

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


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/image/upload":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        # NOTICE: NOT DECODING post_input below FOR IMAGES
        post_input = environ['wsgi.input'].read(length)

        # NOTICE BYTES STRING below FOR IMAGES
        image_eid = post_input.split(b'------')[1]
        eid = re.sub(b'^.*name="eid"(.*)$', r"\1", image_eid, flags=re.DOTALL).strip()
        eid = int(eid.decode('UTF-8'))

        image_data = post_input.split(b'------')[2]
        image_filename = re.sub(b'^.*filename="(.*?)".*$', r"\1", image_data, flags=re.DOTALL).strip()
        image_contents = re.sub(b'^.*Content-Type: image/jpeg(.*)$', r"\1", image_data, flags=re.DOTALL).strip()

        img_name = image_filename.decode('UTF-8')

        if img_name:
            open(f"../www/img/orig/{img_name}", 'wb').write(image_contents)

        # Now create a thumbnail of the original
        size = 300, 300
        image = Image.open(f"../www/img/orig/{img_name}")
        image.thumbnail(size)
        image.save(f"../www/img/small/{img_name}", 'JPEG')

        sql = f"UPDATE events SET image = '{img_name}' WHERE eid = {eid}"
        c = db.cursor()
        c.execute(sql)

        response = '<meta http-equiv="refresh" content="0; url=/app/admin/events/list" />'


    ####
    ####
    elif environ['REQUEST_METHOD'] == "POST":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data_object = {}
        data_array = []

        post_input_array = post_input.split('------')

        for d in post_input_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit":
                data_object[post_data_key] = post_data_val
                data_array.append(post_data_val)

        # If form passes an eid value then query
        # is an update as opposed to an insert

        try:
            if int(data_object['eid']) > 0:
                eid = data_object['eid']
        except:
            pass

        # Cleanup: Remove "eid"
        del data_object['eid']
        del data_array[0]

        # Cleanup: Remove "append_time"
        del data_object['append_time']
        del data_array[1]

        # Todo: More validation
        events_form = EventsForm(**data_object)

        # Set query based on update vs insert
        keys_vals = ""
        if eid:
            for k, v in data_object.items():
                keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')
            sql = f"UPDATE events SET {keys_vals} WHERE eid = {eid}"
        else:
            fields = "datetime, title, duration, price, elimit, location, image, description"
            vals = str(data_array).lstrip('[').rstrip(']')
            sql = f"INSERT INTO events ({fields}) VALUES ({vals})"

        c = db.cursor()
        c.execute(sql)

        # Next template needs to know the eid
        if eid:
            pass
        else:
            # Now retrieve the eid from the item we just added
            sql = f"""select eid from events where datetime = '{data_object["datetime"]}' and title = '{data_object["title"]}'"""
            c.execute(sql)
            eid = int(c.fetchone()[0])

        t = Template(read_file("templates/admin-image.html"))
        image_form = ImageForm()
        response = t.render(event_data=data_object, image_form=image_form, sql={"sql":sql}, eid={"eid":eid})


    ####
    ####
    else:
        response = "barf"

    response += f"<hr>{str(environ)}"

    #db.close()

    return [response.encode()]

