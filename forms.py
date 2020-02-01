from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, FileField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url
from datetime import datetime

# https://wtforms.readthedocs.io/en/stable/fields.html

#default_date_time = "2020-02-01-10-00"

class EventsForm(Form):
    #date_time = DateTimeField("Date Time", description="DateTime", default=default_date_time, format="%Y-%m-%d-%H-%M")
    eid = HiddenField("eid", description="eid")
    date = StringField("Date", description="Date")
    time = StringField("Time", description="Time")
    title = StringField("Title", description="Title")
    duration = StringField("Duration", description="Duration")
    price = StringField("Price", description="Price")
    limit = StringField("Limit", description="Limit")
    location = StringField("Location", description="Location")
    image_path = HiddenField("Image Path", description="Image Path")
    description = TextAreaField("Description", description="Description")
    submit = SubmitField("Next", description="Next")

class ImageForm(Form):
    eid = HiddenField("eid", description="eid")
    image = FileField("Upload File")
    submit = SubmitField("Submit", description="Submit")

class BookingForm(Form):
    eid = HiddenField("eid", description="eid")
    name = StringField("Name", description="Name")
    phone = StringField("Phone", description="Phone")
    quantity = StringField("Quantity", description="Quantity")
    receipt = HiddenField("Receipt", description="Receipt")
    submit = SubmitField("Submit", description="Submit")

