from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, FileField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url
from datetime import datetime

# https://wtforms.readthedocs.io/en/stable/fields.html

class EventsForm(Form):
    eid = HiddenField("eid", description="eid")
    edatetime = DateTimeField("Date", description="Date", format="%Y-%m-%d %H:%M:%S")
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

