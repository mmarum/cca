from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, FileField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url
from datetime import datetime

# https://wtforms.readthedocs.io/en/stable/fields.html

"""
| eid         | int(11)      | NO   | PRI | NULL                | auto_increment                |
| datetime    | timestamp    | NO   |     | current_timestamp() | on update current_timestamp() |
| title       | varchar(200) | NO   |     | NULL                |                               |
| duration    | varchar(20)  | NO   |     | NULL                |                               |
| price       | int(11)      | NO   |     | NULL                |                               |
| elimit      | int(11)      | YES  |     | NULL                |                               |
| location    | varchar(200) | NO   |     | NULL                |                               |
| image       | varchar(200) | YES  |     | NULL                |                               |
| description | varchar(500) | YES  |     | NULL                |                               |

"""

class EventsForm(Form):
    eid = HiddenField("eid", description="eid")
    datetime = DateTimeField("Date", description="Date", format="%Y-%m-%d %H:%M:%S")
    title = StringField("Title", description="Title")
    duration = StringField("Duration", description="Duration")
    price = StringField("Price", description="Price")
    elimit = StringField("Limit", description="Limit")
    location = StringField("Location", description="Location")
    image = HiddenField("Image Path", description="Image Path")
    description = TextAreaField("Description", description="Description")
    submit = SubmitField("Next", description="Next")

class ImageForm(Form):
    eid = HiddenField("eid", description="eid")
    image = FileField("Upload File")
    submit = SubmitField("Submit", description="Submit")

