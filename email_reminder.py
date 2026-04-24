import json
import datetime
import requests
from sql_mgr import query
from tools import read_file


def get_tomorrow_iso():
    today = datetime.datetime.today()
    tomorrow = today + datetime.timedelta(days=1)
    tomorrow_iso = tomorrow.strftime("%Y-%m-%d")
    return tomorrow_iso


def get_events():
    sql = f"select eid, edatetime as date, title, location from events where edatetime like '{get_tomorrow_iso()}%'"
    rows = query(sql)
    return rows


def get_orders(eid):
    sql= f"select email, CONCAT(first_name, ' ', last_name) as name from orders where eid = {eid}"
    rows = query(sql)
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

