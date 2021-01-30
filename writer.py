import requests
import os
import sys
import json

"""
cron:
source /home/catalystcreative/virtualenv/app/3.6/bin/activate; cd /home/catalystcreative/app; python writer.py pages
source /home/catalystcreative/virtualenv/app/3.6/bin/activate; cd /home/catalystcreative/app; python writer.py galleries
"""

# TODO: the lists below need to be de-duped or automated

groups = {
"pages": [
    "home",
    "calendar",
    "private-events", 
    #"about-contact", 
    "about-us", 
    "custom-built",
    "after-school",
    "summer-camp",
    "wheel-wars",
    "3-wednesdays-workshop",
    "cart"
],
"galleries": [
    "commissioned-art",
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
    "pottery-painting",
    "string-art",
    "pottery-lessons"
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


user = "catalystcreative"
passw = json.loads(read_file("data/passwords.json"))[user]


def get_page_contents(path):
    r = requests.get(f'https://www.catalystcreativearts.com/app/{path}', auth=(f'{user}', f'{passw}'))
    print(r.url)
    if r.status_code == 200:
        print(r.status_code)
        return r.text
    else:
        raise ValueError(f'get_page_contents fail: {path} {r.status_code}')


def scrape_and_write(path):
    try:
        page_contents = get_page_contents(path)
        if len(page_contents) > 10:
            if path in ["cart", "some-other"]:
                write_file(f"../www/{path}/index.html", page_contents)
            else:
                write_file(f"../www/{path}.html", page_contents)
        else:
            print(f'____ page_contents failure: {path}')
    except:
        print(f'page_contents OR write_file failure: {path}')


try:
    # "galleries" NEEDS TO BE CALLED VIA CRON
    # "home" and "calendar" should also be on cron
    if sys.argv[1] in ["pages", "galleries"]:
        group = sys.argv[1]
        print(group)
        for item in groups[group]:
            try:
                print(item)
                scrape_and_write(item)
            except:
                print('error. bad scrape')
                #pass
    else:
        print('Needs to be pages or galleries')
        #pass
except:
    #print('error. probably no argument')
    pass

