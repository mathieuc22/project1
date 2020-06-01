# Project 1

Web Programming with Python and JavaScript

## Goal

The purpose of Book Review is to let you review and rate the books you read in order to build a nice review database. In addition to the web site, you can use the API to ask for basic info and the review of a book.

You need to register to be part of the project.

## Content

* `application.py` contains the flask application, including the routes and the logic for authentication, search, review process, API and admin tasks
* `book.csv` is the source for the book database
* `import.py` is a python program that can help you importing books from a csv file to the database
* `requirements.txt` contains the required packages that you can install with pip
* In `static` folder you'll find a css file and an background image for the Home page
* In `templates` folder you'll find all the html files:
    * `book.html`: display informations related to a specific book and let a user add a review
    * `books.html`: is the result for a search
    * `error.html`: a generic error page
    * `index.html`: is the Home page
    * `layout.html`: defines the look and feel for the entire website
    * `login.html`: login page
    * `profile.html`: is the user profile template
    * `register.html`: to register a new user
    * `reviews.html`: for admin, lists all the reviews
    * `update_review.html`: provide to a user the ability to edit is review
    * `users.html`: for admin, lists all the users

## Installation

To run locally:
1. Install using git: clone the repository `git clone https://github.com/mathieuc22/project1.git`
2. `cd project1`
2. Create a virtualenv and activate it
3. Install dependencies: `pip install -r requirements.txt`
4. Build a postgresql database and add it to a `DATABASE_URL` env variable
4. Get a Goodread API key and add it to a `GR_KEY` env variable
4. Add `application.py` to a `FLASK_APP` env variable and run the server `flask run`
3. Open http://127.0.0.1:5000 in a browser.
