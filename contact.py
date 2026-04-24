import os
import re
import sys
import json
import requests
import urllib.parse
from jinja2 import Environment, PackageLoader, select_autoescape


def url_decode(encoded_str):
    return urllib.parse.unquote(encoded_str)


env = Environment(
    loader=PackageLoader('contact', '../app/templates'),
    autoescape=select_autoescape(['html'])
)

site = "https://www.catalystcreativearts.com"


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def clean_val(val):
    val = val.replace("+", " ")
    val = val.replace("%40", "@")
    return val


def formatt(environ):
    length = int(environ.get('CONTENT_LENGTH', '0'))
    post_input = environ['wsgi.input'].read(length).decode('UTF-8')
    print("post_input", post_input)
    data_object = {}
    data_list = post_input.split("&")
    for i in data_list:
        key, val = i.split("=")
        data_object[key] = clean_val(val)
    del data_object["submit"]
    return data_object


def spam_check(recipient_comment):
    spam_keywords = json.loads(read_file("spam-keywords.json"))
    for word in spam_keywords:
        if word.lower() in recipient_comment.lower():
            return word
    return None


def is_valid_email(email):
    return re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email) is not None


def is_valid_phone(number):
    number = re.sub(r'\D', '', number)
    return bool(re.fullmatch(r'\+?\d{10,15}', number))


sys.path.insert(0, os.path.dirname(__file__))
def contact(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    template = env.get_template("contact.html")
    if environ['REQUEST_METHOD'].lower() == "post" and environ['HTTP_REFERER'] == f"{site}/contact/":
        form_vals = formatt(environ)
        recipient_email = form_vals["email"]
        recipient_phone = form_vals["phone"]
        recipient_comment = url_decode(form_vals["comment"])

        form_vals["comment"] = recipient_comment

        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystemail"]
        url = f"{site}/email/submit"
        headers = {"Content-Type": "application/json"}

        print("form_vals", form_vals)
        print("form_vals type", type(form_vals))

        found_spam = spam_check(recipient_comment)

        if found_spam == None and is_valid_email(recipient_email) and is_valid_phone(recipient_phone):
            r = requests.post(url=url, json=form_vals, headers=headers, auth=('catalystemail', passwd))
            print("email/submit", r.status_code)

        error = ""
        if found_spam:
            error += f"Found spam words: {found_spam}. "

        if is_valid_email(recipient_email) == False:
            error += f"Bad email: {recipient_email}. "

        if is_valid_phone(recipient_phone) == False:
            error += f"Bad phone: {recipient_phone}. "

        response = template.render(form_vals=form_vals, error=error)
    else:
        response = template.render()
    return [response.encode()]

