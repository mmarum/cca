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
            eid = environ['QUERY_STRING'].split("=")[1]
            event_data = data[eid]
            form = AdminForm(**event_data)
            response = t.render(form=form, event_data=event_data)
        else:
            response = "<a href='/app/admin/events'>Admin/Events</a>"

    elif environ['REQUEST_METHOD'] == "POST":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data = json.loads(read_file("data.json"))
        eid = re.sub(r'^.*name="eid"(.*?)------.*$', r"\1", post_input, flags=re.DOTALL).strip()

        # If no eid then its a new entry
        # And must create a new eid
        if eid == "":
            keys_array = sorted(list(data.keys()))
            eid = int(keys_array[-1]) + 1

        data[eid] = {}
        data_array = post_input.split('------')

        for d in data_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit":
                data[eid][post_data_key] = post_data_val

        if data[eid]["eid"] == "":
            data[eid]["eid"] = str(eid)

        # Invoking the object in order to validate form field values
        form = AdminForm(**data[eid])
        # Todo: some validation 

        write_file("data.json", json.dumps(data, indent=4))
        response = f"{data}"

    else:
        response = "barf"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

