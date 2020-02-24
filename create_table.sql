CREATE TABLE events (
eid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
edatetime datetime UNIQUE NOT NULL,
title VARCHAR (200) NOT NULL,
duration VARCHAR (20) NOT NULL,
price INT NOT NULL,
elimit INT,
location VARCHAR (200) NOT NULL,
image VARCHAR (200),
description VARCHAR (1000)
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
FOREIGN KEY (eid) REFERENCES events(eid)
);

