from flask import Flask, render_template, redirect, request, url_for, send_from_directory
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user, AnonymousUserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import json
from algoliasearch.search_client import SearchClient
from statistics import mean

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}  
# ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
# Bootstrap(app)
db = SQLAlchemy()
db.init_app(app)
client = SearchClient.create('9GNCTQIKDP', 'c60b3e233b5bb52062c085eda75a761c')
index = client.init_index('profdata')
# gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
f = open('mydata.json')
data = json.load(f)
# f.close()


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    year = db.Column(db.Integer)
    branch = db.Column(db.String(100))
    # review = db.relationship("Review", back_populates="author")



class AnonymousUser(UserMixin, db.Model):
    __tablename__ = 'anonymous_user'
    id = db.Column(db.Integer, primary_key=True)

    def __init__(self):
        self._is_active = False

    def is_authenticated(self):
        return False

    def is_anonymous(self):
        return True

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value


class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    # author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # author = db.relationship("User", back_populates="review")
    prof_id = db.Column(db.Integer, db.ForeignKey('prof_data.id'))
    prof = db.relationship("ProfData", back_populates="review")
    da = db.Column(db.VARCHAR(200))
    attendance = db.Column(db.VARCHAR(200))
    marks = db.Column(db.VARCHAR(200))
    research = db.Column(db.VARCHAR(200))
    # text = db.Column(db.TEXT, nullable=False)



class ProfData(db.Model):
    __tablename__ = 'prof_data'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    designation = db.Column(db.Text)
    link = db.Column(db.Text)
    image = db.Column(db.Text)
    review = db.relationship("Review", back_populates="prof")

login_manager.anonymous_user = AnonymousUser

with app.app_context():
    db.create_all()
    data = ProfData.query.all()
    rev = Review.query.all()
    c = User.query.all()

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))



@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        print("hello")
        return AnonymousUser()
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return render_template("index.html")


@app.errorhandler(404)
def invalid_route(e):
    return render_template('404.html')


@app.route("/all-prof/<num>")
def all_prof(num):
    prof_ratings = {}
    for prof in data[int(num)*12:(int(num)*12)+12]:
        num_ratings = db.session.query(func.count(Review.id)).filter_by(prof_id=prof.id).scalar() or 0

        avg_rating_da = db.session.query(func.avg(func.nullif(Review.da, '0') \
                                                  .cast(db.Integer))).filter_by(prof_id=prof.id).scalar()
        avg_rating_attend = db.session.query(func.avg(func.nullif(Review.attendance, '0') \
                                                      .cast(db.Integer))).filter_by(prof_id=prof.id).scalar()
        avg_rating_marks = db.session.query(func.avg(func.nullif(Review.marks, '0') \
                                                     .cast(db.Integer))).filter_by(prof_id=prof.id).scalar()
        avg_rating_research = db.session.query(func.avg(func.nullif(Review.research, '0') \
                                                        .cast(db.Integer))).filter_by(prof_id=prof.id).scalar()
        try:
            avg_rating_da = round(avg_rating_da, 1) if avg_rating_da is not None else "Unrated"
            avg_rating_attend = round(avg_rating_attend, 1) if avg_rating_attend is not None else "Unrated"
            avg_rating_marks = round(avg_rating_marks, 1) if avg_rating_marks is not None else "Unrated"
            avg_rating_research = round(avg_rating_research, 1) if avg_rating_research is not None else "Unrated"


            prof_ratings[prof.id] = {"da": avg_rating_da, "attendance": avg_rating_attend, "marks": avg_rating_marks,
                                     "re": avg_rating_research, "num": num_ratings}
        except TypeError:
            pass

    return render_template("no-sidebar.html", l=data, n=num, r=rev, rating=prof_ratings)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        branch = request.form.get("branch")
        year = request.form.get("year")
        if name == "" or email == "" or branch == "" or year == "" or request.form.get("password") == "":
            return render_template('signup.html', l=1, p=0)
        if len(request.form.get("password")) < 8:
            return render_template('signup.html', l=0, p=1)
        password = (generate_password_hash(request.form.get("password"), method='pbkdf2:sha256:260000',
                                           salt_length=8))[21:]
        new_user = User(name=name, email=email, branch=branch, year=year, password=password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect("/")
    return render_template("signup.html", l=0, p=0)

@app.route("/help")
def help():
    return render_template('help.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        meth = 'pbkdf2:sha256:260000$'
        o = User.query.filter_by(email=email).first()
        try:
            if o.email == email and check_password_hash(f"{meth}{o.password}", password):
                login_user(o)
                return redirect("/")
            else:
                return render_template("login.html", l=1)
        except AttributeError:
            return render_template("login.html", l=1)
    return render_template("login.html", l=0)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/search", methods=["GET", "POST"])
def search():
    search_query = request.form.get("searchquery")
    search_results = index.search(search_query)["hits"]
    prof_ratings = {}

    prof_ids = [result["id"] for result in search_results]
    reviews = db.session.query(Review.prof_id,
                               func.avg(func.nullif(Review.da, '0').cast(db.Integer)).label("da_avg"),
                               func.avg(func.nullif(Review.attendance, '0').cast(db.Integer)).label("attendance_avg"),
                               func.avg(func.nullif(Review.marks, '0').cast(db.Integer)).label("marks_avg"),
                               func.avg(func.nullif(Review.research, '0').cast(db.Integer)).label("research_avg"),
                               func.count(Review.id).label("num_ratings")
                               ).filter(Review.prof_id.in_(prof_ids)).group_by(Review.prof_id).all()

    for review in reviews:
        prof_ratings[review.prof_id] = {
            "da": round(review.da_avg, 1) if review.da_avg is not None else "Unrated",
            "attendance": round(review.attendance_avg, 1) if review.attendance_avg is not None else "Unrated",
            "marks": round(review.marks_avg, 1) if review.marks_avg is not None else "Unrated",
            "re": round(review.research_avg, 1) if review.research_avg is not None else "Unrated",
            "num": review.num_ratings if review.num_ratings is not None else 0
        }

    return render_template("search.html", li=search_results, leng=len(search_results), name=search_query,
                           rating=prof_ratings)

@app.route("/review/<num>", methods=["GET", "POST"])
def review(num):
    if request.method == "POST":
        o = ProfData.query.filter_by(id=int(num)).first()
        new_review = Review(attendance=request.form.get("attend"), da=request.form.get("da"),
                            marks=request.form.get("marks"), research=request.form.get("research"), prof=o)
        db.session.add(new_review)
        db.session.commit()
        print(current_user.id)
        return redirect("/")
    return render_template("review.html", n=num)
    
@app.route('/ads.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])

# @app.route("/comment/<num>", methods=["GET","POST"])
# def comment(num):


if __name__ == "__main__":
    app.run(debug=True)
