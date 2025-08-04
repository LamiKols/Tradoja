from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FloatField, BooleanField, HiddenField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError, Optional
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
    
    # Geographical Indications (GI) fields
    gi_label = SelectField('Geographical Indication (GI)', choices=[], coerce=str)
    gi_custom_label = StringField('Custom GI Label (if Other selected)', 
                                 render_kw={'placeholder': 'e.g., Osun Palm Oil, Kaduna Ginger'})

class SearchForm(FlaskForm):
    """Form for searching produce"""
    search_term = StringField('Search Produce', validators=[
        Length(max=100, message="Search term cannot exceed 100 characters")
    ])
    gi_filter = SelectField('Filter by GI', choices=[
        ('all', 'All Products'),
        ('gi_only', 'GI Certified Only'),
        ('non_gi', 'Non-GI Products')
    ], default='all')


class GIAdminForm(FlaskForm):
    """Form for admin GI certification management"""
    gi_status = SelectField('GI Status', choices=[
        ('pending', 'Pending Review'),
        ('verified', 'Verified/Approved'),
        ('rejected', 'Rejected')
    ], validators=[DataRequired()])
    gi_certificate_number = StringField('GI Certificate Number',
                                       render_kw={'placeholder': 'e.g., NG-GI-007'})
    gi_admin_comment = TextAreaField('Admin Comments',
                                    render_kw={'placeholder': 'Reason for approval/rejection, additional notes'},
                                    validators=[Length(max=1000)])
    submit = SubmitField('Update GI Status')


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
    submit = SubmitField('Update Status')


class CSAWeatherForm(FlaskForm):
    """Form for Climate-Smart Agriculture weather and location data"""
    city = StringField('City/Location', 
                      validators=[DataRequired()], 
                      default='Lagos',
                      render_kw={'placeholder': 'Enter city name (e.g., Lagos, Abuja, Kano)'})
    latitude = FloatField('Latitude (Optional)', 
                         render_kw={'placeholder': 'GPS latitude coordinate'})
    longitude = FloatField('Longitude (Optional)', 
                          render_kw={'placeholder': 'GPS longitude coordinate'})
    submit = SubmitField('Get Weather Data')


class CSASoilForm(FlaskForm):
    """Form for soil data input and carbon footprint calculation"""
    soil_type = SelectField('Soil Type', choices=[
        ('', 'Select soil type'),
        ('clay', 'Clay soil'),
        ('sandy', 'Sandy soil'),
        ('loamy', 'Loamy soil'),
        ('silty', 'Silty soil'),
        ('peaty', 'Peaty soil'),
        ('chalky', 'Chalky soil')
    ], validators=[DataRequired()])
    
    soil_moisture = SelectField('Current Soil Moisture', choices=[
        ('', 'Select moisture level'),
        ('dry', 'Dry (needs irrigation)'),
        ('moderate', 'Moderate (adequate moisture)'),
        ('wet', 'Wet (excess moisture)')
    ], validators=[DataRequired()])
    
    field_size = FloatField('Field Size (hectares)', 
                           validators=[DataRequired(), NumberRange(min=0.1, max=10000)],
                           render_kw={'placeholder': 'Enter farm size in hectares'})
    
    fertilizer_type = SelectField('Fertilizer Type', choices=[
        ('', 'Select fertilizer type'),
        ('none', 'No fertilizer used'),
        ('organic', 'Organic fertilizer (compost, manure)'),
        ('synthetic', 'Synthetic/Chemical fertilizer'),
        ('mixed', 'Mixed (organic + synthetic)')
    ], validators=[DataRequired()])
    
    fertilizer_amount = FloatField('Fertilizer Amount (kg per hectare)', 
                                  validators=[NumberRange(min=0, max=1000)],
                                  render_kw={'placeholder': 'Amount of fertilizer used per hectare'})
    
    estimated_yield = FloatField('Expected Yield (tons per hectare)', 
                                validators=[DataRequired(), NumberRange(min=0.1, max=100)],
                                render_kw={'placeholder': 'Expected harvest per hectare'})
    
    submit = SubmitField('Analyze & Get Recommendations')


class ExportListingForm(FlaskForm):
    """Form for creating export listings"""
    produce_name = StringField('Produce Name', 
                              validators=[DataRequired()],
                              render_kw={'placeholder': 'e.g., Cassava, Yam, Cocoa'})
    
    quantity = StringField('Quantity', 
                          validators=[DataRequired()],
                          render_kw={'placeholder': 'e.g., 50 tons, 100 bags, 500 kg'})
    
    price = FloatField('Price per Unit (USD)', 
                      validators=[DataRequired(), NumberRange(min=0.01)],
                      render_kw={'placeholder': 'Enter price in USD'})
    
    origin_state = SelectField('Origin State', choices=[
        ('', 'Select origin state'),
        ('abia', 'Abia'), ('adamawa', 'Adamawa'), ('akwa-ibom', 'Akwa Ibom'),
        ('anambra', 'Anambra'), ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'),
        ('benue', 'Benue'), ('borno', 'Borno'), ('cross-river', 'Cross River'),
        ('delta', 'Delta'), ('ebonyi', 'Ebonyi'), ('edo', 'Edo'),
        ('ekiti', 'Ekiti'), ('enugu', 'Enugu'), ('gombe', 'Gombe'),
        ('imo', 'Imo'), ('jigawa', 'Jigawa'), ('kaduna', 'Kaduna'),
        ('kano', 'Kano'), ('katsina', 'Katsina'), ('kebbi', 'Kebbi'),
        ('kogi', 'Kogi'), ('kwara', 'Kwara'), ('lagos', 'Lagos'),
        ('nasarawa', 'Nasarawa'), ('niger', 'Niger'), ('ogun', 'Ogun'),
        ('ondo', 'Ondo'), ('osun', 'Osun'), ('oyo', 'Oyo'),
        ('plateau', 'Plateau'), ('rivers', 'Rivers'), ('sokoto', 'Sokoto'),
        ('taraba', 'Taraba'), ('yobe', 'Yobe'), ('zamfara', 'Zamfara'),
        ('fct', 'Federal Capital Territory')
    ], validators=[DataRequired()])
    
    target_market = SelectField('Target Export Market', choices=[
        ('', 'Select target market'),
        ('EU', 'European Union'),
        ('ECOWAS', 'ECOWAS Region'),
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('CHINA', 'China'),
        ('INDIA', 'India'),
        ('MIDDLE_EAST', 'Middle East'),
        ('CANADA', 'Canada'),
        ('ASIA_PACIFIC', 'Asia Pacific'),
        ('OTHER', 'Other Markets')
    ], validators=[DataRequired()])
    
    has_phytosanitary = BooleanField('Phytosanitary Certificate Available')
    phytosanitary_file = FileField('Upload Phytosanitary Certificate', 
                                  validators=[FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 
                                            'Only PDF, JPG, JPEG, and PNG files allowed')])
    
    # Compliance standards (multiple checkboxes)
    eu_gi = BooleanField('EU Geographical Indication (GI)')
    usda_organic = BooleanField('USDA Organic Certified')
    fair_trade = BooleanField('Fair Trade Certified')
    global_gap = BooleanField('GlobalGAP Certified')
    iso_22000 = BooleanField('ISO 22000 Food Safety')
    haccp = BooleanField('HACCP Certified')
    
    description = TextAreaField('Product Description', 
                               validators=[Length(max=1000)],
                               render_kw={'rows': 4, 'placeholder': 'Describe quality, processing, packaging, etc.'})
    
    harvest_date = DateField('Harvest Date', validators=[DataRequired()])
    shipment_window_start = DateField('Shipment Window Start', validators=[DataRequired()])
    shipment_window_end = DateField('Shipment Window End', validators=[DataRequired()])
    
    def validate_shipment_window_end(self, field):
        if self.shipment_window_start.data and field.data:
            if field.data <= self.shipment_window_start.data:
                raise ValidationError('End date must be after start date.')
    
    submit = SubmitField('List for Export')


class ExportFilterForm(FlaskForm):
    """Form for filtering export listings"""
    produce_name = StringField('Produce Name')
    target_market = SelectField('Target Market', choices=[
        ('', 'All Markets'),
        ('EU', 'European Union'),
        ('ECOWAS', 'ECOWAS Region'),
        ('US', 'United States'),
        ('UK', 'United Kingdom'),
        ('CHINA', 'China'),
        ('INDIA', 'India'),
        ('MIDDLE_EAST', 'Middle East'),
        ('CANADA', 'Canada'),
        ('ASIA_PACIFIC', 'Asia Pacific'),
        ('OTHER', 'Other Markets')
    ])
    origin_state = SelectField('Origin State', choices=[
        ('', 'All States'),
        ('abia', 'Abia'), ('adamawa', 'Adamawa'), ('akwa-ibom', 'Akwa Ibom'),
        ('anambra', 'Anambra'), ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'),
        ('benue', 'Benue'), ('borno', 'Borno'), ('cross-river', 'Cross River'),
        ('delta', 'Delta'), ('ebonyi', 'Ebonyi'), ('edo', 'Edo'),
        ('ekiti', 'Ekiti'), ('enugu', 'Enugu'), ('gombe', 'Gombe'),
        ('imo', 'Imo'), ('jigawa', 'Jigawa'), ('kaduna', 'Kaduna'),
        ('kano', 'Kano'), ('katsina', 'Katsina'), ('kebbi', 'Kebbi'),
        ('kogi', 'Kogi'), ('kwara', 'Kwara'), ('lagos', 'Lagos'),
        ('nasarawa', 'Nasarawa'), ('niger', 'Niger'), ('ogun', 'Ogun'),
        ('ondo', 'Ondo'), ('osun', 'Osun'), ('oyo', 'Oyo'),
        ('plateau', 'Plateau'), ('rivers', 'Rivers'), ('sokoto', 'Sokoto'),
        ('taraba', 'Taraba'), ('yobe', 'Yobe'), ('zamfara', 'Zamfara'),
        ('fct', 'Federal Capital Territory')
    ])
    has_phytosanitary = SelectField('Certification Status', choices=[
        ('', 'All Listings'),
        ('yes', 'With Phytosanitary Certificate'),
        ('no', 'Without Certificate')
    ])
    status = SelectField('Approval Status', choices=[
        ('', 'All Status'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('shipped', 'Shipped')
    ])
    submit = SubmitField('Filter Results')


class ExportStatusForm(FlaskForm):
    """Form for admin to update export listing status"""
    status = SelectField('Status', choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved for Export'),
        ('rejected', 'Rejected'),
        ('shipped', 'Shipped')
    ], validators=[DataRequired()])
    admin_comment = TextAreaField('Admin Comment', 
                                 validators=[Length(max=1000)],
                                 render_kw={'rows': 4, 'placeholder': 'Comment for the farmer...'})
    submit = SubmitField('Update Status')


class PrecisionFieldForm(FlaskForm):
    """Form for creating and editing precision agriculture fields"""
    field_name = StringField('Field Name', validators=[DataRequired(), Length(min=2, max=100)])
    crop_type = SelectField('Crop Type', validators=[DataRequired()])
    
    # Location input options
    address = StringField('Field Address', validators=[Optional()], 
                         render_kw={'placeholder': 'Enter farm address or location name'})
    manual_latitude = FloatField('Latitude', validators=[Optional(), NumberRange(min=-90, max=90)],
                                render_kw={'placeholder': '6.5244', 'step': 'any'})
    manual_longitude = FloatField('Longitude', validators=[Optional(), NumberRange(min=-180, max=180)],
                                 render_kw={'placeholder': '3.3792', 'step': 'any'})
    
    # Geographic fields (will be populated by map interface)
    coordinates = HiddenField('Field Coordinates')
    center_latitude = HiddenField('Center Latitude')
    center_longitude = HiddenField('Center Longitude')  
    field_size_hectares = FloatField('Field Size (hectares)', validators=[DataRequired(), NumberRange(min=0.01)])
    
    # Farming details
    planting_date = DateField('Planting Date', validators=[Optional()])
    soil_type = SelectField('Soil Type', validators=[Optional()])
    irrigation_type = SelectField('Irrigation Type', validators=[Optional()])
    fertilizer_type = SelectField('Fertilizer Type', validators=[Optional()])
    
    submit = SubmitField('Save Field')
    
    def __init__(self, *args, **kwargs):
        super(PrecisionFieldForm, self).__init__(*args, **kwargs)
        # Import here to avoid circular imports
        from precision_service import PrecisionAgricultureService
        service = PrecisionAgricultureService()
        
        self.crop_type.choices = service.get_crop_choices()
        self.soil_type.choices = service.get_soil_choices()
        self.irrigation_type.choices = service.get_irrigation_choices()
        self.fertilizer_type.choices = service.get_fertilizer_choices()


class FieldAnalyticsForm(FlaskForm):
    """Form for updating field analytics parameters"""
    crop_type = SelectField('Crop Type', validators=[DataRequired()])
    planting_date = DateField('Planting Date', validators=[Optional()])
    soil_type = SelectField('Soil Type', validators=[Optional()])
    irrigation_type = SelectField('Irrigation Type', validators=[Optional()])
    fertilizer_type = SelectField('Fertilizer Type', validators=[Optional()])
    
    submit = SubmitField('Update Analytics')
    
    def __init__(self, *args, **kwargs):
        super(FieldAnalyticsForm, self).__init__(*args, **kwargs)
        from precision_service import PrecisionAgricultureService
        service = PrecisionAgricultureService()
        
        self.crop_type.choices = service.get_crop_choices()
        self.soil_type.choices = service.get_soil_choices()
        self.irrigation_type.choices = service.get_irrigation_choices()
        self.fertilizer_type.choices = service.get_fertilizer_choices()
