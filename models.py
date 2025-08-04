from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    """User model for farmers, buyers, and admins"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # Extended roles for Lagos program
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # SMS integration fields
    phone_number = db.Column(db.String(20))
    sms_enabled = db.Column(db.Boolean, default=False)
    sms_registration_date = db.Column(db.DateTime)
    
    # Subscription fields
    is_premium = db.Column(db.Boolean, default=False)
    subscription_start_date = db.Column(db.DateTime)
    subscription_end_date = db.Column(db.DateTime)
    subscription_plan_code = db.Column(db.String(50))
    paystack_customer_code = db.Column(db.String(100))
    
    # Relationship with produce
    produce_listings = db.relationship('Produce', foreign_keys='Produce.farmer_id', backref='farmer', lazy=True, cascade='all, delete-orphan')
    purchased_produce = db.relationship('Produce', foreign_keys='Produce.buyer_id', backref='buyer', lazy=True)
    
    # Relationship with messages
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_farmer(self):
        """Check if user is a farmer"""
        return self.role == 'farmer'
    
    def is_buyer(self):
        """Check if user is a buyer"""
        return self.role == 'buyer'
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
        
    def has_premium_access(self):
        """Check if user has active premium subscription"""
        if not self.is_premium:
            return False
        if self.subscription_end_date and self.subscription_end_date < datetime.utcnow():
            return False
        return True
    
    def __repr__(self):
        return f'<User {self.email}>'


class ProduceLagosRegistration(db.Model):
    """Universal onboarding model for all Produce for Lagos program roles"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # Full role selection
    
    # Progress tracking
    registration_status = db.Column(db.String(20), default='in_progress')  # 'in_progress', 'completed', 'pending_approval', 'approved', 'rejected'
    current_step = db.Column(db.Integer, default=1)
    total_steps = db.Column(db.Integer, default=4)
    completion_percentage = db.Column(db.Integer, default=0)
    started_date = db.Column(db.DateTime, default=datetime.utcnow)
    completed_date = db.Column(db.DateTime)
    approved_date = db.Column(db.DateTime)
    
    # Personal Information (Step 1)
    full_name = db.Column(db.String(200))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    nationality = db.Column(db.String(50), default='Nigerian')
    state_of_origin = db.Column(db.String(50))
    lga_of_origin = db.Column(db.String(100))
    marital_status = db.Column(db.String(20))
    education_level = db.Column(db.String(50))
    primary_phone = db.Column(db.String(20))
    secondary_phone = db.Column(db.String(20))
    email_address = db.Column(db.String(120))
    
    # Address Information
    residential_address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(10))
    lga = db.Column(db.String(100))
    ward = db.Column(db.String(100))
    
    # Business/Organization Information (Step 2)
    organization_name = db.Column(db.String(200))
    business_registration_number = db.Column(db.String(100))
    tax_identification_number = db.Column(db.String(50))
    business_address = db.Column(db.Text)
    business_type = db.Column(db.String(100))
    years_in_operation = db.Column(db.Integer)
    number_of_employees = db.Column(db.Integer)
    annual_turnover = db.Column(db.String(50))
    
    # Role-specific fields (Step 3)
    # Farmer-specific
    farm_size = db.Column(db.String(50))
    crops_grown = db.Column(db.Text)  # JSON string
    farming_experience = db.Column(db.Integer)
    farming_methods = db.Column(db.Text)
    irrigation_system = db.Column(db.String(100))
    storage_facilities = db.Column(db.Text)
    
    # Aggregator-specific
    aggregation_capacity = db.Column(db.String(100))
    storage_capacity = db.Column(db.String(100))
    transportation_fleet = db.Column(db.Text)
    catchment_areas = db.Column(db.Text)
    
    # Transport Company-specific
    vehicle_types = db.Column(db.Text)
    fleet_size = db.Column(db.Integer)
    routes_covered = db.Column(db.Text)
    insurance_details = db.Column(db.Text)
    
    # Bulk Trader-specific
    trading_volume = db.Column(db.String(100))
    target_markets = db.Column(db.Text)
    commodity_specialization = db.Column(db.Text)
    
    # Retailer-specific
    store_type = db.Column(db.String(100))
    retail_locations = db.Column(db.Text)
    customer_base = db.Column(db.String(100))
    
    # Input Supplier-specific
    input_types = db.Column(db.Text)
    supplier_network = db.Column(db.Text)
    distribution_channels = db.Column(db.Text)
    
    # Financial Information (Step 4)
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(20))
    account_name = db.Column(db.String(200))
    bvn = db.Column(db.String(15))
    
    # Document uploads
    id_document_path = db.Column(db.String(500))
    business_registration_path = db.Column(db.String(500))
    tax_certificate_path = db.Column(db.String(500))
    certifications_path = db.Column(db.String(500))
    additional_documents_path = db.Column(db.String(500))
    
    # Admin fields
    admin_comments = db.Column(db.Text)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_date = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', foreign_keys=[user_id], backref='produce_lagos_registration')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def calculate_completion_percentage(self):
        """Calculate registration completion percentage"""
        total_fields = 0
        completed_fields = 0
        
        # Step 1: Personal Information (weight: 25%)
        step1_fields = [self.full_name, self.date_of_birth, self.gender, self.primary_phone, 
                       self.residential_address, self.city, self.state, self.lga]
        total_fields += len(step1_fields)
        completed_fields += sum(1 for field in step1_fields if field)
        
        # Step 2: Business Information (weight: 25%)
        if self.role not in ['farmer']:  # Business fields not required for individual farmers
            step2_fields = [self.organization_name, self.business_address, self.business_type]
            total_fields += len(step2_fields)
            completed_fields += sum(1 for field in step2_fields if field)
        
        # Step 3: Role-specific (weight: 30%)
        if self.role == 'farmer':
            role_fields = [self.farm_size, self.crops_grown, self.farming_experience]
        elif self.role == 'aggregator':
            role_fields = [self.aggregation_capacity, self.storage_capacity, self.catchment_areas]
        elif self.role == 'transport_company':
            role_fields = [self.vehicle_types, self.fleet_size, self.routes_covered]
        elif self.role == 'bulk_trader':
            role_fields = [self.trading_volume, self.target_markets, self.commodity_specialization]
        elif self.role == 'retailer':
            role_fields = [self.store_type, self.retail_locations, self.customer_base]
        elif self.role == 'input_supplier':
            role_fields = [self.input_types, self.supplier_network, self.distribution_channels]
        else:
            role_fields = []
        
        total_fields += len(role_fields)
        completed_fields += sum(1 for field in role_fields if field)
        
        # Step 4: Financial & Documents (weight: 20%)
        step4_fields = [self.bank_name, self.account_number, self.id_document_path]
        total_fields += len(step4_fields)
        completed_fields += sum(1 for field in step4_fields if field)
        
        if total_fields == 0:
            return 0
        
        percentage = int((completed_fields / total_fields) * 100)
        self.completion_percentage = percentage
        return percentage
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for registration status"""
        status_classes = {
            'in_progress': 'bg-warning',
            'completed': 'bg-info',
            'pending_approval': 'bg-primary',
            'approved': 'bg-success',
            'rejected': 'bg-danger'
        }
        return status_classes.get(self.registration_status, 'bg-secondary')
    
    def get_role_display_name(self):
        """Return human-readable role name"""
        role_names = {
            'farmer': 'Farmer',
            'aggregator': 'Aggregator',
            'transport_company': 'Transport Company',
            'bulk_trader': 'Bulk Trader',
            'retailer': 'Retailer',
            'input_supplier': 'Input Supplier',
            'investor': 'Investor',
            'government_agency': 'Government Agency',
            'ngo_dev_partner': 'NGO/Development Partner'
        }
        return role_names.get(self.role, self.role.title())
    
    def __repr__(self):
        return f'<ProduceLagosRegistration {self.user.email} - {self.role}>'


class BulkOnboarding(db.Model):
    """Model for tracking bulk onboarding operations"""
    id = db.Column(db.Integer, primary_key=True)
    batch_name = db.Column(db.String(200), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500))
    total_records = db.Column(db.Integer, default=0)
    processed_records = db.Column(db.Integer, default=0)
    successful_registrations = db.Column(db.Integer, default=0)
    failed_registrations = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='processing')  # 'processing', 'completed', 'failed'
    error_log = db.Column(db.Text)
    
    # Relationship
    uploader = db.relationship('User', backref='bulk_onboarding_batches')
    
    def __repr__(self):
        return f'<BulkOnboarding {self.batch_name}>'

class Produce(db.Model):
    """Produce model for farmer listings"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)  # e.g., "50 kg", "100 bags"
    price = db.Column(db.Float, nullable=False)  # Price per unit
    price_unit = db.Column(db.String(20), nullable=False, default='NGN')  # Currency/unit
    description = db.Column(db.Text)
    date_listed = db.Column(db.DateTime, default=datetime.utcnow)
    is_available = db.Column(db.Boolean, default=True)
    contact_method = db.Column(db.String(50), default='web')  # 'web', 'sms', 'phone'
    
    # Geographical Indications (GI) fields
    gi_label = db.Column(db.String(200))  # e.g., "Ogun Cassava", "Ebonyi Rice"
    gi_certified = db.Column(db.Boolean, default=False)
    gi_status = db.Column(db.String(20), default='none')  # 'none', 'pending', 'verified', 'rejected'
    gi_certificate_number = db.Column(db.String(100))
    gi_admin_comment = db.Column(db.Text)
    
    # Foreign key to User
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Sale status
    is_sold = db.Column(db.Boolean, default=False)
    sale_date = db.Column(db.DateTime)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<Produce {self.name}>'
    
    def formatted_price(self):
        """Return formatted price string"""
        return f"{self.price_unit} {self.price:,.2f}"
    
    def get_gi_status_badge_class(self):
        """Return Bootstrap badge class for GI status"""
        status_classes = {
            'none': 'bg-light text-dark',
            'pending': 'bg-warning',
            'verified': 'bg-success',
            'rejected': 'bg-danger'
        }
        return status_classes.get(self.gi_status, 'bg-secondary')
    
    def get_gi_display_label(self):
        """Return display label for GI status"""
        if self.gi_certified and self.gi_label:
            return f"GI: {self.gi_label}"
        elif self.gi_status == 'pending':
            return f"GI Pending: {self.gi_label or 'Review'}"
        return None


class Message(db.Model):
    """Message model for in-platform messaging system"""
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    message_body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Foreign keys
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=True)  # Optional reference to produce
    
    # Relationship with produce
    produce = db.relationship('Produce', backref='messages')
    
    def __repr__(self):
        return f'<Message {self.subject}>'
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        db.session.commit()
    
    def formatted_timestamp(self):
        """Return formatted timestamp"""
        return self.timestamp.strftime('%Y-%m-%d %H:%M')


class LogisticsRequest(db.Model):
    """Logistics request model for delivery and pickup scheduling"""
    id = db.Column(db.Integer, primary_key=True)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    request_type = db.Column(db.String(20), nullable=False)  # 'pickup' or 'delivery'
    preferred_date = db.Column(db.Date, nullable=False)
    preferred_time = db.Column(db.Time, nullable=False)
    pickup_location = db.Column(db.String(200), nullable=False)
    destination_address = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'fulfilled', 'cancelled'
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    produce = db.relationship('Produce', backref='logistics_requests')
    requester = db.relationship('User', backref='logistics_requests')
    
    def __repr__(self):
        return f'<LogisticsRequest {self.request_type} for {self.produce.name}>'
    
    def formatted_date_time(self):
        """Return formatted preferred date and time"""
        return f"{self.preferred_date.strftime('%B %d, %Y')} at {self.preferred_time.strftime('%I:%M %p')}"
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'approved': 'bg-info',
            'fulfilled': 'bg-success',
            'cancelled': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def can_be_modified(self):
        """Check if request can still be modified by requester"""
        return self.status in ['pending', 'approved']


class FundingApplication(db.Model):
    """Funding application model for Offtake Guarantee Fund"""
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=True)  # Optional
    amount_requested = db.Column(db.Float, nullable=False)
    application_reason = db.Column(db.Text, nullable=False)
    supporting_document = db.Column(db.String(255), nullable=True)  # File path
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'declined'
    admin_comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    applicant = db.relationship('User', backref='funding_applications')
    produce = db.relationship('Produce', backref='funding_applications')
    
    def __repr__(self):
        return f'<FundingApplication ${self.amount_requested} by {self.applicant.name}>'
    
    def formatted_amount(self):
        """Return formatted amount"""
        return f"NGN {self.amount_requested:,.2f}"
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'approved': 'bg-success',
            'declined': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def formatted_timestamp(self):
        """Return formatted timestamp"""
        return self.timestamp.strftime('%B %d, %Y at %I:%M %p')


class CSAData(db.Model):
    """Climate-Smart Agriculture data model for weather and farming analytics"""
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Location data
    city = db.Column(db.String(100), nullable=False, default='Lagos')
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Weather data (stored as JSON)
    weather_data = db.Column(db.Text)  # JSON string of weather info
    
    # Soil data from farmer input
    soil_type = db.Column(db.String(50))  # clay, sandy, loamy, etc.
    soil_moisture = db.Column(db.String(50))  # dry, moderate, wet
    field_size = db.Column(db.Float)  # in hectares
    
    # Carbon footprint data
    fertilizer_type = db.Column(db.String(50))  # organic, synthetic, none
    fertilizer_amount = db.Column(db.Float)  # kg per hectare
    estimated_yield = db.Column(db.Float)  # tons per hectare
    carbon_footprint = db.Column(db.Float)  # calculated CO2 equivalent
    
    # Recommendations (stored as JSON)
    crop_recommendations = db.Column(db.Text)  # JSON string of recommendations
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    farmer = db.relationship('User', backref=db.backref('csa_data', lazy=True))
    
    def get_weather_data(self):
        """Parse weather data from JSON"""
        if self.weather_data:
            import json
            return json.loads(self.weather_data)
        return {}
    
    def set_weather_data(self, data):
        """Store weather data as JSON"""
        import json
        self.weather_data = json.dumps(data)
    
    def get_crop_recommendations(self):
        """Parse crop recommendations from JSON"""
        if self.crop_recommendations:
            import json
            return json.loads(self.crop_recommendations)
        return []
    
    def set_crop_recommendations(self, recommendations):
        """Store crop recommendations as JSON"""
        import json
        self.crop_recommendations = json.dumps(recommendations)
    
    def __repr__(self):
        return f'<CSAData {self.id} - {self.farmer.name} - {self.city}>'


class ExportListing(db.Model):
    """Export listing model for cross-border trade"""
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Basic produce information
    produce_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)  # e.g., "50 tons", "100 bags"
    price = db.Column(db.Float, nullable=False)  # Price per unit
    price_unit = db.Column(db.String(20), nullable=False, default='USD')  # Currency/unit
    origin_state = db.Column(db.String(50), nullable=False)
    
    # Export details
    target_market = db.Column(db.String(100), nullable=False)  # EU, ECOWAS, US, UK, etc.
    has_phytosanitary = db.Column(db.Boolean, default=False)
    phytosanitary_file = db.Column(db.String(255))  # File path for certificate
    
    # Compliance standards (stored as JSON)
    compliance_standards = db.Column(db.Text)  # JSON string of selected standards
    
    # Additional details
    description = db.Column(db.Text)
    harvest_date = db.Column(db.Date)
    shipment_window_start = db.Column(db.Date)
    shipment_window_end = db.Column(db.Date)
    
    # Status and admin fields
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected', 'shipped'
    admin_comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    farmer = db.relationship('User', backref=db.backref('export_listings', lazy=True))
    
    def get_compliance_standards(self):
        """Parse compliance standards from JSON"""
        if self.compliance_standards:
            import json
            return json.loads(self.compliance_standards)
        return []
    
    def set_compliance_standards(self, standards):
        """Store compliance standards as JSON"""
        import json
        self.compliance_standards = json.dumps(standards)
    
    def formatted_price(self):
        """Return formatted price string"""
        return f"{self.price_unit} {self.price:,.2f}"
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'approved': 'bg-success',
            'rejected': 'bg-danger',
            'shipped': 'bg-info'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def formatted_harvest_date(self):
        """Return formatted harvest date"""
        if self.harvest_date:
            return self.harvest_date.strftime('%B %d, %Y')
        return 'Not specified'
    
    def formatted_shipment_window(self):
        """Return formatted shipment window"""
        if self.shipment_window_start and self.shipment_window_end:
            return f"{self.shipment_window_start.strftime('%b %d')} - {self.shipment_window_end.strftime('%b %d, %Y')}"
        elif self.shipment_window_start:
            return f"From {self.shipment_window_start.strftime('%B %d, %Y')}"
        return 'Not specified'
    
    def __repr__(self):
        return f'<ExportListing {self.produce_name} to {self.target_market} by {self.farmer.name}>'


class PrecisionField(db.Model):
    """Precision agriculture field model for GPS-based field mapping"""
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    crop_type = db.Column(db.String(50), nullable=False)
    field_size_hectares = db.Column(db.Float, nullable=False)
    
    # Geographic data
    coordinates = db.Column(db.Text)  # JSON string of polygon coordinates
    center_latitude = db.Column(db.Float)
    center_longitude = db.Column(db.Float)
    
    # Farming data
    planting_date = db.Column(db.Date)
    soil_type = db.Column(db.String(50))
    irrigation_type = db.Column(db.String(50))
    fertilizer_type = db.Column(db.String(50))
    
    # Analytics results (calculated)
    recommended_fertilizer_kg_ha = db.Column(db.Float)
    recommended_irrigation_l_ha = db.Column(db.Float)
    estimated_yield_tons_ha = db.Column(db.Float)
    planting_season_fit = db.Column(db.String(20))  # optimal, good, poor
    risk_warnings = db.Column(db.Text)  # JSON string of warnings
    
    # Metadata
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    farmer = db.relationship('User', backref=db.backref('precision_fields', lazy=True))
    
    def get_coordinates_list(self):
        """Parse coordinates from JSON"""
        if self.coordinates:
            try:
                import json
                return json.loads(self.coordinates)
            except:
                return []
        return []
    
    def set_coordinates(self, coords):
        """Store coordinates as JSON"""
        import json
        self.coordinates = json.dumps(coords)
    
    def get_risk_warnings_list(self):
        """Parse risk warnings from JSON"""
        if self.risk_warnings:
            try:
                import json
                return json.loads(self.risk_warnings)
            except:
                return []
        return []
    
    def set_risk_warnings(self, warnings):
        """Store risk warnings as JSON"""
        import json
        self.risk_warnings = json.dumps(warnings)
    
    def formatted_size(self):
        """Return formatted field size"""
        return f"{self.field_size_hectares:.2f} ha"
    
    def formatted_coordinates(self):
        """Return formatted center coordinates"""
        if self.center_latitude and self.center_longitude:
            return f"{self.center_latitude:.6f}, {self.center_longitude:.6f}"
        return "Not set"
    
    def get_season_fit_badge_class(self):
        """Return Bootstrap badge class for season fit"""
        fit_classes = {
            'optimal': 'bg-success',
            'good': 'bg-warning',
            'poor': 'bg-danger'
        }
        return fit_classes.get(self.planting_season_fit, 'bg-secondary')
    
    def formatted_planting_date(self):
        """Return formatted planting date"""
        if self.planting_date:
            return self.planting_date.strftime('%B %d, %Y')
        return 'Not set'
    
    def __repr__(self):
        return f'<PrecisionField {self.field_name} - {self.crop_type} by {self.farmer.name}>'


class SMSInteraction(db.Model):
    """SMS interaction model for tracking Africa's Talking SMS communications"""
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    message_type = db.Column(db.String(10), nullable=False)  # 'incoming' or 'outgoing'
    content = db.Column(db.String(500))
    status = db.Column(db.String(20), nullable=False)  # 'sent', 'received', 'failed'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SMSInteraction {self.phone_number} - {self.message_type}>'


class MatchRecommendation(db.Model):
    """AI-powered marketplace matchmaking recommendations"""
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=False)
    
    # Match details
    match_score = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    match_factors = db.Column(db.Text)  # JSON string of factors that influenced the match
    recommendation_reason = db.Column(db.Text)  # Human-readable explanation
    
    # Recommendation delivery
    delivery_method = db.Column(db.String(20), nullable=False)  # 'web', 'sms', 'email'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User response
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'declined', 'expired'
    response_at = db.Column(db.DateTime)
    response_method = db.Column(db.String(20))  # 'web', 'sms', 'message'
    
    # Outcome tracking (for ML training)
    outcome = db.Column(db.String(20))  # 'contacted', 'deal_made', 'no_response', 'rejected'
    outcome_notes = db.Column(db.Text)
    outcome_recorded_at = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref='farmer_recommendations')
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='buyer_recommendations')
    produce = db.relationship('Produce', backref='match_recommendations')
    
    def get_match_factors(self):
        """Parse match factors from JSON"""
        if self.match_factors:
            import json
            return json.loads(self.match_factors)
        return {}
    
    def set_match_factors(self, factors):
        """Store match factors as JSON"""
        import json
        self.match_factors = json.dumps(factors)
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'accepted': 'bg-success',
            'declined': 'bg-danger',
            'expired': 'bg-secondary'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def is_expired(self):
        """Check if recommendation has expired (7 days)"""
        if self.status != 'pending':
            return False
        
        expiry_date = self.sent_at + timedelta(days=7)
        return datetime.utcnow() > expiry_date
    
    def __repr__(self):
        return f'<MatchRecommendation {self.farmer.name} -> {self.buyer.name} for {self.produce.name}>'
    
    def formatted_timestamp(self):
        """Return formatted timestamp"""
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')


class Transaction(db.Model):
    """Transaction model for all payments in the platform"""
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    
    # Transaction details
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'produce_sale', 'logistics', 'subscription'
    
    # Amount breakdown
    base_amount = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, default=0.0)
    logistics_fee = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Payment status
    status = db.Column(db.String(20), default='pending')  # 'pending', 'successful', 'failed', 'cancelled'
    paystack_reference = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime)
    
    # Related entities
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'))
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'))
    
    # Metadata
    transaction_metadata = db.Column(db.Text)  # JSON metadata for additional info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='transactions')
    produce = db.relationship('Produce', backref='transaction')
    logistics_request = db.relationship('LogisticsRequest', backref='transaction')
    
    def __repr__(self):
        return f'<Transaction {self.reference}>'


class Subscription(db.Model):
    """Subscription model for premium features"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Subscription details
    plan_name = db.Column(db.String(50), nullable=False)  # 'Premium Monthly'
    plan_code = db.Column(db.String(50), nullable=False)  # Paystack plan code
    amount = db.Column(db.Float, nullable=False)  # Monthly fee
    
    # Status and dates
    status = db.Column(db.String(20), default='active')  # 'active', 'cancelled', 'expired'
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    next_billing_date = db.Column(db.DateTime)
    
    # Paystack details
    subscription_code = db.Column(db.String(100))
    customer_code = db.Column(db.String(100))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='subscriptions')
    
    def is_active(self):
        """Check if subscription is currently active"""
        if self.status != 'active':
            return False
        if self.end_date and self.end_date < datetime.utcnow():
            return False
        return True
    
    def __repr__(self):
        return f'<Subscription {self.user_id}: {self.plan_name}>'


class PaymentLog(db.Model):
    """Detailed payment logs for audit and reconciliation"""
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    
    # Log details
    event_type = db.Column(db.String(50), nullable=False)  # 'initiated', 'verified', 'failed', 'webhook'
    paystack_response = db.Column(db.Text)  # Full Paystack response
    
    # Status
    success = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transaction = db.relationship('Transaction', backref='payment_logs')
    
    def __repr__(self):
        return f'<PaymentLog {self.transaction_id}: {self.event_type}>'
