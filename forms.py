from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FloatField, IntegerField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField


##WTForm
class AddItem(FlaskForm):
    name = StringField("Name of Item", validators=[DataRequired()])
    description = StringField("Item Description", validators=[DataRequired()])
    img_url = StringField("Item Image URL", validators=[DataRequired(), URL()])
    quantity = IntegerField("Number of items available", validators=[DataRequired()])
    price = FloatField("Unit Price", validators=[DataRequired()])
    submit = SubmitField("Add Item")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("SIGN UP!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("LOG IN!")


class CartForm(FlaskForm):
    quantity = IntegerField("Quantity", validators=[DataRequired()])
    submit = SubmitField("Add to cart")
