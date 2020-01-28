import os
import sys
import json
import urllib.parse
import re

# https://jinja.palletsprojects.com/en/2.10.x/api/
from jinja2 import Template

# https://wtforms.readthedocs.io/en/stable/index.html
from forms import AdminForm

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

def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    if environ['REQUEST_METHOD'] == "GET":

        data = json.loads(read_file("data.json"))
        t = Template(read_file("templates/form.html"))

        if environ['PATH_INFO'] == '/app/admin/events':
            form = AdminForm()
            response = t.render(data=data, form=form)

        elif environ['PATH_INFO'] == '/app/admin/events/edit':
            date_time = environ['QUERY_STRING'].split("=")[1]
            event_data = data[date_time]
            form = AdminForm(**event_data)
            response = t.render(form=form, event_data=event_data, date_time=date_time)
        else:
            response = "<a href='/app/admin/events'>Admin/Events</a>"

    elif environ['REQUEST_METHOD'] == "POST":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data = json.loads(read_file("data.json"))
        date_time = re.sub(r'^.*name="date_time"(.*?)------.*$', r"\1", post_input, flags=re.DOTALL).strip()
        data[date_time] = {}
        data_array = post_input.split('------')

        for d in data_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            data[date_time]["date_time"] = date_time
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit" and post_data_key != "date_time":
                data[date_time][post_data_key] = post_data_val

        # Invoking the object in order to validate form field values
        form = AdminForm(**data[date_time])

        write_file("data.json", json.dumps(data, indent=4))
        response = f"{data}"

    else:
        response = "barf"

    response += f"<hr>{str(environ)}"

    return [response.encode()]

