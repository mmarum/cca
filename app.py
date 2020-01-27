import os
import sys
import json
import urllib.parse
import re

# https://jinja.palletsprojects.com/en/2.10.x/api/
from jinja2 import Template

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

        if environ['PATH_INFO'] == '/app/admin/events':
            data = json.loads(read_file("data.json"))
            t = Template(read_file("templates/form.html"))
            response = t.render(data=data)
        else:
            response = "<a href='/app/admin/events'>Admin/Events</a>"

    elif environ['REQUEST_METHOD'] == "POST":
        post_input = ""

        try:
            length = int(environ.get('CONTENT_LENGTH', '0'))
        except:
            length = 0

        if length != 0:
            post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data = json.loads(read_file("data.json"))
        date_time = re.sub(r'^.*name="date_time"(.*?)------.*$', r"\1", post_input, flags=re.DOTALL).strip()
        data[date_time] = {}
        data_array = post_input.split('------')
        for d in data_array:
            post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
            post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
            if len(post_data_key) > 1 and not post_data_key.startswith('WebKitForm') and post_data_key != "submit" and post_data_key != "date_time":
                data[date_time][post_data_key] = post_data_val

        write_file("data.json", json.dumps(data, indent=4))
        response = f"{data}"

    else:
        response = "barf"

    #response += str(environ)

    return [response.encode()]

