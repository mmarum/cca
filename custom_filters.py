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
