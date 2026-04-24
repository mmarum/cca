import requests
import os
import sys
import json
from tools import read_file, write_file


domain = "https://www.catalystcreativearts.com"

headers = {
    "User-Agent": "Mozilla/5.0"
}

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


def scrape_and_write(path):
    r = requests.get(f'{domain}/app/{path}', auth=(f'{user}', f'{passw}'), headers=headers)
    print(r.url, r.status_code)
    if r.status_code == 200 and len(r.text) > 10:
        if path == "cart":
        	path += "/index"
        write_file(f"../www/{path}.html", r.text)
    else:
        raise ValueError('scrape_and_write fail')


def loop_thru_pages(mode):
    if mode not in ["pages", "galleries"]:
    	raise ValueError('must be pages or galleries')
    for item in groups[mode]:
        scrape_and_write(item)


if __name__ == '__main__':
	mode = sys.argv[1]
	loop_thru_pages(mode)
	#page = sys.argv[1]
    #scrape_and_write(page)


