import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
def registration(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/submit" and environ['HTTP_REFERER'].endswith('registration'):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        # insert into database

        response = "in-progress"
    return [response.encode()]

