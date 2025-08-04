from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FloatField, BooleanField, HiddenField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError
from wtforms.widgets import TextArea
from models import User
from datetime import date, time

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


class MessageForm(FlaskForm):
    """Form for sending messages"""
    subject = StringField('Subject', validators=[DataRequired(), Length(min=1, max=200)])
    message_body = TextAreaField('Message', validators=[DataRequired(), Length(min=1, max=2000)],
                                render_kw={"rows": 6, "placeholder": "Write your message here..."})
    receiver_id = HiddenField('Receiver ID', validators=[DataRequired()])
    produce_id = HiddenField('Produce ID')  # Optional


class MessageReplyForm(FlaskForm):
    """Form for replying to messages"""
    message_body = TextAreaField('Reply', validators=[DataRequired(), Length(min=1, max=2000)],
                                render_kw={"rows": 4, "placeholder": "Write your reply here..."})


class LogisticsRequestForm(FlaskForm):
    """Form for creating logistics requests"""
    produce_id = HiddenField('Produce ID', validators=[DataRequired()])
    request_type = SelectField('Service Type', 
                              choices=[('pickup', 'Pickup from Farmer'), ('delivery', 'Delivery to Me')],
                              validators=[DataRequired()])
    preferred_date = DateField('Preferred Date', validators=[DataRequired()],
                              default=date.today)
    preferred_time = TimeField('Preferred Time', validators=[DataRequired()],
                              default=time(9, 0))
    pickup_location = StringField('Pickup Location', validators=[DataRequired(), Length(min=5, max=200)],
                                 render_kw={"placeholder": "Enter pickup address..."})
    destination_address = StringField('Destination Address', validators=[DataRequired(), Length(min=5, max=200)],
                                     render_kw={"placeholder": "Enter delivery address..."})
    notes = TextAreaField('Additional Notes', validators=[Length(max=500)],
                         render_kw={"rows": 3, "placeholder": "Any special instructions or notes..."})


class LogisticsStatusForm(FlaskForm):
    """Form for updating logistics request status (admin use)"""
    status = SelectField('Status', 
                        choices=[('pending', 'Pending'), ('approved', 'Approved'), 
                                ('fulfilled', 'Fulfilled'), ('cancelled', 'Cancelled')],
                        validators=[DataRequired()])


class FundingApplicationForm(FlaskForm):
    """Form for funding applications"""
    produce_id = SelectField('Related Produce (Optional)', 
                           choices=[('', 'None - General funding')],
                           coerce=lambda x: int(x) if x else None)
    amount_requested = FloatField('Amount Requested (NGN)', 
                                 validators=[DataRequired(), NumberRange(min=1000, max=10000000,
                                           message="Amount must be between NGN 1,000 and NGN 10,000,000")])
    application_reason = TextAreaField('Reason for Application', 
                                     validators=[DataRequired(), Length(min=50, max=2000,
                                               message="Please provide detailed reason (50-2000 characters)")],
                                     render_kw={"rows": 6, "placeholder": "Explain how this funding will help your farming operations..."})
    supporting_document = FileField('Supporting Document (Optional)', 
                                   validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 
                                             'Only PDF, JPG, JPEG, and PNG files are allowed')])
    
    def __init__(self, user_produce=None, *args, **kwargs):
        super(FundingApplicationForm, self).__init__(*args, **kwargs)
        if user_produce:
            self.produce_id.choices = [('', 'None - General funding')] + \
                                    [(str(p.id), f"{p.name} - {p.quantity}") for p in user_produce]


class FundingStatusForm(FlaskForm):
    """Form for updating funding application status (admin use)"""
    status = SelectField('Status', 
                        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('declined', 'Declined')],
                        validators=[DataRequired()])
    admin_comment = TextAreaField('Admin Comment', 
                                 validators=[Length(max=1000)],
                                 render_kw={"rows": 4, "placeholder": "Optional comment for the applicant..."})
