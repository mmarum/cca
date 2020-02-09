CREATE TABLE events (
eid INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
edatetime datetime UNIQUE NOT NULL,
title VARCHAR (200) NOT NULL,
duration VARCHAR (20) NOT NULL,
price INT NOT NULL,
elimit INT,
location VARCHAR (200) NOT NULL,
image VARCHAR (200),
description VARCHAR (500)
);
