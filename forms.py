from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url
from datetime import datetime

# https://wtforms.readthedocs.io/en/stable/fields.html

default_date_time = "2020-02-01-10-00"

class AdminForm(Form):
    #date_time = DateTimeField('Date Time', description='DateTime', default=default_date_time, format='%Y-%m-%d-%H-%M')
    eid = HiddenField('eid', description='eid')
    date_time = StringField('Date Time', description='DateTime')
    one = StringField('One', description='One')
    two = StringField('Two', description='Two')
    three = TextAreaField('Three', description='Three')
    submit = SubmitField('Submit', description='Submit')

