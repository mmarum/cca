from wtforms import Form, DateTimeField, StringField, SubmitField, HiddenField, RadioField, BooleanField, TextAreaField, FileField, validators
from wtforms.validators import InputRequired, DataRequired, ValidationError, url

class RegistrationForm(Form):
    rid = HiddenField("rid", description="rid")
    order_id = HiddenField("Order ID", description="Order ID")
    camper1_name = StringField("Participant Name", [validators.required()], description="Participant Name")
    camper1_age = StringField("Participant Age", [validators.required()], description="Participant Age")
    camper1_grade = StringField("Participant Grade", [validators.required()], description="Participant Grade")
    camper2_name = StringField("Participant 2 Name", description="Participant 2 Name")
    camper2_age = StringField("Participant 2 Age", description="Participant 2 Age")
    camper2_grade = StringField("Participant 2 Grade", description="Participant 2 Grade")
    camper3_name = StringField("Participant 3 Name", description="Participant 3 Name")
    camper3_age = StringField("Participant 3 Age", description="Participant 3 Age")
    camper3_grade = StringField("Participant 3 Grade", description="Participant 3 Grade")
    parent_name = StringField("Name", [validators.required()], description="Name")
    parent_address = StringField("Address", [validators.required()], description="Address")
    parent_city = StringField("City", [validators.required()], description="City")
    parent_state = StringField("State", [validators.required()], description="State")
    parent_zip = StringField("Zip Code", [validators.required()], description="Zip Code")
    parent_email = StringField("Email", [validators.required()], description="Email")
    parent_phone = StringField("Phone", [validators.required()], description="Phone")
    parent_em_name = StringField("Emergency Contact Person", description="Emergency Contact Person")
    parent_em_phone = StringField("Emergency Phone", description="Emergency Phone")
    pickup1_name = StringField("Name", description="Name")
    pickup1_phone = StringField("Phone", description="Phone")
    pickup2_name = StringField("Name 2", description="Name 2")
    pickup2_phone = StringField("Phone 2", description="Phone 2")
    session1 = BooleanField("Week 1: June 22 - 26, 2020", description="session 1")
    session2 = BooleanField("Week 2: July 13 - 17, 2020", description="session 2")
    treatment_permission = BooleanField("Emergency Treatment Permission", [validators.required()], description="")
    photo_release = BooleanField("Photo/Social Media Release", [validators.required()], description="")
    signature = StringField("Signature", [validators.required()], description="")
    submit = SubmitField("Continue", description="Continue")


class RegFormWheelWars(Form):
    rid = HiddenField("rid", description="rid")
    order_id = HiddenField("Order ID", description="Order ID")
    """
    event_date
    name
    phone_number
    age
    city
    career
    Can you use a pottery wheel?
    Brief description of pottery experience:
    Brief description of the pottery items you have made on the wheel:
    Future pottery Interests:
    Attach several photos of your pottery wheel work. (Is that possible?)
    Add Photo/Social Media Release
    """

