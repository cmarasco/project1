import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    db.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR NOT NULL, password VARCHAR NOT NULL);")
    db.execute("CREATE TABLE books (id SERIAL PRIMARY KEY, ibsn VARCHAR NOT NULL, title VARCHAR NOT NULL, \
                author VARCHAR NOT NULL, year INTEGER NOT NULL);")
    db.execute("CREATE TABLE reviews (id SERIAL PRIMARY KEY, stars INTEGER NOT NULL, review VARCHAR NOT NULL, \
                user_id INTEGER REFERENCES users, book_id INTEGER REFERENCES books);")
    #db.execute("CREATE TABLE reviews (id SERIAL PRIMARY KEY, stars INTEGER NOT NULL, review TEXT NOT NULL, \
    #            user_id INTEGER REFERENCES users, book_id INTEGER REFERENCES books);")

    f = open("books.csv")
    reader = csv.reader(f)
    #Columns, first is origin, the destination, and duration
    for ibsn, title, author, year in reader:
        #:variable means placeholder for that variable
        db.execute("INSERT INTO books (ibsn, title, author, year) VALUES (:ibsn, :title, :author, :year)",
            #Fills in placeholders
            {"ibsn": ibsn, "title": title, "author": author, "year": year})
    #Saving changes you made
    db.commit()

if __name__ == "__main__":
    main()
