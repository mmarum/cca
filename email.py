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
    #print('SENDGRID_API_KEY', SENDGRID_API_KEY)

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":

        length = int(environ.get('CONTENT_LENGTH', '0'))

        post_input = environ['wsgi.input'].read(length).decode('UTF-8')

        form_data = json.loads(post_input)

        subject = str(form_data['subject'])

        content = str(form_data['content']) + "\n"

        content = content.replace('%20', ' ')

        if "Contact form inquiry" in subject and ("http" in content or "www" in content):
            raise ValueError('Link found in contact form submission. Stopping process.')

        payer_info = json.loads(form_data['payer_info'])

        to_email = payer_info['email']

        if to_email == "mmarum-buyer@gmail.com":
            to_email = "mmarum@gmail.com"

        print("email", to_email)

        content += payer_info["name"] + "\n"
        content += payer_info["title"] + "\n"
        content += payer_info["date"] + "\n"
        content += payer_info["location"] + "\n"

        try:
            sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        except:
            print("fail on set sg")

        try:
            from_email = Email("order@catalystcreativearts.com")
        except:
            print("fail on Email()")

        try:
            to_email = To(to_email)
        except:
            print("fail on To()")

        try:
            content = Content("text/plain", content)
        except:
            print("fail on Content()")

        try:
            mail = Mail(from_email, to_email, subject, content)
        except:
            print("fail on Mail()")

        try:
            response = sg.client.mail.send.post(request_body=mail.get())
        except:
            print("fail on send.post")

        print('sendgrid resp status code', response.status_code)
        #print('sendgrid resp body', response.body)
        #print('sendgrid resp headers', response.headers)

        response = "200"

    else:
        response = "200"

    return [response.encode()]

