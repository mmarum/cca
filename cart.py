import os
import sys
import re
import json
import MySQLdb
import datetime

def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content

# curl -X POST -H "Content-Type: application/json" --data '{"session_id": "9737659200802678", "product_id": 1, "quantity": 1}' https://www.catalystcreativearts.com/cart/add
# Sample response: {session_id: "9737659200802678", product_id: 1, quantity: 1}

# cart_products: cid pid quantity price_override
# cart: cid session_id create_time payment_time order_id

sys.path.insert(0, os.path.dirname(__file__))
def cart(environ, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])
    if environ['REQUEST_METHOD'] == "POST" and environ['PATH_INFO'] == "/add": # and re.match('/app/products/[a-z-]+/[0-9]+', environ['HTTP_REFERER']):
        length = int(environ.get('CONTENT_LENGTH', '0'))
        post_input = environ['wsgi.input'].read(length).decode('UTF-8')
        input_list = json.loads(post_input)

        session_id = input_list["session_id"]
        product_id = int(input_list["product_id"])
        quantity = int(input_list["quantity"])

        passwd = json.loads(read_file("../app/data/passwords.json"))["catalystcreative_cca"]
        db = MySQLdb.connect(host="localhost", user="catalystcreative_cca", passwd=passwd, db="catalystcreative_arts")
        time_now = datetime.datetime.now()

        try:

            # CHECK to see if there's an existing cart for this session_id
            db.query(f"SELECT cid FROM cart WHERE session_id = {session_id}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]

        except:

            # SINCE there's not a cart entry already, create one
            fields = "session_id, create_time"
            vals = [session_id, time_now]
            sql = f"INSERT INTO cart ({fields}) VALUES (%s, %s)"
            c = db.cursor()
            c.execute(sql, vals)
            c.close()

            # NOW retrieve its cid
            db.query(f"SELECT LAST_INSERT_ID() as cid")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]

        cid = row["cid"]

        fields = "cid, pid, quantity"
        vals = [cid, product_id, quantity]
        # insert into cart_products (cid, pid, quantity) values (1, 1, 1);
        sql = f"INSERT INTO cart_products ({fields}) VALUES (%s, %s, %s)"
        c = db.cursor()
        c.execute(sql, vals)
        c.close()

        response = f"{cid} {session_id} {product_id} {quantity} {time_now}"
    else:
        response = "200"

    return [response.encode()]

