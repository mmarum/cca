import os
import sys
import json
# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
# https://app.sendgrid.com/
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

    SENDGRID_API_KEY = json.loads(read_file("../app/data/passwords.json"))["SENDGRID_API_KEY"]
    #print SENDGRID_API_KEY

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        #print('post_input')
        #print str(post_input)
        form_data = json.loads(post_input)
        #print('form_data')
        #print 'form_data: ' + str(form_data)

        # TODO: email pattern verification

        subject = str(form_data['subject'])
        #print 'subject: ' + subject
        content = str(form_data['content'])
        #print 'content: ' + content

        content = content.replace('%20', ' ')
        #content = urllib.unquote(content).decode('utf8')
        #print content

        if "Contact form inquiry" in subject and ("http" in content or "www" in content):
            raise ValueError('Link found in contact form submission. Stopping process.')

        # payer_info should look like this:
        # {'order_id': '03466302SA486820S', 'event_id': '146', 'payer_email': 'mmarum@gmail.com', 'payer_name': 'Matthew', 'amount': '1.00'}

        # form_data: {u'content': u'_hey_ _content_', u'payer_info': u'{\n    "order_id": "8AP73850LP3806125",\n    "event_id": "146",\n    "payer_email": "mmarum@gmail.com",\n    "payer_name": "Matthew",\n    "amount": "1.00"\n}', u'subject': u'Thank you for your CCA Event purchase'}

        """
form_data: {u'content': u'_hey_ _content_', u'payer_info': u'{\n    "order_id": "41T612531F6532025",\n    "event_id": "152",\n    "payer_email": "mmarum-buyer@gmail.com",\n    "payer_name": "test",\n    "amount": "38.00"\n}', u'subject': u'Thank you for your CCA Event purchase'}
subject: Thank you for your CCA Event purchase
content: _hey_ _content_
____payer_info
['order_id', 'event_id', 'amount', 'payer_name', 'payer_email']
Traceback (most recent call last):
  File "email.py", line 78, in email
    to_emails = payer_info['payer_email']
TypeError: list indices must be integers, not str
        """

        try:
            payer_info_u = json.loads(form_data['payer_info'])
            print(payer_info_u)

            #payer_info = [x.encode('utf-8') for x in payer_info_u]
            payer_info = payer_info_u
            print(payer_info)

            print('____payer_info')
            print(payer_info)

            to_emails = payer_info['payer_email']

            if to_emails == "mmarum-buyer@gmail.com":
                #to_emails = "mmarum@gmail.com"
                to_emails = "mmarum@advance.net"

            content = str(payer_info["payer_name"]) + ",\n"
            content += "Thank you for your event purchase at CCA.\n" 
            content += "Order ID: " + str(payer_info["order_id"]) + ".\n"
            content += "Event ID: " + str(payer_info["event_id"]) + ".\n"
            content += "Amount: " + str(payer_info["amount"]) + ".\n"

        except:
            payer_info = ''
            to_emails = "mmarum@gmail.com"
            #to_emails = "j.marumusa@gmail.com"
            #to_emails = "mmarum@advance.net"

        print 'to_emails: ' + to_emails

        message = Mail(
            from_email="cca-robot@catalystcreativearts.com",
            to_emails=to_emails,
            subject=subject,
            html_content=content)

        print 'print message ____'
        print message

        try:
            #sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            print sg

            try:
                response = sg.send(message)
                print response.status_code
                print response.body
                print response.headers
            except:
                print "FAILED TO SEND"
                
        except Exception as e:
            print e.message

        response = "200"

    else:
        response = "200"

    return [response.encode()]

