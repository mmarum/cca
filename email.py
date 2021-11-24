from __future__ import print_function
import os
import sys
import json
# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
# https://app.sendgrid.com/

#from sendgrid import SendGridAPIClient
#from sendgrid.helpers.mail import Mail

import sendgrid
from sendgrid.helpers.mail import *

#import urllib

#python2.7.16
#sendgrid
#requests

# curl -XPOST -H "Content-Type: application/json" \
# --data '{"email":"mmarum@gmail.com","purpose": "1"}' \
# -u catalystemail:your_password \
# "https://www.catalystcreativearts.com/email/submit"

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

def email(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])

    passwd = json.loads(read_file("../app/data/passwords.json"))

    SENDGRID_API_KEY = passwd["SENDGRID_API_KEY"]
    print('SENDGRID_API_KEY', SENDGRID_API_KEY)

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        #print('post_input', str(post_input))
        form_data = json.loads(post_input)
        #print('form_data', str(form_data))

        # TODO: email pattern verification

        subject = str(form_data['subject'])
        #print('subject', subject)
        content = str(form_data['content'])
        #print('content', content)

        content = content.replace('%20', ' ')
        #content = urllib.unquote(content).decode('utf8')
        #print('content', content)

        if "Contact form inquiry" in subject and ("http" in content or "www" in content):
            raise ValueError('Link found in contact form submission. Stopping process.')

        # payer_info should look like this:
        # {'order_id': '03466302SA486820S', 'event_id': '146', 'payer_email': 'mmarum@gmail.com', 'payer_name': 'Matthew', 'amount': '1.00'}

        # form_data: {u'content': u'_hey_ _content_', u'payer_info': u'{\n    "order_id": "8AP73850LP3806125",\n    "event_id": "146",\n    "payer_email": "mmarum@gmail.com",\n    "payer_name": "Matthew",\n    "amount": "1.00"\n}', u'subject': u'Thank you for your CCA Event purchase'}

        try:
            payer_info = json.loads(form_data['payer_info'])
            print('payer_info', payer_info)

            to_email = payer_info['payer_email']

            if to_email == "mmarum-buyer@gmail.com":
                to_email = "mmarum@gmail.com"

            content = str(payer_info["payer_name"]) + ",\n"
            content += "Thank you for your event purchase at CCA.\n" 
            content += "Order ID: " + str(payer_info["order_id"]) + ".\n"
            content += "Event ID: " + str(payer_info["event_id"]) + ".\n"
            content += "Amount: " + str(payer_info["amount"]) + ".\n"

        except:
            payer_info = ''
            to_email = "mmarum@gmail.com"

        try:
            sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
            from_email = Email("order@catalystcreativearts.com")
            to_email = To(to_email)
            subject = subject
            content = Content("text/plain", content)
            mail = Mail(from_email, to_email, subject, content)
            response = sg.client.mail.send.post(request_body=mail.get())
            print('sendgrid resp status code', response.status_code)
            print('sendgrid resp body', response.body)
            print('sendgrid resp headers', response.headers)

        except Exception as e:
            print('err message', e.message)

        response = "200"

    else:
        response = "200"

    return [response.encode()]

