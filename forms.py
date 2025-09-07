from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FloatField, BooleanField, HiddenField, DateField, TimeField, SubmitField, IntegerField
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
        ('aggregator', 'Aggregator'),
        ('transport_company', 'Transport Company'),
        ('bulk_trader', 'Bulk Trader'),
        ('retailer', 'Retailer'),
        ('input_supplier', 'Input Supplier'),
        ('investor', 'Investor'),
        ('government_agency', 'Government Agency'),
        ('ngo_dev_partner', 'NGO/Development Partner'),
        ('buyer', 'Buyer')  # Keep buyer for backwards compatibility
    ], validators=[DataRequired()])
    buyer_type = SelectField('Buyer Category', choices=[
        ('retail_buyer', 'Retail Buyer'),
        ('bulk_trader', 'Bulk Trader'),  
        ('institutional_buyer', 'Institutional Buyer'),
        ('agro_processor', 'Agro Processor')
    ], validators=[Optional()])
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



class PurchaseForm(FlaskForm):
    """Form for purchasing produce with payment processing"""
    produce_id = HiddenField("Produce ID", validators=[DataRequired()])
    quantity_to_buy = FloatField("Quantity to Purchase", validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Quantity must be greater than 0")
    ])
    delivery_required = BooleanField("Delivery Required", default=False)
    delivery_address = TextAreaField("Delivery Address", validators=[Optional()])
    buyer_notes = TextAreaField("Additional Notes", validators=[Optional()])
    submit = SubmitField("Proceed to Payment")


class SubscriptionForm(FlaskForm):
    """Form for premium subscription signup"""
    plan = SelectField("Subscription Plan", choices=[
        ("premium_monthly", "Premium Monthly - ₦10,000/month")
    ], validators=[DataRequired()])
    submit = SubmitField("Subscribe Now")


class LogisticsPaymentForm(FlaskForm):
    """Form for logistics service payment"""
    logistics_request_id = HiddenField("Logistics Request ID", validators=[DataRequired()])
    service_type = SelectField("Service Type", choices=[
        ("pickup", "Pickup Service - ₦2,000"),
        ("delivery", "Delivery Service - ₦2,000"),
        ("both", "Pickup & Delivery - ₦3,500")
    ], validators=[DataRequired()])
    submit = SubmitField("Pay for Logistics")


# Universal Onboarding Forms for Produce for Lagos Program

class OnboardingStep1Form(FlaskForm):
    """Step 1: Personal Information"""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=200)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    nationality = StringField('Nationality', validators=[DataRequired()], default='Nigerian')
    state_of_origin = SelectField('State of Origin', choices=[], validators=[DataRequired()])
    lga_of_origin = StringField('LGA of Origin', validators=[DataRequired(), Length(max=100)])
    marital_status = SelectField('Marital Status', choices=[
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], validators=[DataRequired()])
    education_level = SelectField('Education Level', choices=[
        ('none', 'No formal education'),
        ('primary', 'Primary education'),
        ('secondary', 'Secondary education'),
        ('tertiary', 'Tertiary education'),
        ('vocational', 'Vocational training')
    ], validators=[DataRequired()])
    primary_phone = StringField('Primary Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    secondary_phone = StringField('Secondary Phone Number', validators=[Optional(), Length(max=20)])
    email_address = StringField('Email Address', validators=[DataRequired(), Email()])
    
    # Address Information
    residential_address = TextAreaField('Residential Address', validators=[DataRequired()], 
                                      render_kw={'rows': 3})
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state = SelectField('State', choices=[], validators=[DataRequired()])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=10)])
    lga = StringField('Local Government Area', validators=[DataRequired(), Length(max=100)])
    ward = StringField('Ward', validators=[Optional(), Length(max=100)])
    
    def __init__(self, *args, **kwargs):
        super(OnboardingStep1Form, self).__init__(*args, **kwargs)
        # Nigerian states
        nigerian_states = [
            ('abia', 'Abia'), ('adamawa', 'Adamawa'), ('akwa_ibom', 'Akwa Ibom'),
            ('anambra', 'Anambra'), ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'),
            ('benue', 'Benue'), ('borno', 'Borno'), ('cross_river', 'Cross River'),
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
        ]
        self.state_of_origin.choices = nigerian_states
        self.state.choices = nigerian_states


class OnboardingStep2Form(FlaskForm):
    """Step 2: Business/Organization Information"""
    organization_name = StringField('Organization/Business Name', validators=[Optional(), Length(max=200)])
    business_registration_number = StringField('Business Registration Number', validators=[Optional(), Length(max=100)])
    tax_identification_number = StringField('Tax Identification Number (TIN)', validators=[Optional(), Length(max=50)])
    business_address = TextAreaField('Business Address', validators=[Optional()], render_kw={'rows': 3})
    business_type = SelectField('Business Type', choices=[
        ('', 'Select Business Type'),
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('limited_liability', 'Limited Liability Company'),
        ('cooperative', 'Cooperative Society'),
        ('ngo', 'Non-Governmental Organization'),
        ('government_agency', 'Government Agency'),
        ('individual', 'Individual/Personal')
    ], validators=[Optional()])
    years_in_operation = IntegerField('Years in Operation', validators=[Optional(), NumberRange(min=0, max=100)])
    number_of_employees = IntegerField('Number of Employees', validators=[Optional(), NumberRange(min=0)])
    annual_turnover = SelectField('Annual Turnover (NGN)', choices=[
        ('', 'Select Annual Turnover'),
        ('under_1m', 'Under ₦1 Million'),
        ('1m_5m', '₦1 Million - ₦5 Million'),
        ('5m_10m', '₦5 Million - ₦10 Million'),
        ('10m_50m', '₦10 Million - ₦50 Million'),
        ('50m_100m', '₦50 Million - ₦100 Million'),
        ('above_100m', 'Above ₦100 Million')
    ], validators=[Optional()])


class OnboardingStep3FarmerForm(FlaskForm):
    """Step 3: Farmer-specific information"""
    farm_size = StringField('Farm Size (Hectares or Acres)', validators=[DataRequired(), Length(max=50)])
    crops_grown = TextAreaField('Main Crops/Produce', validators=[DataRequired()], 
                               render_kw={'rows': 3, 'placeholder': 'e.g., Rice, Maize, Cassava, Yam'})
    season_calendar = StringField('Seasonal Calendar (Harvest cycles per year)', validators=[DataRequired()],
                                render_kw={'placeholder': 'e.g., 2 cycles per year, April-July and October-January'})
    avg_output = StringField('Average Monthly Output (Volume)', validators=[DataRequired()],
                           render_kw={'placeholder': 'e.g., 50 bags of rice, 100kg of tomatoes'})
    farming_experience = IntegerField('Years of Farming Experience', validators=[DataRequired(), NumberRange(min=0, max=70)])
    farming_methods = SelectField('Type of Farming', choices=[
        ('', 'Select farming type'),
        ('Crop', 'Crop'),
        ('Livestock', 'Livestock'),
        ('Mixed', 'Mixed')
    ], validators=[DataRequired()])
    irrigation_methods = StringField('Irrigation Methods Used (if any)',
                                   render_kw={'placeholder': 'e.g., Drip irrigation, Rain-fed, Sprinkler system'})
    postharvest_facilities = TextAreaField('Post-Harvest Facilities Available', validators=[Optional()],
                                         render_kw={'rows': 3, 'placeholder': 'Describe storage, processing, and handling facilities'})
    coop_member = SelectField('Are you a member of any Farmer\'s Cooperative or Association?', choices=[
        ('', 'Please select'),
        ('Yes', 'Yes'),
        ('No', 'No')
    ], validators=[DataRequired()])
    extension_service = SelectField('Do you have access to any form of extension service?', choices=[
        ('', 'Please select'),
        ('Yes', 'Yes'),
        ('No', 'No')
    ], validators=[DataRequired()])


class OnboardingStep3AggregatorForm(FlaskForm):
    """Step 3: Aggregator-specific information"""
    aggregation_capacity = StringField('Aggregation Capacity (tons/month)', validators=[DataRequired(), Length(max=100)])
    storage_capacity = StringField('Storage Capacity (tons)', validators=[DataRequired(), Length(max=100)])
    transportation_fleet = TextAreaField('Transportation Fleet', validators=[Optional()], 
                                        render_kw={'rows': 3, 'placeholder': 'Describe your vehicles and capacity'})
    catchment_areas = TextAreaField('Catchment Areas', validators=[DataRequired()], 
                                   render_kw={'rows': 3, 'placeholder': 'List areas where you source produce'})


class OnboardingStep3TransportForm(FlaskForm):
    """Step 3: Transport Company-specific information"""
    vehicle_types = TextAreaField('Vehicle Types', validators=[DataRequired()], 
                                 render_kw={'rows': 3, 'placeholder': 'List vehicle types and specifications'})
    fleet_size = IntegerField('Fleet Size', validators=[DataRequired(), NumberRange(min=1)])
    routes_covered = TextAreaField('Routes Covered', validators=[DataRequired()], 
                                  render_kw={'rows': 3, 'placeholder': 'List regular routes and coverage areas'})
    insurance_details = TextAreaField('Insurance Details', validators=[Optional()], 
                                     render_kw={'rows': 3, 'placeholder': 'Vehicle and cargo insurance information'})


class OnboardingStep3BulkTraderForm(FlaskForm):
    """Step 3: Bulk Trader-specific information"""
    trading_volume = StringField('Trading Volume (tons/month)', validators=[DataRequired(), Length(max=100)])
    target_markets = TextAreaField('Target Markets', validators=[DataRequired()], 
                                  render_kw={'rows': 3, 'placeholder': 'Domestic and export markets'})
    commodity_specialization = TextAreaField('Commodity Specialization', validators=[DataRequired()], 
                                            render_kw={'rows': 3, 'placeholder': 'Primary commodities traded'})


class OnboardingStep3RetailerForm(FlaskForm):
    """Step 3: Retailer-specific information"""
    store_type = SelectField('Store Type', choices=[
        ('', 'Select Store Type'),
        ('supermarket', 'Supermarket'),
        ('grocery_store', 'Grocery Store'),
        ('market_stall', 'Market Stall'),
        ('mobile_vendor', 'Mobile Vendor'),
        ('online_store', 'Online Store'),
        ('wholesale_outlet', 'Wholesale Outlet')
    ], validators=[DataRequired()])
    retail_locations = TextAreaField('Retail Locations', validators=[DataRequired()], 
                                    render_kw={'rows': 3, 'placeholder': 'List your store locations'})
    customer_base = SelectField('Customer Base Size', choices=[
        ('', 'Select Customer Base'),
        ('small', 'Small (1-100 customers)'),
        ('medium', 'Medium (101-500 customers)'),
        ('large', 'Large (501-2000 customers)'),
        ('very_large', 'Very Large (2000+ customers)')
    ], validators=[DataRequired()])


class OnboardingStep3InputSupplierForm(FlaskForm):
    """Step 3: Input Supplier-specific information"""
    input_types = TextAreaField('Input Types', validators=[DataRequired()], 
                               render_kw={'rows': 3, 'placeholder': 'Seeds, fertilizers, pesticides, equipment, etc.'})
    supplier_network = TextAreaField('Supplier Network', validators=[Optional()], 
                                    render_kw={'rows': 3, 'placeholder': 'Your manufacturer and distributor network'})
    distribution_channels = TextAreaField('Distribution Channels', validators=[DataRequired()], 
                                         render_kw={'rows': 3, 'placeholder': 'How you reach customers'})


class OnboardingStep4Form(FlaskForm):
    """Step 4: Financial Information & Document Upload"""
    # Financial Information
    bank_name = StringField('Bank Name', validators=[DataRequired(), Length(max=100)])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(min=10, max=20)])
    account_name = StringField('Account Name', validators=[DataRequired(), Length(max=200)])
    bvn = StringField('Bank Verification Number (BVN)', validators=[Optional(), Length(min=11, max=11)])
    
    # Document Uploads
    id_document = FileField('Identity Document', validators=[
        DataRequired(), 
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    business_registration = FileField('Business Registration Document', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    tax_certificate = FileField('Tax Certificate', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    certifications = FileField('Professional Certifications', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    additional_documents = FileField('Additional Supporting Documents', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])


class OnboardingAdminReviewForm(FlaskForm):
    """Admin form for reviewing registrations"""
    registration_status = SelectField('Registration Status', choices=[
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_revision', 'Needs Revision')
    ], validators=[DataRequired()])
    admin_comments = TextAreaField('Admin Comments', validators=[Optional()], 
                                  render_kw={'rows': 4, 'placeholder': 'Comments for applicant'})
    submit = SubmitField('Update Registration Status')


class BulkOnboardingForm(FlaskForm):
    """Form for bulk onboarding via CSV upload"""
    batch_name = StringField('Batch Name', validators=[DataRequired(), Length(min=2, max=200)])
    role = SelectField('Role for All Records', choices=[
        ('farmer', 'Farmer'),
        ('aggregator', 'Aggregator'),
        ('transport_company', 'Transport Company'),
        ('bulk_trader', 'Bulk Trader'),
        ('retailer', 'Retailer'),
        ('input_supplier', 'Input Supplier')
    ], validators=[DataRequired()])
    csv_file = FileField('CSV File', validators=[
        DataRequired(),
        FileAllowed(['csv'], 'Only CSV files allowed')
    ])
    submit = SubmitField('Upload Bulk Registration')


class ProcessorOnboardingStep1Form(FlaskForm):
    """Step 1: Business Information for Agro-Processors"""
    business_name = StringField('Business Name', validators=[DataRequired(), Length(min=2, max=200)])
    cac_number = StringField('CAC Registration Number', validators=[DataRequired(), Length(min=2, max=100)])
    business_type = SelectField('Business Type', choices=[
        ('sole_proprietorship', 'Sole Proprietorship'),
        ('partnership', 'Partnership'),
        ('limited_liability', 'Limited Liability Company'),
        ('cooperative', 'Cooperative Society')
    ], validators=[DataRequired()])
    years_in_operation = IntegerField('Years in Operation', validators=[DataRequired(), NumberRange(min=0, max=100)])
    contact_person = StringField('Contact Person Name', validators=[DataRequired(), Length(min=2, max=200)])
    contact_phone = StringField('Contact Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    website = StringField('Website (Optional)', validators=[Optional(), Length(max=200)])


class ProcessorOnboardingStep2Form(FlaskForm):
    """Step 2: Processing Capacity and Products"""
    processing_capacity_tpd = FloatField('Processing Capacity (Tons per Day)', validators=[DataRequired(), NumberRange(min=0.1, max=10000)])
    products_processed = TextAreaField('Products Processed', validators=[DataRequired()], 
                                     render_kw={'rows': 4, 'placeholder': 'e.g., cassava -> garri, flour; maize -> flour, starch'})
    employees_count = IntegerField('Number of Employees', validators=[DataRequired(), NumberRange(min=1, max=10000)])
    annual_processing_volume = FloatField('Annual Processing Volume (Tons)', validators=[Optional(), NumberRange(min=0)])


class ProcessorOnboardingStep3Form(FlaskForm):
    """Step 3: Plant Location and Logistics"""
    plant_location_state = SelectField('Plant Location - State', choices=[], validators=[DataRequired()])
    plant_location_lga = StringField('Plant Location - LGA', validators=[DataRequired(), Length(max=100)])
    plant_address = TextAreaField('Complete Plant Address', validators=[DataRequired()], render_kw={'rows': 3})
    storage_capacity = FloatField('Storage Capacity (Tons)', validators=[Optional(), NumberRange(min=0)])
    has_cold_storage = BooleanField('Cold Storage Available')
    transportation_fleet = SelectField('Transportation Fleet', choices=[
        ('none', 'No Fleet - Use Third Party'),
        ('small', 'Small Fleet (1-5 vehicles)'),
        ('medium', 'Medium Fleet (6-20 vehicles)'),
        ('large', 'Large Fleet (20+ vehicles)')
    ], validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(ProcessorOnboardingStep3Form, self).__init__(*args, **kwargs)
        # Nigerian states
        nigerian_states = [
            ('abia', 'Abia'), ('adamawa', 'Adamawa'), ('akwa_ibom', 'Akwa Ibom'),
            ('anambra', 'Anambra'), ('bauchi', 'Bauchi'), ('bayelsa', 'Bayelsa'),
            ('benue', 'Benue'), ('borno', 'Borno'), ('cross_river', 'Cross River'),
            ('delta', 'Delta'), ('ebonyi', 'Ebonyi'), ('edo', 'Edo'),
            ('ekiti', 'Ekiti'), ('enugu', 'Enugu'), ('gombe', 'Gombe'),
            ('imo', 'Imo'), ('jigawa', 'Jigawa'), ('kaduna', 'Kaduna'),
            ('kano', 'Kano'), ('katsina', 'Katsina'), ('kebbi', 'Kebbi'),
            ('kogi', 'Kogi'), ('kwara', 'Kwara'), ('lagos', 'Lagos'),
            ('nasarawa', 'Nasarawa'), ('niger', 'Niger'), ('ogun', 'Ogun'),
            ('ondo', 'Ondo'), ('osun', 'Osun'), ('oyo', 'Oyo'),
            ('plateau', 'Plateau'), ('rivers', 'Rivers'), ('sokoto', 'Sokoto'),
            ('taraba', 'Taraba'), ('yobe', 'Yobe'), ('zamfara', 'Zamfara'),
            ('abuja', 'FCT Abuja')
        ]
        self.plant_location_state.choices = nigerian_states


class ProcessorOnboardingStep4Form(FlaskForm):
    """Step 4: Document Uploads"""
    nafdac_permit_file = FileField('NAFDAC Permit/License', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    utility_docs_file = FileField('Utility Documents (Lease/Title, Power Bills)', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    cac_certificate = FileField('CAC Certificate', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    tax_clearance = FileField('Tax Clearance Certificate', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])


class ProcessorOnboardingStep5Form(FlaskForm):
    """Step 5: Banking and Final Details"""
    bank_name = SelectField('Bank Name', choices=[
        ('', 'Select Bank'),
        ('access_bank', 'Access Bank'),
        ('first_bank', 'First Bank'),
        ('gtbank', 'Guaranty Trust Bank'),
        ('uba', 'United Bank for Africa'),
        ('zenith_bank', 'Zenith Bank'),
        ('fidelity_bank', 'Fidelity Bank'),
        ('union_bank', 'Union Bank'),
        ('sterling_bank', 'Sterling Bank'),
        ('stanbic_ibtc', 'Stanbic IBTC'),
        ('fcmb', 'First City Monument Bank')
    ], validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(min=10, max=10)])
    account_name = StringField('Account Name', validators=[DataRequired(), Length(min=2, max=200)])
    bvn = StringField('Bank Verification Number (BVN)', validators=[DataRequired(), Length(min=11, max=11)])
    preferred_crops = TextAreaField('Preferred Crops for Sourcing', validators=[DataRequired()],
                                   render_kw={'rows': 3, 'placeholder': 'e.g., cassava, maize, rice, yam'})


class BOILoanApplicationForm(FlaskForm):
    """BOI Loan Application Form"""
    loan_amount_requested = FloatField('Loan Amount Requested (NGN)', validators=[
        DataRequired(), 
        NumberRange(min=500000, max=500000000, message="Loan amount must be between ₦500,000 and ₦500,000,000")
    ])
    purpose_of_loan = TextAreaField('Purpose of Loan', validators=[DataRequired()], 
                                   render_kw={'rows': 4, 'placeholder': 'Detailed description of how the loan will be used'})
    tenor_months = SelectField('Loan Tenor (Months)', choices=[
        (12, '12 months'),
        (18, '18 months'),
        (24, '24 months'),
        (36, '36 months'),
        (48, '48 months'),
        (60, '60 months')
    ], coerce=int, validators=[DataRequired()])
    collateral_description = TextAreaField('Collateral Description (Optional)', validators=[Optional()],
                                         render_kw={'rows': 3, 'placeholder': 'Description of assets to be used as collateral'})
    financials_file = FileField('Financial Statements/Bank Statements', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    projections_file = FileField('Business Projections (Optional)', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
    supporting_docs_file = FileField('Supporting Documents (Optional)', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, JPEG, and PNG files allowed')
    ])
