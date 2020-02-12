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

from gallery import Gallery

#from MySQLdb import _mysql
#db = mysql.connect(host="localhost", user=dbuser, passwd=passwd, db="jedmarum_events")
#db.query("""SELECT * FROM events""")
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


def make_cal(db, month=2, year=2020):

    myCal = calendar.HTMLCalendar(calendar.SUNDAY)

    # TODO: Identify current year and month
    # to replace hard-coded values
    this_year = year #2020
    this_month = month #2
    htmlStr = myCal.formatmonth(this_year, this_month)
    htmlStr = htmlStr.replace("&nbsp;"," ")
    next_link = f"<div><a href='' onclick='nextMonth({month+1}); return false;'>Next</a>\n"
    htmlStr = f"<div id='month{month}'>\n{htmlStr}\n{next_link}\n</div>\n"

    c = db.cursor()
    c.execute(f"SELECT edatetime FROM events WHERE MONTH(edatetime) = {this_month} AND YEAR(edatetime) = {this_year}")
    allrows = c.fetchall()
    c.close()

    for d in allrows:
        day = str(d[0])
        day = day.split(' ')[0].split('-')[2].lstrip('0')
        htmlStr = htmlStr.replace(f'">{day}<', f' event"><a href="#" >{day}</a><')

    return htmlStr


def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="jedmarum_events")

    ####
    ####
    if environ['REQUEST_METHOD'] == "GET":

        #data = json.loads(read_file("data/events.json"))

        if environ['PATH_INFO'] == '/admin/events/list':
            c = db.cursor()
            c.execute("SELECT * FROM events WHERE edatetime > CURDATE() ORDER BY edatetime")
            allrows = c.fetchall()
            c.close()
            t = Template(read_file("templates/admin-events-list.html"))
            response = t.render(allrows=allrows)


        elif environ['PATH_INFO'] == '/admin/events/add-edit':
            if len(environ['QUERY_STRING']) > 1:
                eid = environ['QUERY_STRING'].split("=")[1]
                db.query(f"SELECT * FROM events WHERE eid = {eid}")
                r = db.store_result()
                row = r.fetch_row(maxrows=1, how=1)[0]
                form = EventsForm(**row)
            else:
                form = EventsForm()
            t = Template(read_file("templates/admin-events-add-edit.html"))
            response = t.render(form=form)


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


        elif environ['PATH_INFO'] == '/list/events':

            db.query("SELECT * FROM events WHERE edatetime > CURDATE() ORDER BY edatetime")
            r = db.store_result()
            allrows = r.fetch_row(maxrows=100, how=1)

            db.query("SELECT eid, count(eid) as count_eid FROM orders group by eid")
            # TODO: May need to add join to events table above
            # so as to only pull future event dates
            r = db.store_result()
            orders_count = r.fetch_row(maxrows=100, how=1)

            orders_count_object = {}
            for item in orders_count:
                key = item['eid']
                val = item['count_eid']

                orders_count_object[key] = val

            t = Template(read_file("templates/list-events.html"))
            response = t.render(events=allrows, orders_count=orders_count_object)


        elif environ['PATH_INFO'] == '/book/event':
            eid = environ['QUERY_STRING'].split("=")[1]
            db.query(f"SELECT * FROM events WHERE eid = {eid}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            t = Template(read_file("templates/book-event.html"))
            response = t.render(event_data=row)


        elif environ['PATH_INFO'] == '/gallery/slideshow':
            #eid = environ['QUERY_STRING'].split("=")[1]
            g = Gallery()
            images = g.get_images()
            t = Template(read_file("templates/gallery-slideshow.html"))
            response = t.render(images=images)


        elif environ['PATH_INFO'] == '/admin/booking':

            # TODO: This first part should be call-able separately
            # And should be called about once per minute 

            # OR EVEN BETTER:
            # Maybe this chunk should be moved to the
            # /paypal-transaction-complete section

            # List, sort, then read all files in the orders/ folder
            files = [f for f in listdir("orders/") if isfile(join("orders/", f))]

            if len(files) > 0:
                # PART-1: Load new orders into database:
                # Reminder: Orders data files are saved as event_eid_value.json
                for f in files:
                    eid = f.replace(".json", "").strip()
                    event_orders_data = json.loads(read_file(f"orders/{f}"))

                    data_array = []
                    for order in event_orders_data:
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

                        # Load database:
                        fields = "order_id, eid, create_time, email, first_name, last_name, quantity, cost, paid"
                        vals = str(data_array).lstrip('[').rstrip(']')
                        sql = f"INSERT INTO orders ({fields}) VALUES ({vals})"

                        c = db.cursor()
                        c.execute(sql)
                        c.close()

                    # Now move the file to /orders/loaded/event_eid_value.json
                    # So that it doesn't get processed again
                    os.rename(f"orders/{f}", f"orders/loaded/{f}")

            # PART-2: Select future-date orders from database for admin view
            c = db.cursor()
            c.execute("SELECT e.title, e.edatetime, e.elimit, o.* FROM events e, orders o WHERE e.eid = o.eid AND e.edatetime > CURDATE() ORDER BY o.eid")
            allrows = c.fetchall()
            c.close()

            t = Template(read_file("templates/admin-booking.html"))
            response = t.render(orders=allrows)


        elif environ['PATH_INFO'] == '/calendar':

            htmlStr = ""
            for n in range(2,5):
                htmlStr += make_cal(db, n, 2020)

            html = { "html": htmlStr}
            t = Template(read_file("templates/calendar.html"))
            response = t.render(html=html)
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

        if img_name and image_contents:
            open(f"../www/img/orig/{img_name}", 'wb').write(image_contents)

            # Now create a thumbnail of the original
            size = 300, 300
            image = Image.open(f"../www/img/orig/{img_name}")
            image.thumbnail(size)
            image.save(f"../www/img/small/{img_name}", 'JPEG')

            sql = f"UPDATE events SET image = '{img_name}' WHERE eid = {eid}"
            c = db.cursor()
            c.execute(sql)
            c.close()

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

        # Todo: More validation
        events_form = EventsForm(**data_object)

        # Set query based on update vs insert
        if action == "Update":
            keys_vals = ""
            for k, v in data_object.items():
                keys_vals += str(f"{k}='{v}', ")
            keys_vals = keys_vals.rstrip(', ')
            sql = f"UPDATE events SET {keys_vals} WHERE eid = {eid}"

        else:
            fields = "edatetime, title, duration, price, elimit, location, image, description"
            vals = str(data_array).lstrip('[').rstrip(']')
            sql = f"INSERT INTO events ({fields}) VALUES ({vals})"

        c = db.cursor()
        c.execute(sql)
        c.close()

        # Next template needs to know the eid
        if action == "Insert":
            # Now retrieve the eid from the item we just added
            e = data_object['edatetime']
            t = data_object['title']
            sql2 = f"SELECT eid FROM events WHERE edatetime = '{e}' AND title = '{t}'"
            d = db.cursor()
            d.execute(sql2)
            eid = int(d.fetchone()[0])
            d.close()
        else:
            sql2 = "just an update"

        t = Template(read_file("templates/admin-image.html"))
        image_form = ImageForm()
        response = t.render(event_data=data_object, image_form=image_form, 
            sql={"sql":sql}, eid={"eid":eid}, sql2={"sql2":sql2})

    ####
    ####
    else:
        response = "barf"

    #response += f"<hr>{str(environ)}"

    db.close()

    return [response.encode()]

