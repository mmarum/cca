import json


# jinja custom filters pass the filtered value as first arg: ("extra_data")

def get_inventory(extra_data, key):
    #print("extra_data", extra_data)
    #print("key", key)
    data = json.loads(extra_data)
    #print(data)
    inv = int(data["spots_remaining"][key])
    #print(inv)
    return inv


def slugify(var):
    var = var.lower()
    var = "_".join(var.split(" ")[:8])
    var = var.replace("?", "")
    var = var.replace(",", "")
    var = var.replace(":", "")
    return var

