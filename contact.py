import os
import sys
import json
import requests

def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

sys.path.insert(0, os.path.dirname(__file__))
def contact(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit" and environ['HTTP_REFERER'].endswith('about-contact.html'):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        print(post_input)
        with open("../app/data/contact.txt", "a") as myfile:
            myfile.write(post_input)
        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
        url = "https://www.catalystcreativearts.com/email/submit"
        data = {"subject": "CCA Contact form inquiry", "content": f"{post_input}"}
        headers = {"Content-Type": "application/json"}
        r = requests.post(url=url, json=data, headers=headers, auth=('catalystemail', passwd))
        print(r.status_code)
        response = '<meta http-equiv="refresh" content="0; url=/about-contact.html#thanks" />'
    else:
        response = "200"
    return [response.encode()]

