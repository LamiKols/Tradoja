from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FloatField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError
from wtforms.widgets import TextArea
from models import User

class RegistrationForm(FlaskForm):
    """User registration form"""
    name = StringField('Full Name', validators=[
        DataRequired(), 
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message="Please enter a valid email address")
    ])
    role = SelectField('Role', choices=[
        ('farmer', 'Farmer'), 
        ('buyer', 'Buyer')
    ], validators=[DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message="Passwords must match")
    ])
    
    def validate_email(self, email):
        """Check if email is already registered"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message="Please enter a valid email address")
    ])
    password = PasswordField('Password', validators=[DataRequired()])

class ProduceForm(FlaskForm):
    """Form for adding/editing produce listings"""
    name = StringField('Produce Name', validators=[
        DataRequired(), 
        Length(min=2, max=100, message="Produce name must be between 2 and 100 characters")
    ])
    quantity = StringField('Quantity Available', validators=[
        DataRequired(), 
        Length(min=1, max=50, message="Please specify quantity (e.g., '50 kg', '100 bags')")
    ])
    price = FloatField('Price per Unit', validators=[
        DataRequired(), 
        NumberRange(min=0.01, message="Price must be greater than 0")
    ])
    price_unit = SelectField('Currency/Unit', choices=[
        ('NGN', 'Nigerian Naira (NGN)'),
        ('USD', 'US Dollar (USD)')
    ], default='NGN', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[
        Length(max=500, message="Description cannot exceed 500 characters")
    ], widget=TextArea())
    is_available = BooleanField('Available for Sale', default=True)

class SearchForm(FlaskForm):
    """Form for searching produce"""
    search_term = StringField('Search Produce', validators=[
        Length(max=100, message="Search term cannot exceed 100 characters")
    ])
