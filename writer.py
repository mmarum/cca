import requests
import os
import sys
import json

"""
cron:
source /home/catalystcreative/virtualenv/app/3.6/bin/activate; cd /home/catalystcreative/app; python writer.py pages
source /home/catalystcreative/virtualenv/app/3.6/bin/activate; cd /home/catalystcreative/app; python writer.py galleries
"""

domain = "https://www.catalystcreativearts.com"


def read_file(file_name):
    f = open(file_name, "r")
    content = f.read()
    f.close()
    return content


def write_file(file_name, content):
    f = open(file_name, "w")
    f.write(content)
    f.close()


valid_pages = json.loads(read_file("data/valid-pages.json"))
valid_galleries = json.loads(read_file("data/valid-galleries.json"))
upcoming_event_ids = json.loads(read_file("data/upcoming_event_ids.json"))
upcoming = [f"event/{x}" for x in upcoming_event_ids]

groups = {
    "pages": valid_pages,
    "galleries": valid_galleries,
    "events": upcoming
}

sitemap_pages = groups["pages"]
sitemap_galleries = groups["galleries"]
sitemap_events = groups["events"]
sitemap_list = sitemap_pages + sitemap_galleries + sitemap_events
sitemap_list.remove('cart')
sitemap_list.remove('build-individual-event')
sitemap_list.insert(0, '')

sitemap_content = ""
for x in sitemap_list:
    if x == "":
        sitemap_content += f"{domain}/\n"
    else:
        sitemap_content += f"{domain}/{x}.html\n"
write_file("../www/sitemap.txt", sitemap_content)


user = "catalystcreative"
passw = json.loads(read_file("data/passwords.json"))[user]


def get_page_contents(path):
    r = requests.get(f'{domain}/app/{path}', auth=(f'{user}', f'{passw}'))
    print(r.url)
    print(r.status_code)
    if r.status_code == 200 and len(r.text) > 10:
        return r.text
    else:
        print(f'get_page_contents fail: {domain}/app/{path} {r.status_code}')
        raise ValueError(f'get_page_contents fail: {domain}/app/{path} {r.status_code}')


def scrape_and_write(path):
    page_contents = "x"
    try:

        #try:
        #    page_contents = str(get_page_contents(path).encode())
        #except:
        #    page_contents = get_page_contents(path)
        page_contents = get_page_contents(path)

        if len(page_contents) > 10:
            if path in ["cart", "some-other"]:
                write_file(f"../www/{path}/index.html", page_contents)
            else:
                write_file(f"../www/{path}.html", page_contents)
        else:
            print(f'page_contents failure: {path}')
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

