#!/usr/bin/bash

# This script copies files into the git repo

cp /home/catalystcreative/app/*.* /home/catalystcreative/app/cca/
cp /home/catalystcreative/app/templates/*.* /home/catalystcreative/app/cca/templates/
cp /home/catalystcreative/app/data/*.html /home/catalystcreative/app/cca/app_data/
cp /home/catalystcreative/contact/contact.py /home/catalystcreative/app/cca/contact.py
cp /home/catalystcreative/order/order.py /home/catalystcreative/app/cca/order.py
cp /home/catalystcreative/registration/registration.py /home/catalystcreative/app/cca/registration.py
cp /home/catalystcreative/registration/reg_form.py /home/catalystcreative/app/cca/reg_form.py
cp /home/catalystcreative/registration/templates/*.* /home/catalystcreative/app/cca/registration_templates/
cp /home/catalystcreative/email/email.py /home/catalystcreative/app/cca/email.py
cp /home/catalystcreative/cart-api/cart.py /home/catalystcreative/app/cca/cart.py
cp /home/catalystcreative/shop/shop.py /home/catalystcreative/app/cca/shop.py
cp /home/catalystcreative/webhook/webhook.py /home/catalystcreative/app/cca/webhook.py

cp /home/catalystcreative/checkout/checkout.py /home/catalystcreative/app/cca/checkout.py
cp /home/catalystcreative/checkout/templates/*.* /home/catalystcreative/app/cca/checkout_templates/
cp /home/catalystcreative/www/checkout*.* /home/catalystcreative/app/cca/checkout_templates/

cp /home/catalystcreative/store-checkout/store_checkout.py /home/catalystcreative/app/cca/store_checkout.py
cp /home/catalystcreative/store-checkout/templates/*.* /home/catalystcreative/app/cca/store-checkout_templates/
cp /home/catalystcreative/www/store-checkout*.* /home/catalystcreative/app/cca/store-checkout_templates/


