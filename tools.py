import re


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def write_file(file_name, content):
    f = open(file_name, "w", encoding="utf-8")
    f.write(content)
    f.close()
    return True


def manage_post_input(post_input):
    data_object = {}
    post_input_list = post_input.split("&")
    for item in post_input_list:
        key, val = item.split("=")
        if key == "submit":
            continue
        data_object[key] = val
    return data_object
