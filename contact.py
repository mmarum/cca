import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
def contact(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit" and environ['HTTP_REFERER'].endswith('about-contact.html'):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        with open("../app/data/contact.txt", "a") as myfile:
            myfile.write(post_input)
        response = '<meta http-equiv="refresh" content="0; url=/about-contact.html#thanks" />'
    return [response.encode()]

