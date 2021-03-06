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

# curl -X POST -H "Content-Type: application/json" --data '{"session_id": "123", "product_id": 1, "quantity": 1}' https://www.catalystcreativearts.com/cart-api/add
# Sample response: {session_id: "123", product_id: 1, quantity: 1}
# cart_products: cid pid quantity price_override
# cart: cid session_id create_time payment_time order_id

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
            # CHECK to see if there's an existing cart for this session_id
            db.query(f"SELECT cid FROM cart WHERE session_id = '{session_id}'")
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

        try:
            # CHECK to see if user already added this product
            db.query(f"SELECT id, quantity FROM cart_products WHERE cid = {cid} AND pid = {product_id}")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            cp_id = row["id"]
            cp_quantity = row["quantity"]
            # There should only ever be ONE row returned from above

            new_quantity = quantity + cp_quantity

            # IF pid already exists for this cid then UPDATE
            sql = f"UPDATE cart_products SET quantity = {new_quantity} WHERE id = {cp_id}"
            c = db.cursor()
            c.execute(sql)
            c.close()

        except:
            # IF pid does NOT yet exist for this cid then INSERT
            # insert into cart_products (cid, pid, quantity) values (1, 1, 1);
            sql = f"INSERT INTO cart_products ({fields}) VALUES (%s, %s, %s)"
            c = db.cursor()
            c.execute(sql, vals)
            c.close()

        response = f"{cid} {session_id} {product_id} {quantity} {time_now}"


    ####
    if environ['PATH_INFO'] == "/update":

        product_id = int(input_list["product_id"])
        quantity = int(input_list["quantity"])

        db.query(f"SELECT cid FROM cart WHERE session_id = '{session_id}'")
        r = db.store_result()
        row = r.fetch_row(maxrows=1, how=1)[0]
        cid = row["cid"]

        db.query(f"SELECT id FROM cart_products WHERE cid = {cid} AND pid = {product_id}")
        r = db.store_result()
        row = r.fetch_row(maxrows=1, how=1)[0]
        cp_id = row["id"]

        if quantity == 0:
            sql = f"DELETE FROM cart_products WHERE id = {cp_id}"
        else:
            sql = f"UPDATE cart_products SET quantity = {quantity} WHERE id = {cp_id}"

        c = db.cursor()
        c.execute(sql)
        c.close()

        response = f"{cid} {session_id} {product_id} {quantity} {time_now}"


    ####
    elif environ['PATH_INFO'] == "/total":
        #curl -X POST -H "Content-Type: application/json" --data '{"session_id": "123"}' https://www.catalystcreativearts.com/cart-api/total
        sub_query = f"SELECT cid FROM cart WHERE session_id = '{session_id}'"
        try:
            db.query(f"SELECT SUM(quantity) AS sum FROM cart_products WHERE cid = ({sub_query})")
            r = db.store_result()
            row = r.fetch_row(maxrows=1, how=1)[0]
            number_of_items = int(row["sum"])
        except:
            number_of_items = 0
        try:
            db.query(f"SELECT sum(a.quantity * b.price) as subtotal from cart_products a, products b where a.pid = b.pid and a.cid = ({sub_query})")
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
            sub_query = f"SELECT cid FROM cart WHERE session_id = '{session_id}'"
            #db.query(f"SELECT a.*, b.* FROM cart_products a, products b WHERE a.pid = b.pid AND a.cid = ({sub_query})")
            db.query(f"select pid, quantity from cart_products where cid = ({sub_query})")
            r = db.store_result()
            rows = r.fetch_row(maxrows=100, how=1)
            # ({'pid': 1, 'quantity': 6}, {'pid': 2, 'quantity': 4})
        except:
            rows = {}

        print("rows", rows)

        if not rows:
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

