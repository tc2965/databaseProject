INSERT INTO airline VALUES
('China Eastern');

INSERT INTO airport VALUES
('JFK', 'John F. Kennedy', 'NYC', 'USA', 'International'),
('PVG', 'Shanghai Pudong', 'Shanghai', 'China', 'International');

INSERT INTO customer VALUES
('test1@gmail.com', 'Saimanasa Juluru', 'test1gmailPword#', '55', 'Clark Street', 'Brooklyn', 'NY', '2033336666', '123456789', '2032', 'USA', '20001102'),
('test2@aol.com', 'Tiffany Chan', 'test2aolPword#', '101', 'Johnson Street', 'Brooklyn', 'NY', '2122223344', '987654321', '2029', 'USA', '20011001'),
('test3@yahoo.com', 'Allison Yang', 'test3yahooPword#', '140', 'E 14th Street', 'New York', 'NY', '6469996565', '246802468', '2030', 'USA', '20010609');

INSERT INTO airplane VALUES
('737', 'China Eastern', '149', 'Boeing', '12'),
('A380', 'China Eastern', '853	', 'Airbus', '5'),
('777', 'China Eastern', '313', 'Boeing', '10');

INSERT INTO airline_staff VALUES
('standardUsername', 'letMeInThx333', 'John', 'Smith', '19870330', 'China Eastern');

INSERT INTO airline_staff_phones VALUES('standardUsername', '4546660900');

INSERT INTO flight VALUES('CH200', '737', '2022-04-06 14:00:09', 'JFK', '2022-04-07 23:00:09', 'PVG', '300.99', 'On Time', 'China Eastern'),
('XY300', 'A380', '2022-04-06 19:56:45', 'JFK', '2022-04-07 05:00:00', 'PVG', '333.99', 'Delay', 'China Eastern'),
('ER400', '777', '2022-04-06 12:30:12', 'JFK', '2022-04-07 21:27:00', 'PVG', '415.30', 'On Time', 'China Eastern');

INSERT INTO ticket VALUES('ABC1234567', 'Economy', 'China Eastern', 'CH200', '2022-04-06 14:00:09'),
('DEF7654321', 'Business', 'China Eastern', 'XY300', '2022-04-06 19:56:45'),
('XYZ7778880', 'First', 'China Eastern', 'ER400', '2022-04-06 12:30:12');

INSERT INTO purchases VALUES('ABC1234567', '300.99', '2022-01-06 13:13:29', 'test1@gmail.com', 'Credit', '493028938', 'Saimanasa Juluru', '06/27'),
('DEF7654321', '333.99', '2021-12-13 11:20:29', 'test2@aol.com', 'Debit', '904389041', 'Tiffany Chan', '09/28'),
('XYZ7778880', '6415.30', '2022-02-01 18:45:00', 'test3@yahoo.com', 'Credit', '897654123', 'Allison Yang', '11/02');