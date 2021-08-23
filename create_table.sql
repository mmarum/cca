CREATE TABLE events (
eid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
edatetime datetime UNIQUE NOT NULL,
title VARCHAR (200) NOT NULL,
duration VARCHAR (20) NOT NULL,
price INT NOT NULL,
elimit INT,
location VARCHAR (200) NOT NULL,
image VARCHAR (200),
description VARCHAR (5000),
price_text VARCHAR (2500),
pinned VARCHAR (1000),
extra_data VARCHAR (5000),
);

CREATE TABLE orders (
id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
order_id VARCHAR (20) UNIQUE NOT NULL,
eid INT NOT NULL,
create_time VARCHAR (200) NOT NULL,
email VARCHAR (200) NOT NULL,
first_name VARCHAR (200),
last_name VARCHAR (200),
quantity INT NOT NULL,
cost VARCHAR (20) NOT NULL,
paid VARCHAR (20) NOT NULL,
guest_list VARCHAR(500),
FOREIGN KEY (eid) REFERENCES events(eid)
);

CREATE TABLE registration (
rid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
order_id VARCHAR (20),
camper1_name VARCHAR (200) NOT NULL,
camper1_age INT NOT NULL,
camper1_grade INT NOT NULL,
camper2_name VARCHAR (200),
camper2_age INT,
camper2_grade INT,
camper3_name VARCHAR (200),
camper3_age INT,
camper3_grade INT,
parent_name VARCHAR (200) NOT NULL,
parent_address VARCHAR (200) NOT NULL,
parent_city VARCHAR (200) NOT NULL,
parent_state VARCHAR (200) NOT NULL,
parent_zip VARCHAR (200) NOT NULL,
parent_email VARCHAR (200) NOT NULL,
parent_phone VARCHAR (200) NOT NULL,
parent_em_name VARCHAR (200),
parent_em_phone VARCHAR (200),
pickup1_name VARCHAR (200),
pickup1_phone VARCHAR (200),
pickup2_name VARCHAR (200),
pickup2_phone VARCHAR (200),
session_detail VARCHAR(500),
session1 TINYINT (1),
session2 TINYINT (1),
treatment_permission TINYINT (1),
photo_release TINYINT (1),
signature VARCHAR (200)
);

CREATE TABLE products (
pid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
name VARCHAR (200) NOT NULL,
description VARCHAR (2000),
image_path_array VARCHAR (1000),
inventory INT,
active TINYINT (1),
price VARCHAR (20),
keywords_array VARCHAR (500)
);

CREATE TABLE cart_order (
cart_order_id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
session_id VARCHAR (20) NOT NULL,
create_date datetime,
checkout_date datetime,
ship_date datetime,
status VARCHAR (50)
);

CREATE TABLE cart_order_product (
cart_order_id INT NOT NULL,
product_id INT NOT NULL,
quantity INT NOT NULL
);
