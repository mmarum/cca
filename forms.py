from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, validators
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
    duration = StringField("Duration (Hours)", description="Duration")
    price = StringField("Price", description="Price")
    location = StringField("Location", description="Location")
    image = StringField("Image", description="Image")
    description = TextAreaField("Description", description="Description")
    submit = SubmitField("Submit", description="Submit")

