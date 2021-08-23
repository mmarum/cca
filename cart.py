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

def write_log(file_name, content):
    f = open(file_name, "a")
    f.write(content)
    f.close()
    return True

# curl -X POST -H "Content-Type: application/json" --data '{"session_id": "123", "product_id": 1, "quantity": 1}' https://www.catalystcreativearts.com/cart-api/add
# Sample response: {session_id: "123", product_id: 1, quantity: 1}

sys.path.insert(0, os.path.dirname(__file__))
def cart_api(environ, start_response):
    start_response('200 OK', [('Content-Type', 'application/json')])

    if environ['REQUEST_METHOD'] != "POST":
        return ["Error. Request must be POST".encode()]

    #if not re.match('/app/products/[a-z-]+/[0-9]+', environ['HTTP_REFERER']):
    #    return ["Error. Invalid referer".encode()]

    length = int(environ.get('CONTENT_LENGTH', '0'))
    post_input = environ['wsgi.input'].read(length).decode('UTF-8')
    input_list = json.loads(post_input)

    session_id = str(input_list["session_id"])

    passwd = json.loads(read_file("../app/data/passwords.json"))["catalystcreative_cca"]
    db = MySQLdb.connect(host="localhost", user="catalystcreative_cca", passwd=passwd, db="catalystcreative_arts")
    time_now = datetime.datetime.now()


    ####
    if environ['PATH_INFO'] == "/add":
        product_id = int(input_list["product_id"])
        quantity = int(input_list["quantity"])
        try:
            db.query(f"SELECT cart_order_id FROM cart_order WHERE session_id = '{session_id}' and status is NULL")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            cart_order_id = row["cart_order_id"]
        except:
            fields = "session_id, create_date"
            vals = [session_id, time_now]
            sql = f"INSERT INTO cart_order ({fields}) VALUES (%s, %s)"
            c = db.cursor()
            c.execute(sql, vals)
            c.close()
            db.query(f"SELECT LAST_INSERT_ID() as cart_order_id")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            cart_order_id = row["cart_order_id"]
        db.query(f"SELECT count(quantity) as count from cart_order_product \
            WHERE cart_order_id = {cart_order_id} and product_id = {product_id}")
        r = db.store_result()
        row = r.fetch_row(maxrows=1, how=1)[0]
        count = int(row["count"])
        if count > 0:
            sql = f"UPDATE cart_order_product SET quantity = {quantity} \
                WHERE cart_order_id = {cart_order_id} and product_id = {product_id}"
            c = db.cursor()
            c.execute(sql)
            c.close()
        else:
            fields = "cart_order_id, product_id, quantity"
            vals = [cart_order_id, product_id, quantity]
            sql = f"INSERT INTO cart_order_product ({fields}) VALUES (%s, %s, %s)"
            c = db.cursor()
            c.execute(sql, vals)
            c.close()
        response = f"{cart_order_id} {session_id} {product_id} {quantity} {time_now}"


    ####
    if environ['PATH_INFO'] == "/update":
        product_id = int(input_list["product_id"])
        quantity = int(input_list["quantity"])
        db.query(f"SELECT cart_order_id FROM cart_order WHERE session_id = '{session_id}' and status is NULL")
        r = db.store_result()
        row = r.fetch_row(maxrows=1, how=1)[0]
        cart_order_id = row["cart_order_id"]
        if quantity == 0:
            sql = f"DELETE FROM cart_order_product WHERE cart_order_id = {cart_order_id} and product_id = {product_id}"
        else:
            sql = f"UPDATE cart_order_product SET quantity = {quantity} WHERE cart_order_id = {cart_order_id} and product_id = {product_id}"
        c = db.cursor()
        c.execute(sql)
        c.close()
        response = f"{cart_order_id} {session_id} {product_id} {quantity} {time_now}"


    ####
    elif environ['PATH_INFO'] == "/total":
        #curl -X POST -H "Content-Type: application/json" --data '{"session_id": "123"}' https://www.catalystcreativearts.com/cart-api/total
        sub_query = f"SELECT cart_order_id FROM cart_order WHERE session_id = '{session_id}' and status is NULL"
        try:
            db.query(f"SELECT SUM(quantity) AS sum FROM cart_order_product WHERE cart_order_id = ({sub_query})")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            number_of_items = int(row["sum"])
        except:
            number_of_items = 0
        try:
            db.query(f"SELECT sum(a.quantity * b.price) as subtotal from cart_order_product a, products b where a.product_id = b.pid and a.cart_order_id = ({sub_query})")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            subtotal = int(row["subtotal"])
        except:
            subtotal = 0

        snapshot = { "number_of_items": number_of_items, "subtotal": subtotal }
        snapshot = json.dumps(snapshot)
        response = str(snapshot)
 

    ####
    elif environ['PATH_INFO'] == "/list":
        #curl -X POST -H "Content-Type: application/json" --data '{"session_id": "123"}' https://www.catalystcreativearts.com/cart-api/list
        try:
            db.query(f"SELECT cart_order_id FROM cart_order WHERE session_id = '{session_id}' and status is NULL")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            cart_order_id = int(row["cart_order_id"])

            db.query(f"SELECT b.product_id as pid, b.quantity \
                FROM cart_order a, cart_order_product b \
                WHERE a.cart_order_id = b.cart_order_id \
                AND a.cart_order_id = {cart_order_id}")
            r = db.store_result()
            rows = r.fetch_row(maxrows=100, how=1)
            # ({'pid': 1, 'quantity': 6}, {'pid': 2, 'quantity': 4})
        except:
            rows = {}

        print("rows", rows)

        if len(rows) == 0:
            response = "cart empty"
            return [response.encode()]
 
        pids = []
        quantities = {}
        for obj in rows:
            p = obj['pid']
            #print(f"p: {p}")
            pids.append(p)
            quantities[p] = obj['quantity']

        print("quantities", quantities)
        print("pids", pids)

        pids = str(pids).strip('[').strip(']')

        print("pids", pids)

        db.query(f"select * from products where pid in ({pids})")
        r = db.store_result()
        rows = r.fetch_row(maxrows=100, how=1)

        rows_copy = list(rows)
        count = 0
        for obj in rows:
            p = obj['pid']
            rows_copy[count]['quantity'] = quantities[p]
            count += 1

        y = json.dumps(rows_copy)
        response = str(y)

        # Use valuesfrom keywords array to build a "related products" list


    else:
        response = "Default error"


    return [response.encode()]

