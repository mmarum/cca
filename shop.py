import os
import sys
import time
import json
import MySQLdb
import requests
from jinja2 import Environment, PackageLoader, select_autoescape


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

env = Environment(
    loader=PackageLoader('shop', '../app/templates'),
    autoescape=select_autoescape(['html'])
)

sys.path.insert(0, os.path.dirname(__file__))

def shop(environ, start_response):

    dbuser = "catalystcreative_cca"
    passwd = json.loads(read_file("../app/data/passwords.json"))[dbuser]

    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])

    db = MySQLdb.connect(host="localhost", user=dbuser, passwd=passwd, db="catalystcreative_arts")

    method = environ['REQUEST_METHOD']
    path = environ['PATH_INFO']

    allowed_filter_words = []
    db.query("select distinct(lower(keywords_array)) as keyword from products where keywords_array != '' and active = 1")
    r = db.store_result()
    allrows = r.fetch_row(maxrows=100, how=1)
    for row in allrows:
        allowed_filter_words.append(row["keyword"])

    if path.startswith("/product"):
        pid = int(path.replace("/product/", ""))
        if not isinstance(pid, int):
            raise ValueError(f"Attempted pid not an int: {pid}")
        db.query(f"SELECT * FROM products WHERE pid = {pid}")
        r = db.store_result()
        row = r.fetch_row(maxrows=1, how=1)[0]
        template = env.get_template("product-detail.html")
        response = template.render(row=row)

    elif path.startswith("/filter"):
        filter_word = path.replace("/filter/", "")
        if filter_word not in allowed_filter_words:
            raise ValueError(f"Attempted filter_word not in allowed_filter_words list: {filter_word}")

        db.query(f"SELECT *, CEILING(inventory / 100) as invt FROM products WHERE active = 1 and keywords_array LIKE '%{filter_word}%' order by invt desc, pid asc")
        r = db.store_result()
        allrows = r.fetch_row(maxrows=100, how=1)
        template = env.get_template("list-products.html")
        response = template.render(products=allrows, allowed_filter_words=allowed_filter_words)

    else:
        db.query("SELECT *, CEILING(inventory / 100) as invt FROM products WHERE active = 1 order by invt desc, name desc")
        r = db.store_result()
        allrows = r.fetch_row(maxrows=100, how=1)
        template = env.get_template("list-products.html")
        response = template.render(products=allrows, allowed_filter_words=allowed_filter_words)

    return [response.encode()]

