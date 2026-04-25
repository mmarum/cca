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


def post_input_mgr_1(post_input):
    data_object = {}
    post_input_list = post_input.split("&")
    for item in post_input_list:
        key, val = item.split("=")
        if key == "submit":
            continue
        data_object[key] = val
    return data_object


def post_input_mgr_2(post_input):
	post_input_array = post_input.split('------')
	data_object = {}
	data_array = []
	for d in post_input_array:
	    post_data_key = re.sub(r'^.*name="(.*?)".*$', r"\1", d, flags=re.DOTALL).strip()
	    post_data_val = re.sub(r'^.*name=".*?"(.*)$', r"\1", d, flags=re.DOTALL).strip()
	    if len(post_data_key) > 1 \
	        and not post_data_key.startswith('WebKitForm') \
	        and post_data_key != "submit" \
	        and not post_data_val.startswith('-----'):

	        data_object[post_data_key] = post_data_val
	        data_array.append(post_data_val)
	return {
	    "data_object": data_object,
	    "data_array": data_array
	}

