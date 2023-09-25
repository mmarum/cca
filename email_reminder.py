import json
import datetime
import MySQLdb
import requests


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def get_tomorrow_iso():
    today = datetime.datetime.today()
    tomorrow = today + datetime.timedelta(days=1)
    tomorrow_iso = tomorrow.strftime("%Y-%m-%d")
    return tomorrow_iso


def get_events():
    query = f"select eid, edatetime as date, title, location from events where edatetime like '{get_tomorrow_iso()}%'"
    #print("query", query)
    db.query(query)
    r = db.store_result()
    rows = r.fetch_row(maxrows=100, how=1)
    #print("rows", rows)
    return rows


def get_orders(eid):
    query = f"select email, CONCAT(first_name, ' ', last_name) as name from orders where eid = {eid}"
    #print("query", query)
    db.query(query)
    r = db.store_result()
    rows = r.fetch_row(maxrows=100, how=1)
    #print("rows", rows)
    return rows


def send_email(payer_info):
    url = "https://www.catalystcreativearts.com/email/submit"
    data = {
        "subject": "Event Reminder: Catalyst Creative Arts", 
        "content": "Reminder", 
        "payer_info": f"{json.dumps(payer_info, indent=4)}"
    }
    headers = {"Content-Type": "text/html"}
    r = requests.post(url=url, json=data, headers=headers, 
        auth=('catalystemail', passwd["catalystemail"]))


def stitch_and_send():
    events = get_events()
    for event in events:
        #print("event", event)
        orders = get_orders(event["eid"])
        for order in orders:
            #print("order", order)
            data = {**event, **order}

            this_date = str(data["date"])
            data["date"] = this_date

            # TEMPORARY FOR TESTING:
            #data["email"] = "mmarum@gmail.com"

            print("data", data)
            send_email(data)


passwd = json.loads(read_file("data/passwords.json"))
db = MySQLdb.connect(host="localhost", user="catalystcreative_cca", 
    passwd=passwd["catalystcreative_cca"], db="catalystcreative_arts")


stitch_and_send()

db.close()

