create table airport
	(airport_code		varchar(15),
	 name		varchar(30),
	 city       varchar(10),
     country    varchar(10),
     type       varchar(15),
	 primary key (airport_code)
    );

create table airline
    (name       varchar(30),
    primary key (name));

create table airplane
    (ID     varchar(15),
     airline_name   varchar(30),
     number_of_seats    int,
     manufacturer   varchar(20),
     age            int,
     primary key (ID),
     foreign key (airline_name) references airline(name)
     );

create table flight
    (flight_number  varchar(15),
     airplane_id    varchar(15),
     departure_date_time datetime,
     departure_airport_code  varchar(15),
     arrival_date_time   datetime,
     arrival_airport_code   varchar(15),
     base_price      decimal(19,2),
     status   varchar(8),
     airline_name    varchar(30),
     primary key (airline_name, flight_number, departure_date_time),
     foreign key (airline_name) references airline(name),
     foreign key (departure_airport_code) references airport(airport_code),
     foreign key (arrival_airport_code) references airport(airport_code),
     foreign key (airplane_id) references airplane(ID)
    );

create table ticket
    (ID             varchar(20),
     travel_class   varchar(15),
     airline_name   varchar(30),
     flight_number  varchar(15),
     departure_date_time    datetime,
     primary key (ID),
     foreign key (airline_name, flight_number, departure_date_time) references flight(airline_name, flight_number, departure_date_time)
     );

create table customer
    (email      varchar(20),
     name       varchar(30),
     customer_password   varchar(32),
     building_number    varchar(5),
     street             varchar(15),
     city               varchar(15),
     state              varchar(2),
     phone_number   varchar(10),
     passport_number    varchar(20),
     passport_expiration    varchar(20),
     passport_country   varchar(15),
     date_of_birth      date,
     primary key (email)
    );

create table purchases
    (ticket_id      varchar(20),
     sold_price     decimal(19, 2),
     date_time      datetime,
     customer_email varchar(20),
     card_type      varchar(6),
     card_number    varchar(16),
     name_on_card   varchar(30),
     card_expiration    varchar(20),
     primary key(ticket_id, customer_email),
     foreign key (ticket_id) references ticket(ID),
     foreign key (customer_email) references customer(email)
    );

create table airline_staff
    (username       varchar(30),
     user_password       varchar(32),
     first_name     varchar(20),
     last_name      varchar(20),
     date_of_birth  date,
     airline_name   varchar(15),
     primary key (username),
     foreign key (airline_name) references airline(name)
     );

create table airline_staff_phones
    (username       varchar(30),
     phone_number    varchar(10),
     primary key (username, phone_number),
     foreign key (username) references airline_staff(username)
    );

create table ratings
    (customer_email     varchar(20),
     ticket_id			varchar(20),
     rating             int,
     comment            varchar(255),
     primary key (customer_email, ticket_id),
     foreign key (customer_email, ticket_id) references purchases(customer_email, ticket_id)
     );

create table comments
    (customer_email     varchar(20),
     ticket_id			varchar(20),
     customer_comment            varchar(255),
     primary key (customer_email, ticket_id),
     foreign key (customer_email, ticket_id) references purchases(customer_email, ticket_id)
     );
