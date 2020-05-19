import os
import sys
import json
# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
# https://app.sendgrid.com/
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

    SENDGRID_API_KEY = json.loads(read_file("../app/data/passwords.json"))["SENDGRID_API_KEY"]
    print SENDGRID_API_KEY

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        print('post_input')
        print str(post_input)
        form_data = json.loads(post_input)
        print('form_data')
        print str(form_data)

        # TODO: email pattern verification

        subject = str(form_data['subject'])
        print subject
        content = str(form_data['content'])
        content = content.replace('%20', ' ')
        print content

        if "Contact form inquiry" in subject and ("http" in content or ".com" in content):
            raise ValueError('Link found in contact form submission. Stopping process.')

        message = Mail(
            from_email="cca-robot@catalystcreativearts.com",
            to_emails="mmarum@gmail.com,info@catalystcreativearts.com",
            subject=subject,
            html_content=content)

        print message

        try:
            #sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            print sg

            try:
                response = sg.send(message)
            except:
                response = "FAILED TO SEND"
                print "FAILED TO SEND"
                
            print response.status_code
            print response.body
            print response.headers
        except Exception as e:
            print e.message

        response = "200"

    else:
        response = "200"

    return [response.encode()]
