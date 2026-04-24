import os
import sys
import json
import urllib.parse
from datetime import datetime
from mailjet_rest import Client
#from datetime import date


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def url_decode(encoded_str):
    return urllib.parse.unquote(encoded_str)


sys.path.insert(0, os.path.dirname(__file__))


def email(environ, start_response):
    #today_iso = date.today().isoformat()
    now_iso = datetime.now().isoformat()
    start_response('200 OK', [('Content-Type', 'text/plain')])

    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit":

        length = int(environ.get('CONTENT_LENGTH', '0'))
        form_input = json.loads(environ['wsgi.input'].read(length).decode('UTF-8'))
        subject = form_input["subject"]

        print("form_input", form_input)
        print("form_input type", type(form_input))

        form_input_str = ""
        for k, v in form_input.items():
            form_input_str += f"{k}: {v}\n"

        if subject == "Inquiry from CCA contact form":
            email_to = "info@catalystcreativearts.com"
            name_to = "Jaime@CCA"

        secrets = json.loads(read_file("../app/data/passwords.json"))
        api_key = secrets["mailjet_api_key"]
        api_secret = secrets["mailjet_api_secret"]

        mailjet = Client(auth=(api_key, api_secret), version='v3.1')
        data = {
	      'Messages': [{
	        "From": {"Email": "info@catalystcreativearts.com", "Name": "Jaime@CCA"},
	        "To": [{"Email": email_to, "Name": name_to}],
	        "Cc": [{"Email": "mmarum@gmail.com", "Name": "mmarum"}],
	        "Subject": f"{subject} {now_iso}",
	        "TextPart": url_decode(form_input_str),
	        "CustomID": f"MailjetTest {now_iso}"
          }]
        }
        result = mailjet.send.create(data=data)
        print(result.status_code)
        print(result.json())

        response = "200"

    else:
        response = "ERROR"

    return [response.encode()]


if __name__ == "__main__":
    print("test")
