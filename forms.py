from wtforms import DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url

class AdminForm():
    date_time = DateTimeField('Date Time', description='Date Time')
    one = StringField('One', description='One')
    two = StringField('Two', description='Two')
    three = StringField('Three', description='Three')
    submit = SubmitField('Submit', description='Submit')

