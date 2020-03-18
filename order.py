import os
import sys
import json
import requests
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


def order(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit": #and environ['HTTP_REFERER'].endswith('calendar.html'):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        form_orders = json.loads(post_input)
        event_id = str(form_orders['event_id'])

        try:
            orders = json.loads(read_file(f"../app/orders/{event_id}.json"))
        except:
            orders = []

        orders.append(form_orders)

        write_file(f"../app/orders/{event_id}.json", json.dumps(orders, indent=4))

        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
        url = "https://www.catalystcreativearts.com/email/submit"
        data = {"subject": "CCA Event purchase", "content": f"{json.dumps(orders, indent=4)}"}
        headers = {"Content-Type": "application/json"}
        r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
        print(r.status_code)

        response = f"sendgrid response: {str(r.status_code)}"

    else:
        response = "200"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]
