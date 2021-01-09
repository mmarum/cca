import json

def get_inventory(extra_data, key):
    print("key", key)
    data = json.loads(extra_data)
    print(data)
    inv = int(data["spots_remaining"][key])
    print(inv)
    return inv
