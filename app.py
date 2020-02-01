import os
import sys
import json
#import urllib.parse
import re
import base64

# https://jinja.palletsprojects.com/en/2.10.x/api/
from jinja2 import Template

# https://wtforms.readthedocs.io/en/stable/index.html
from forms import EventsForm, ImageForm

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

        data = json.loads(read_file("events.json"))
        t = Template(read_file("templates/admin-events.html"))

        if environ['PATH_INFO'] == '/app/admin/events':
            form = EventsForm()
            response = t.render(form=form, data=data)

        elif environ['PATH_INFO'] == '/app/admin/events/edit':
            eid = environ['QUERY_STRING'].split("=")[1]
            event_data = data[eid]
            form = EventsForm(**event_data)
            response = t.render(form=form, event_data=event_data)

        elif environ['PATH_INFO'] == "/app/admin/events/delete":
            eid = environ['QUERY_STRING'].split("=")[1]
            del data[eid]
            write_file("events.json", json.dumps(data, indent=4))
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/events" />'

        else:
            response = '<meta http-equiv="refresh" content="0; url=/app/admin/events" />'

    elif environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/app/image/upload":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length)

        image_eid = post_input.split(b'------')[1]
        eid = re.sub(b'^.*name="eid"(.*)$', r"\1", image_eid, flags=re.DOTALL).strip()

        image_data = post_input.split(b'------')[2]
        image_filename = re.sub(b'^.*filename="(.*?)".*$', r"\1", image_data, flags=re.DOTALL).strip()
        image_contents = re.sub(b'^.*Content-Type: image/jpeg(.*)$', r"\1", image_data, flags=re.DOTALL).strip()

        open(image_filename.decode('UTF-8'), 'wb').write(image_contents)

        # Attach this image filename to event object
        data = json.loads(read_file("events.json"))
        data[eid.decode('UTF-8')]["image_path"] = image_filename.decode('UTF-8')
        write_file("events.json", json.dumps(data, indent=4))

        #response = str(image_contents)
        response = '<meta http-equiv="refresh" content="0; url=/app/admin/events" />'

    elif environ['REQUEST_METHOD'] == "POST":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        data = json.loads(read_file("events.json"))
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
        form = EventsForm(**data[eid])
        # Todo: some validation 

        write_file("events.json", json.dumps(data, indent=4))

        t = Template(read_file("templates/admin-image.html"))
        image_form = ImageForm()
        response = t.render(event_data=data[eid], image_form=image_form)

    else:
        response = "barf"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]

