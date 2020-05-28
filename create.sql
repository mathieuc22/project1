
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL
);
ALTER TABLE table_name
ADD COLUMN isadmin group boolean false;



CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    rating DECIMAL NOT NULL,
    content VARCHAR NOT NULL,
    date TIMESTAMP NOT NULL,
    isbn VARCHAR REFERENCES books,
    user_id INTEGER REFERENCES users
);
