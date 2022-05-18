from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import AddItem, RegisterForm, LoginForm, CartForm
from sqlalchemy import Table, Column, Integer, String, Text, create_engine, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from functools import wraps
import stripe
import os


stripe.api_key = os.environ.get("STRIPE_KEY")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
Bootstrap(app)


app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///shopping-site-data.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

Base = declarative_base()

login_manager = LoginManager()
login_manager.init_app(app)


def add_price(item, product_id):
    new_price = stripe.Price.create(
        unit_amount=int(item.price * 100),
        currency="usd",
        product=product_id,
    )
    price_id = new_price["id"]
    with Session(engine) as session:
        new_product = Products(
            product_id=product_id,
            price_id=price_id
        )
        session.add(new_product)
        session.commit()


@login_manager.user_loader
def load_user(user_id):
    with Session(engine) as session:
        return session.query(User).get(user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


class User(Base, UserMixin):

    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(String(250), nullable=False, unique=True)
    name = Column(String(250), nullable=False)
    password = Column(String(250), nullable=False)

    # Relate user to the catalog
    items = relationship("Catalog", back_populates='seller')
    cart = relationship("CartItems", back_populates='buyer')

    # Relate user to actual orders
    order = relationship("Orders", back_populates='buyer')


class Catalog(Base):

    __tablename__ = "catalog"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), unique=True, nullable=False)
    img_url = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Float, nullable=False)

    # relate item to seller
    seller = relationship("User", back_populates='items')
    # relate item to buyer
    cart = relationship("CartItems", back_populates='cart_item')

    seller_id = Column(Integer, ForeignKey("user.id"))


class CartItems(Base):
    __tablename__ = "cart"
    id = Column(Integer, primary_key=True)
    quantity = Column(Integer, nullable=False)

    # relate cart to buyer
    buyer_id = Column(Integer, ForeignKey("user.id"))
    buyer = relationship("User", back_populates='cart')

    # relate cart to items
    item_id = Column(Integer, ForeignKey("catalog.id"))
    cart_item = relationship("Catalog", back_populates="cart")


class Orders(Base):
    __tablename__ = "order"
    id = Column(Integer, primary_key=True)

    user_order = Column(Text, nullable=False)
    order_status = Column(Boolean, nullable=False)

    buyer_id = Column(Integer, ForeignKey("user.id"))
    buyer = relationship("User", back_populates='order')


class Products(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_id = Column(String(1000), nullable=False)
    price_id = Column(String(1000))


engine = create_engine("sqlite:///shopping-site-data.db")

# Base.metadata.create_all(engine)


YOUR_DOMAIN = 'http://localhost:5000'


@app.route("/")
def home():
    with Session(engine) as session:
        items = session.query(Catalog).all()
    return render_template("index.html", all_items=items, logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        with Session(engine) as session:
            user_email = form.email.data
            user_name = form.name.data
            user_password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=8)
            check_email = session.query(User).filter_by(email=user_email).first()
            if check_email:
                flash("This email already exists. Log in Instead.")
                return redirect(url_for('login'))
            else:
                new_user = User(
                    name=user_name,
                    email=user_email,
                    password=user_password
                )
                session.add(new_user)
                session.commit()
                login_user(new_user)
                return redirect(url_for('home'))
    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_email = form.email.data
        user_password = form.password.data
        with Session(engine) as session:
            user = session.query(User).filter_by(email=user_email).first()
            if not user:
                flash("This email address is not registered")
                return redirect(url_for('login'))
            else:
                if check_password_hash(user.password, user_password):
                    login_user(user)
                    return redirect(url_for('home'))
                else:
                    flash("Incorrect password. Try again")
                    return redirect(url_for("login"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/new-item", methods=["GET", "POST"])
@admin_only
def add_new_item():
    form = AddItem()
    if form.validate_on_submit():
        with Session(engine) as session:
            new_item = Catalog(
                name=form.name.data,
                img_url=form.img_url.data,
                quantity=form.quantity.data,
                description=form.description.data,
                price=form.price.data,
                seller=current_user
            )
            session.add(new_item)
            session.commit()
            with Session(engine) as new_session:
                new_product_item = new_session.query(Catalog).filter_by(name=new_item.name).first()
                print(new_product_item.id)
                created_product = stripe.Product.create(name=new_product_item.name,
                                                        id=f"catalogproduct{new_product_item.id}",
                                                        images=[new_product_item.img_url])
                add_price(item=new_product_item, product_id=created_product["id"])
                return redirect(url_for("add_new_item"))
    return render_template("add-item.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/item/<int:item_id>", methods=["GET", "POST"])
def show_item(item_id):
    with Session(engine) as session:
        form = CartForm()
        requested_item = session.query(Catalog).get(item_id)
        if form.validate_on_submit():
            if not current_user.is_authenticated:
                flash("Log in to add to cart")
                return redirect(url_for('login'))
            else:
                new_item = CartItems(
                    buyer=current_user,
                    cart_item=requested_item,
                    quantity=form.quantity.data
                )
                session.add(new_item)
                session.commit()
                print(item_id)
                return redirect(url_for('home'))
        return render_template("item.html", item=requested_item, form=form, current_user=current_user,
                               logged_in=current_user.is_authenticated)


@app.route("/view-cart")
def view_cart():
    with Session(engine) as session:
        requested_items = session.query(CartItems).filter_by(buyer_id=current_user.id).all()
        return render_template("view-cart.html", items=requested_items, current_user=current_user,
                               logged_in=current_user.is_authenticated)


@app.route("/edit-cart/<int:item_id>", methods=["POST"])
def edit_cart(item_id):
    if request.method == "POST":
        new_quantity = request.form["quantity"]
        with Session(engine) as session:
            item_to_edit = session.query(CartItems).get(item_id)
            item_to_edit.quantity = new_quantity
            session.commit()
        return redirect(url_for('view_cart'))


@app.route("/remove/<int:item_id>")
def remove_item(item_id):
    with Session(engine) as session:
        item_to_remove = session.query(CartItems).get(item_id)
        session.delete(item_to_remove)
        session.commit()
    return redirect(url_for('view_cart'))


@app.route("/add-to-cart/<int:item_id>")
def add_to_cart(item_id):
    with Session(engine) as session:
        requested_item = session.query(Catalog).get(item_id)
        if not current_user.is_authenticated:
            flash("Log in to add to cart")
            return redirect(url_for('login'))
        else:
            new_item = CartItems(
                buyer=current_user,
                cart_item=requested_item,
                quantity=1
            )
            session.add(new_item)
            session.commit()
            return redirect(url_for('home'))


@app.route('/create-checkout-session/<int:user_id>', methods=["GET", "POST"])
def create_checkout_session(user_id):
    with Session(engine) as session:
        final_items = session.query(CartItems).filter_by(buyer_id=user_id).all()
        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        "price": session.query(Products).filter_by(product_id=f"catalogproduct{item.cart_item.id}").first().price_id,
                        "quantity": item.quantity,
                    } for item in final_items],
                mode='payment',
                success_url='http://192.168.8.100:5000/success.html',
                cancel_url='http://192.168.8.100:5000/cancel.html',
            )
        except Exception as e:
            return str(e)

        # return render_template("checkout.html", items=final_items)
        return redirect(checkout_session.url, code=303)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
    # app.run(debug=True)
