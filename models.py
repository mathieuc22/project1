from flask_sqlalchemy

db = SQLAlchemy()


class books(Base):
    __tablename__ = "books"
    isbn = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=False)

class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

class Reviews(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    content
    book = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user = db.Column(db.Integer, db.ForeignKey("users.id"),nullable=False)
