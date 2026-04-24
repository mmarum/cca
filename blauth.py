import json
import hashlib
from tools import read_file


def check_password(username):
    admin_users = json.loads(read_file("admin-credentials.json"))
    try:
        return admin_users[username]["passhash"]
    except:
        return "no such user"


def hashed_password(password):
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def logged_in(http_cookie):
    auth_success = False
    admin_creds = json.loads(read_file("admin-credentials.json"))
    http_cookie_list = http_cookie.split(";")
    for cookie in http_cookie_list:
        if "admin" in cookie:
            username, passhash = cookie.replace("admin=", "").strip().split(":")
            if passhash == admin_creds[username]["passhash"]:
                auth_success = True
    return auth_success


def login(data_object):
    username = data_object["username"]
    password = data_object["password"]
    stored_password = check_password(username)
    passhash = hashed_password(password)
    if passhash != stored_password:
        if stored_password == "no such user":
            return "no such user"
        else:
            return "wrong password"
    else:
        return { "login": "success", "username": username, "passhash": passhash }


if __name__ == '__main__':
    #http_cookie = 'session_id=4082731013075102.5; admin=mmarum:6df10d2c6858c4a9dc9b32d468777634'
    #logged_in(http_cookie)
    username = "catalystcreative"
    password = "PortSaintLucie4"
    print(login(username, password))

