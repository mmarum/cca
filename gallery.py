import os
import sys
import json
from sql_mgr import query
from tools import read_file

# mysql -u catalystcreative_cca catalystcreative_66 -p
# update piwigz_categories set comment = '' where id = 13;


class Gallery:

    def __init__(self, category=1):
        self.category = category

    def get_gallery(self):

        sql = f"SELECT name, comment FROM piwigz_categories WHERE id = {self.category}"
        try:
            row = query(sql)
            return row
        except:
            return ""

    def get_images(self):

        sql = f"SELECT i.id, i.file, i.name, i.width, i.height, i.path \
            FROM piwigz_images i, piwigz_image_category c \
            WHERE c.image_id = i.id AND c.category_id = {self.category} \
            ORDER BY c.rank"
        allrows = query(sql)
        return allrows


"""
select id, name from piwigz_categories;
+----+---------------------+
| id | name                |
+----+---------------------+
|  1 | Acrylic Painting    |
|  2 | Watercolor Painting |
|  3 | Paint Your Pet      |
|  4 | Fused Glass         |
|  5 | Resin Art           |
|  6 | Fluid Art           |
|  7 | Summer Art Camp     |
+----+---------------------+
"""

