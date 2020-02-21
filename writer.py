import requests
import os
import sys
import json

groups = {
"pages": [
    "home",
    "calendar",
    "private-events", 
    "about-contact", 
    "custom-built"
],
"galleries": [
    "commissioned-art",
    "after-school-summer-camp",
    "acrylic-painting",
    "watercolor-painting",
    "paint-your-pet",
    "artist-guided-family-painting",
    "alcohol-ink",
    "fluid-art",
    "handbuilt-pottery",
    "paint-your-own-pottery",
    "fused-glass",
    "leathercraft",
    "resin-crafts",
    "water-marbling",
    "specialty-classes",
    "custom-built"
]
}


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def write_file(file_name, content):
    f = open(file_name, "w")
    f.write(content)
    f.close()
    return True


user = "jedmarum"
passw = json.loads(read_file("data/passwords.json"))[user]


def get_page_contents(path):
    r = requests.get(f'http://www.jedmarum.com/app/{path}', auth=(f'{user}', f'{passw}'))
    if r.status_code == 200:
        return r.text


def scrape_and_write(scrape_path, write_path):
    try:
        page_contents = get_page_contents(scrape_path)
        if page_contents:
            write_file(f"../www/cca/{write_path}.html", page_contents)
        else:
            print('____ page_contents failure')
    except:
        print('page_contents OR write_file failure')


try:
    # "galleries" NEEDS TO BE CALLED VIA CRON
    if sys.argv[1] in ["pages", "galleries"]:
        group = sys.argv[1]
        print(group)
        for item in groups[group]:
            try:
                print(item)
                scrape_and_write(item, item)
            except:
                print('error-1')
                pass
    else:
        print('Needs to be pages or galleries')
except:
    print('error. probably no argument')
    #pass
