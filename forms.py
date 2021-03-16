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
    location = StringField("Location", description="Location", default="400 E. Division St. Ste 100 Arlington, TX 76011")
    image = HiddenField("Image Path", description="Image Path")
    description = TextAreaField("Description", description="Description")
    price_text = StringField("Variable time or price", description="Variable time or price")
    # (time) Feb 6 3-5pm, Feb 6 6-8pm, Feb 7 1-3pm, Feb 7 4-6pm, test
    # (price) one red @ $10, two blue @ $5, a bird @ $20
    tags = StringField("Tags", description="Tags: home, cart, fluid-art, alcohol-ink OR invisible")
    extra_data = HiddenField("", description="")
    submit = SubmitField("Next", description="Next")
    #abc = StringField('abc', [InputRequired()], render_kw={"placeholder": "test"})

class ImageForm(Form):
    eid = HiddenField("eid", description="eid")
    image = FileField("Upload File")
    submit = SubmitField("Submit", description="Submit")

class RegistrationForm(Form):
    rid = HiddenField("rid", description="rid")
    order_id = HiddenField("Order ID", description="Order ID")
    camper1_name = StringField("Camper Name", description="Camper Name")
    camper1_age = StringField("Camper Age", description="Camper Age")
    camper1_grade = StringField("Camper Grade", description="Camper Grade")
    camper2_name = StringField("Camper 2 Name", description="Camper 2 Name")
    camper2_age = StringField("Camper 2 Age", description="Camper 2 Age")
    camper2_grade = StringField("Camper 2 Grade", description="Camper 2 Grade")
    camper3_name = StringField("Camper 3 Name", description="Camper 3 Name")
    camper3_age = StringField("Camper 3 Age", description="Camper 3 Age")
    camper3_grade = StringField("Camper 3 Grade", description="Camper 3 Grade")
    parent_name = StringField("Name", description="Name")
    parent_address = StringField("Address", description="Address")
    parent_city = StringField("City", description="City")
    parent_state = StringField("State", description="State")
    parent_zip = StringField("Zip Code", description="Zip Code")
    parent_email = StringField("Email", description="Email")
    parent_phone = StringField("Phone", description="Phone")
    parent_em_name = StringField("Emergency Contact Person", description="Emergency Contact Person")
    parent_em_phone = StringField("Emergency Phone", description="Emergency Phone")
    pickup1_name = StringField("Name", description="Name")
    pickup1_phone = StringField("Phone", description="Phone")
    pickup2_name = StringField("Name 2", description="Name 2")
    pickup2_phone = StringField("Phone 2", description="Phone 2")
    session1 = BooleanField("Week 1: June 22 - 26, 2020", description="session 1")
    session2 = BooleanField("Week 2: July 13 - 17, 2020", description="session 2")
    treatment_permission = BooleanField("Emergency Treatment Permission", description="")
    photo_release = BooleanField("Photo/Social Media Release", description="")
    signature = StringField("Signature", description="")
    submit = SubmitField("Submit", description="Submit")


class ProductsForm (Form):
    pid = HiddenField("pid", description="")
    name = StringField("Name", description="")
    description = TextAreaField("Description", description="")
    image_path_array = HiddenField("Image Path Array", description="Add one or multiple images")
    inventory = StringField("Inventory", description="How many items remaining in stock. This value will change automatically as people buy")
    price = StringField("Price", description="Product price before discounts. This can be overridden")
    keywords_array = StringField("Keywords Array", description="Comma-separated list of descriptive one-word keywords")
    active = StringField("Active", description="")
    submit = SubmitField("Next", description="Next")

