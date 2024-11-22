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

# TODO: the lists below need to be de-duped or automated

f = open("data/upcoming_event_ids.json", "r")
upcoming_event_ids = json.loads(f.read())
f.close()

upcoming = [f"event/{x}" for x in upcoming_event_ids]

groups = {
"pages": [
    "index",
    "calendar",
    "private-events", 
    "specialty-classes",
    "gift-card", 
    #"about-contact", 
    "about-us", 
    "media",
    #"reviews",
    #"custom-built",
    "after-school",
    #"summer-camp",
    "art-camp",
    "wheel-wars",
    "paint-wars",
    "3-wednesdays-workshop",
    "cart",
    "build-individual-event",
    "crafts-gallery",
    "listening-room",
    "pottery-lessons",
    "after-school-pottery",
    #"pottery-lessons-test",
    "community-events",
    "mural-2024"
  ],
"galleries": [
    "commissioned-art",
    "acrylic-painting",
    "watercolor-painting",
    "paint-your-pet",
    "artist-guided-family-painting",
    #"alcohol-ink",
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
  ],
"events": upcoming
}

sitemap_pages = groups["pages"]
sitemap_galleries = groups["galleries"]
sitemap_events = groups["events"]
sitemap_list = sitemap_pages + sitemap_galleries + sitemap_events
#sitemap_list.remove('home')
sitemap_list.remove('cart')
sitemap_list.remove('build-individual-event')
sitemap_list.insert(0, '')
#print("sitemap_list", sitemap_list)


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


sitemap_content = ""
for x in sitemap_list:
    if x == "":
        sitemap_content += f"{domain}/\n"
    else:
        sitemap_content += f"{domain}/{x}.html\n"
write_file("../www/sitemap.txt", sitemap_content)
#print("sitemap_content\n", sitemap_content)


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

