import os
import sys
import json
import requests
sys.path.insert(0, os.path.dirname(__file__))

from update_extra import UpdateExtra

domain = "https://www.catalystcreativearts.com"

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


user = "catalystcreative"
passw = json.loads(read_file("../app/data/passwords.json"))[user]


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


        # VARIABLE-TIME STUFF:
        try:
            u = UpdateExtra(event_id, "", 0)
            u.set_via_purchase(form_orders['variable_time_slot'])
            u.update_extra()

            # Now rebuild the page so it reflects accurate inventory numbers
            r = requests.get(f'{domain}/app/build-individual-event?eid={event_id}', auth=(f'{user}', f'{passw}'))
            print("rebuilding", r.url)
            if r.status_code == 200:
                print(r.status_code)
                return r.text
            else:
                raise ValueError(f'get_page_contents fail: {path} {r.status_code}')
        except:
            print(f"NO VARIABLE TIME for {event_id}")


        ####
        try:
            payer_info = {
                "order_id": form_orders['orderID'],
                "event_id": form_orders['event_id'],
                "payer_email": form_orders['details']['payer']['email_address'],
                "payer_name": form_orders['details']['payer']['name']['given_name'],
                "amount": form_orders['details']['purchase_units'][0]['amount']['value']
            }
            print(payer_info)
        except:
            print('SOMETHING WENT WRONG WITH COLLECTING PAYER_INFO FROM FORM_ORDERS')
            payer_info = ''
        ####

        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
        url = f"{domain}/email/submit"

        data = {"subject": "CCA Event purchase", "content": f"{json.dumps(orders, indent=4)}"}
        headers = {"Content-Type": "application/json"}
        r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
        print(r.status_code)

        if type(payer_info) == dict:
            print('attempt to send to payer')
            data = {"subject": "Thank you for your CCA Event purchase", "content": f"_hey_ _content_", "payer_info": f"{json.dumps(payer_info, indent=4)}"}
            headers = {"Content-Type": "text/html"}
            r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
            print(r.status_code)
        else:
            print('NO LUCK-- payer_info type is not dict')

        response = f"sendgrid response: {str(r.status_code)}"

    else:
        response = "200"

    #response += f"<hr>{str(environ)}"

    return [response.encode()]
