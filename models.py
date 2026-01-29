from datetime import datetime, timedelta
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
    buyer_type = db.Column(db.String(30))  # 'retail_buyer', 'bulk_trader', 'institutional_buyer', 'agro_processor'
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # SMS integration fields
    phone_number = db.Column(db.String(20))
    sms_enabled = db.Column(db.Boolean, default=False)
    sms_registration_date = db.Column(db.DateTime)
    
    # Digital inclusion fields (USSD/WhatsApp/T2)
    whatsapp_id = db.Column(db.String(50))  # WhatsApp phone ID
    t2_customer_code = db.Column(db.String(100))  # T2/9mobile wallet customer code
    t2_wallet_balance = db.Column(db.Float, default=0.0)  # T2 wallet balance in Naira
    preferred_language = db.Column(db.String(10), default='en')  # en, yo, ha, pcm, ig
    is_ussd_user = db.Column(db.Boolean, default=False)  # Registered via USSD
    source_channel = db.Column(db.String(20), default='web')  # 'web', 'ussd', 'sms', 'whatsapp', 'agent', 'agent_bulk'
    location = db.Column(db.String(200))  # Auto-filled from cell tower or manual
    registered_by_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # If agent-assisted
    
    # REGISTRATION STATUS (Lite vs Verified)
    # lite = SMS/USSD quick registration, verified = completed full web registration
    registration_status = db.Column(db.String(20), default='verified')  # 'lite', 'pending', 'verified'
    lite_registration_date = db.Column(db.DateTime)  # When lite account was created
    full_registration_date = db.Column(db.DateTime)  # When full registration was completed
    verified_by_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Agent who helped complete registration
    verification_completed_date = db.Column(db.DateTime)  # When verification was completed
    
    # Subscription fields
    is_premium = db.Column(db.Boolean, default=False)
    subscription_start_date = db.Column(db.DateTime)
    subscription_end_date = db.Column(db.DateTime)
    subscription_plan_code = db.Column(db.String(50))
    paystack_customer_code = db.Column(db.String(100))
    
    # Scam detection fields (Layer 5)
    last_ip = db.Column(db.String(45))  # IPv6 max length
    last_location = db.Column(db.String(200))  # Last known location for hop detection
    scam_score = db.Column(db.Integer, default=0)  # 0-100, higher = more suspicious
    phone_verified = db.Column(db.Boolean, default=False)  # Phone verification status
    agent_verified = db.Column(db.Boolean, default=False)  # Verified by field agent
    
    # Cell tower location fields (telecom-provided location for feature phones)
    cell_tower_id = db.Column(db.String(50))  # Cell tower ID from telecom (MCC-MNC-LAC-CID)
    network_location_lat = db.Column(db.Float)  # Latitude from cell tower triangulation
    network_location_lng = db.Column(db.Float)  # Longitude from cell tower triangulation
    location_accuracy = db.Column(db.Float)  # Accuracy in meters (cell tower ~500-2000m)
    location_timestamp = db.Column(db.DateTime)  # When location was captured
    location_source = db.Column(db.String(20))  # 'cell_tower', 'gps', 'manual', 'agent_gps'
    
    # TRADER VALUE-ADD VERIFICATION (Anti-Reseller System)
    # Traders must declare and prove they add value - not just markup
    trader_value_services = db.Column(db.String(500))  # Comma-separated: 'transport,aggregation,processing,storage,working_capital,quality_grading'
    trader_verified = db.Column(db.Boolean, default=False)  # Admin-verified value-add
    trader_verification_status = db.Column(db.String(20), default='none')  # 'none', 'pending', 'verified', 'rejected', 'suspended'
    trader_verification_notes = db.Column(db.Text)  # Admin notes on verification
    trader_verification_date = db.Column(db.DateTime)
    trader_verified_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who verified
    
    # Trader proof documents
    trader_transport_proof = db.Column(db.String(500))  # Vehicle registration, fleet photos
    trader_storage_proof = db.Column(db.String(500))  # Warehouse photos, lease agreement
    trader_processing_proof = db.Column(db.String(500))  # Equipment photos, processing license
    trader_capital_proof = db.Column(db.String(500))  # Bank statement, credit facility letter
    
    # Reseller detection metrics (auto-calculated)
    reseller_score = db.Column(db.Integer, default=0)  # 0-100, higher = more likely pure reseller
    total_purchases = db.Column(db.Integer, default=0)  # Total buy transactions
    total_sales = db.Column(db.Integer, default=0)  # Total sell transactions
    avg_markup_percentage = db.Column(db.Float, default=0.0)  # Average markup on resales
    logistics_bookings = db.Column(db.Integer, default=0)  # Times used platform logistics
    direct_farmer_deals = db.Column(db.Integer, default=0)  # Deals with original farmers
    last_reseller_check = db.Column(db.DateTime)  # Last time reseller score was calculated
    
    # CONTINUOUS VERIFICATION (Anti-Reseller Enhancement)
    verification_expiry = db.Column(db.DateTime)  # When verification needs renewal (90 days)
    last_activity_date = db.Column(db.DateTime)  # Last marketplace activity
    monthly_logistics_count = db.Column(db.Integer, default=0)  # Logistics bookings this month
    monthly_purchase_count = db.Column(db.Integer, default=0)  # Purchases this month
    consecutive_inactive_months = db.Column(db.Integer, default=0)  # Months with no value-add activity
    verification_renewal_required = db.Column(db.Boolean, default=False)  # Flag for renewal
    
    # DEVICE FINGERPRINTING (Anti-Collusion)
    device_fingerprint = db.Column(db.String(64))  # SHA256 hash of device characteristics
    user_agent_hash = db.Column(db.String(64))  # Hash of browser user agent
    registration_ip = db.Column(db.String(45))  # IP at registration
    known_ips = db.Column(db.Text)  # JSON list of known IP addresses
    linked_accounts = db.Column(db.Text)  # JSON list of potentially linked user IDs
    fingerprint_flags = db.Column(db.Integer, default=0)  # Number of fingerprint collisions
    
    # FARMER LISTING PREFERENCES (Farmer-First Control)
    farmer_listing_preference = db.Column(db.String(30), default='all_buyers')  # 'all_buyers', 'verified_only', 'direct_only', 'sabibuy_only'
    
    # STAR RATINGS
    average_rating = db.Column(db.Float, default=0.0)  # Average rating from transactions
    total_ratings = db.Column(db.Integer, default=0)  # Number of ratings received
    rating_as_seller = db.Column(db.Float, default=0.0)  # Rating when selling
    rating_as_buyer = db.Column(db.Float, default=0.0)  # Rating when buying
    
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
    
    def is_agro_processor(self):
        """Check if user is an agro-processor"""
        return self.role == 'buyer' and self.buyer_type == 'agro_processor'
    
    def get_buyer_type_display(self):
        """Get human-readable buyer type"""
        buyer_types = {
            'retail_buyer': 'Retail Buyer',
            'bulk_trader': 'Bulk Trader',
            'institutional_buyer': 'Institutional Buyer',
            'agro_processor': 'Agro Processor'
        }
        return buyer_types.get(self.buyer_type, 'Buyer')
        
    def has_premium_access(self):
        """Check if user has active premium subscription"""
        if not self.is_premium:
            return False
        if self.subscription_end_date and self.subscription_end_date < datetime.utcnow():
            return False
        return True
    
    def is_agent(self):
        """Check if user is an agent for assisted onboarding"""
        return self.role == 'agent'
    
    def get_language_display(self):
        """Get human-readable language name"""
        languages = {
            'en': 'English',
            'yo': 'Yoruba',
            'ha': 'Hausa',
            'pcm': 'Pidgin',
            'ig': 'Igbo'
        }
        return languages.get(self.preferred_language, 'English')
    
    def is_trader(self):
        """Check if user is a trader (bulk_trader buyer type)"""
        return self.role == 'buyer' and self.buyer_type == 'bulk_trader'
    
    def is_lite_account(self):
        """Check if this is a lite (SMS/USSD) account needing full registration"""
        return self.registration_status == 'lite'
    
    def is_verified_account(self):
        """Check if account has completed full registration"""
        return self.registration_status == 'verified'
    
    def upgrade_to_verified(self, verified_by_agent_id=None):
        """Upgrade lite account to verified status"""
        from datetime import datetime
        self.registration_status = 'verified'
        self.full_registration_date = datetime.utcnow()
        self.verification_completed_date = datetime.utcnow()
        if verified_by_agent_id:
            self.verified_by_agent_id = verified_by_agent_id
    
    def get_registration_status_display(self):
        """Get human-readable registration status"""
        statuses = {
            'lite': 'Lite Account (SMS/USSD)',
            'pending': 'Pending Verification',
            'verified': 'Verified ✓'
        }
        return statuses.get(self.registration_status, 'Unknown')
    
    def get_value_services_list(self):
        """Get list of declared value-add services"""
        if not self.trader_value_services:
            return []
        return [s.strip() for s in self.trader_value_services.split(',') if s.strip()]
    
    def set_value_services(self, services_list):
        """Set value-add services from list"""
        self.trader_value_services = ','.join(services_list) if services_list else ''
    
    def has_value_service(self, service):
        """Check if trader has declared a specific value-add service"""
        return service in self.get_value_services_list()
    
    def is_verified_trader(self):
        """Check if trader is verified to add value (not a pure reseller)"""
        if not self.is_trader():
            return True  # Not a trader, no verification needed
        return self.trader_verified and self.trader_verification_status == 'verified'
    
    def can_list_produce(self):
        """Check if user can list produce for sale"""
        if self.is_farmer():
            return True
        if self.is_trader():
            return self.is_verified_trader()
        return False
    
    def can_view_farmer_listings(self):
        """Check if user can see farmer listings directly"""
        if self.is_farmer():
            return True
        if self.is_admin():
            return True
        if self.is_trader():
            return self.is_verified_trader() or self.trader_verification_status == 'pending'
        return True  # Regular buyers can see
    
    def calculate_reseller_score(self):
        """Calculate reseller score based on behavior patterns
        Higher score = more likely to be a pure reseller (bad)
        Returns 0-100 score"""
        score = 0
        
        # No value-add services declared: +30 points
        if not self.trader_value_services:
            score += 30
        
        # Never used platform logistics: +20 points
        if self.logistics_bookings == 0 and self.total_purchases > 3:
            score += 20
        
        # High markup without services: +25 points
        if self.avg_markup_percentage > 30 and not self.trader_verified:
            score += 25
        
        # Only one-off transactions (no repeat farmer relationships): +15 points
        if self.total_purchases > 5 and self.direct_farmer_deals < 2:
            score += 15
        
        # Buy/sell ratio suggests pure flipping: +10 points
        if self.total_purchases > 0 and self.total_sales > 0:
            if abs(self.total_purchases - self.total_sales) < 2:
                score += 10
        
        self.reseller_score = min(100, score)
        self.last_reseller_check = datetime.utcnow()
        return self.reseller_score
    
    def get_reseller_risk_level(self):
        """Get human-readable reseller risk level"""
        if self.reseller_score >= 70:
            return 'high'
        elif self.reseller_score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def get_trader_status_badge(self):
        """Get Bootstrap badge class for trader verification status"""
        status_badges = {
            'none': ('secondary', 'Not Applied'),
            'pending': ('warning', 'Pending Review'),
            'verified': ('success', 'Verified'),
            'rejected': ('danger', 'Rejected'),
            'suspended': ('dark', 'Suspended')
        }
        status = self.trader_verification_status or 'none'
        return status_badges.get(status, ('secondary', 'Unknown'))
    
    def get_value_services_display(self):
        """Get human-readable list of value-add services"""
        service_names = {
            'transport': 'Transport/Delivery',
            'aggregation': 'Aggregation (Bulk Collection)',
            'processing': 'Processing/Packaging',
            'storage': 'Storage/Warehousing',
            'working_capital': 'Working Capital/Financing',
            'quality_grading': 'Quality Grading/Sorting',
            'market_access': 'Market Access/Export'
        }
        services = self.get_value_services_list()
        return [service_names.get(s, s.title()) for s in services]
    
    def __repr__(self):
        return f'<User {self.email}>'


class ProduceLagosRegistration(db.Model):
    """Universal onboarding model for all Produce for Lagos program roles"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # Full role selection
    program_tag = db.Column(db.String(100), default='LAFSINCO/Produce for Lagos Registration')  # Program identification tag
    
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
    crops_grown = db.Column(db.Text)  # Main crops/produce
    season_calendar = db.Column(db.String(200))  # Seasonal calendar (harvest cycles per year)
    avg_output = db.Column(db.String(200))  # Average monthly output (volume)
    farming_experience = db.Column(db.Integer)
    farming_methods = db.Column(db.Text)  # Type of farming (Crop, Livestock, Mixed)
    irrigation_methods = db.Column(db.String(200))  # Irrigation methods used
    postharvest_facilities = db.Column(db.Text)  # Post-harvest facilities available
    coop_member = db.Column(db.String(10))  # Member of farmer's cooperative or association
    extension_service = db.Column(db.String(10))  # Access to extension service
    
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
    
    # Digital inclusion: source channel tracking
    source_channel = db.Column(db.String(20), default='web')  # 'web', 'ussd', 'whatsapp', 'sms', 'agent'
    listing_location = db.Column(db.String(200))  # Location from cell tower or manual entry
    
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
    status = db.Column(db.String(20), default='pending')  # 'pending', 'bidding', 'assigned', 'in_transit', 'delivered', 'cancelled'
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New bidding fields
    quantity_tons = db.Column(db.Float, default=0.0)  # Weight in tons
    requires_cold_chain = db.Column(db.Boolean, default=False)  # Cold chain required?
    winning_bid_id = db.Column(db.Integer, db.ForeignKey('logistics_bid.id', use_alter=True), nullable=True)
    pickup_state = db.Column(db.String(50))  # Nigerian state for matching
    destination_state = db.Column(db.String(50))  # Nigerian state for matching
    
    # Payment/escrow tracking
    escrow_amount = db.Column(db.Float, default=0.0)  # Total escrow amount
    first_payment_released = db.Column(db.Boolean, default=False)  # 50% on accept
    final_payment_released = db.Column(db.Boolean, default=False)  # 50% + bonus on delivery
    cold_chain_bonus_earned = db.Column(db.Boolean, default=False)  # 15% bonus for verified cold chain
    
    # Relationships
    produce = db.relationship('Produce', backref='logistics_requests')
    requester = db.relationship('User', backref='logistics_requests')
    bids = db.relationship('LogisticsBid', foreign_keys='LogisticsBid.logistics_request_id', backref='logistics_request', lazy='dynamic')
    winning_bid = db.relationship('LogisticsBid', foreign_keys=[winning_bid_id], post_update=True)
    
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


class USSDSession(db.Model):
    """USSD session tracking for Africa's Talking and T2 USSD"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    service_code = db.Column(db.String(20))  # e.g., *712*55#
    provider = db.Column(db.String(20), default='africastalking')  # 'africastalking' or 't2'
    
    # Session state
    current_menu = db.Column(db.String(50), default='main')  # Current menu level
    current_step = db.Column(db.Integer, default=0)
    session_data = db.Column(db.Text)  # JSON for temporary form data
    
    # User tracking
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_authenticated = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='ussd_sessions')
    
    def get_session_data(self):
        """Parse session data from JSON"""
        if self.session_data:
            import json
            return json.loads(self.session_data)
        return {}
    
    def set_session_data(self, data):
        """Store session data as JSON"""
        import json
        self.session_data = json.dumps(data)
    
    def update_session_data(self, key, value):
        """Update a single key in session data"""
        data = self.get_session_data()
        data[key] = value
        self.set_session_data(data)
    
    def is_expired(self):
        """Check if session has expired (USSD sessions typically expire after 5 minutes)"""
        if self.ended_at:
            return True
        expiry_time = self.last_activity + timedelta(minutes=5)
        return datetime.utcnow() > expiry_time
    
    def __repr__(self):
        return f'<USSDSession {self.session_id} - {self.phone_number}>'


class WhatsAppInteraction(db.Model):
    """WhatsApp interaction tracking for Meta WhatsApp Cloud API"""
    id = db.Column(db.Integer, primary_key=True)
    wa_message_id = db.Column(db.String(100), unique=True)  # WhatsApp message ID
    phone_number = db.Column(db.String(20), nullable=False)
    message_type = db.Column(db.String(10), nullable=False)  # 'incoming' or 'outgoing'
    content_type = db.Column(db.String(20), default='text')  # 'text', 'audio', 'image', 'template'
    content = db.Column(db.Text)  # Message content or transcription
    
    # Voice message handling
    is_voice_note = db.Column(db.Boolean, default=False)
    voice_transcription = db.Column(db.Text)  # Transcribed text from voice note
    detected_language = db.Column(db.String(10))  # Detected language from voice
    
    # Processing status
    status = db.Column(db.String(20), default='received')  # 'received', 'processed', 'responded', 'failed'
    processing_action = db.Column(db.String(50))  # What action was taken (e.g., 'listing_created')
    
    # User tracking
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationship
    user = db.relationship('User', backref='whatsapp_interactions')
    
    def __repr__(self):
        return f'<WhatsAppInteraction {self.phone_number} - {self.message_type}>'


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
        return self.sent_at.strftime('%Y-%m-%d %H:%M:%S')


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
    
    # Payment method and status
    payment_method = db.Column(db.String(30), default='paystack')  # 'paystack', 't2_wallet', 'cash_on_delivery'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'successful', 'failed', 'cancelled'
    paystack_reference = db.Column(db.String(100))
    t2_transaction_id = db.Column(db.String(100))  # T2 wallet transaction ID
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


class ProcessorProfile(db.Model):
    """Agro-processor profile with business details and KYC information"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Business Information
    business_name = db.Column(db.String(200), nullable=False)
    cac_number = db.Column(db.String(100), nullable=False)
    processing_capacity_tpd = db.Column(db.Float)  # Tons per day
    plant_location_state = db.Column(db.String(50))
    plant_location_lga = db.Column(db.String(100))
    products_processed = db.Column(db.Text)  # e.g., cassava->garri, maize->flour
    employees_count = db.Column(db.Integer)
    
    # Document uploads
    nafdac_permit_file = db.Column(db.String(255))  # File path
    utility_docs_file = db.Column(db.String(255))   # File path
    
    # Banking and contact details
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(20))
    contact_person = db.Column(db.String(200))
    contact_phone = db.Column(db.String(20), nullable=False)
    website = db.Column(db.String(200))
    
    # KYC status
    kyc_status = db.Column(db.String(20), default='pending')  # 'pending', 'verified', 'rejected'
    admin_comment = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='processor_profile')
    
    def get_kyc_status_badge_class(self):
        """Return Bootstrap badge class for KYC status"""
        status_classes = {
            'pending': 'bg-warning',
            'verified': 'bg-success',
            'rejected': 'bg-danger'
        }
        return status_classes.get(self.kyc_status, 'bg-secondary')
    
    def is_verified(self):
        """Check if processor KYC is verified"""
        return self.kyc_status == 'verified'
    
    def __repr__(self):
        return f'<ProcessorProfile {self.business_name}>'


class LoanApplication(db.Model):
    """BOI Loan Application with payment processing fee tracking"""
    id = db.Column(db.Integer, primary_key=True)
    processor_id = db.Column(db.Integer, db.ForeignKey('processor_profile.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # For quick lookups
    
    # Loan details
    loan_amount_requested = db.Column(db.Float, nullable=False)
    purpose_of_loan = db.Column(db.Text, nullable=False)
    tenor_months = db.Column(db.Integer, nullable=False)
    collateral_description = db.Column(db.Text)
    
    # Document uploads
    financials_file = db.Column(db.String(255))      # P&L or bank statements
    projections_file = db.Column(db.String(255))     # Business projections
    supporting_docs_file = db.Column(db.String(255)) # Additional documents
    
    # Tradoja data snapshot (auto-generated)
    agrolink_data_snapshot_json = db.Column(db.Text)  # JSON data about trading activity
    
    # Application status
    status = db.Column(db.String(20), default='draft')  # 'draft', 'payment_pending', 'submitted', 'under_review', 'approved', 'declined'
    reviewer_comments = db.Column(db.Text)
    
    # Processing fee payment tracking
    platform_fee_amount = db.Column(db.Float, default=5000.00)  # ₦5,000 processing fee
    platform_fee_status = db.Column(db.String(20), default='pending')  # 'pending', 'paid', 'failed'
    payment_reference = db.Column(db.String(100))  # Paystack reference
    payment_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    
    # Relationships
    processor = db.relationship('ProcessorProfile', backref='loan_applications')
    user = db.relationship('User', backref='loan_applications')
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for application status"""
        status_classes = {
            'draft': 'bg-secondary',
            'payment_pending': 'bg-warning',
            'submitted': 'bg-info',
            'under_review': 'bg-primary',
            'approved': 'bg-success',
            'declined': 'bg-danger'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_payment_status_badge_class(self):
        """Return Bootstrap badge class for payment status"""
        status_classes = {
            'pending': 'bg-warning',
            'paid': 'bg-success',
            'failed': 'bg-danger'
        }
        return status_classes.get(self.platform_fee_status, 'bg-secondary')
    
    def is_payment_completed(self):
        """Check if processing fee has been paid"""
        return self.platform_fee_status == 'paid'
    
    def can_submit_application(self):
        """Check if application can be submitted (payment completed)"""
        return self.is_payment_completed() and self.status in ['draft', 'payment_pending']
    
    def get_agrolink_data_snapshot(self):
        """Parse Tradoja data snapshot from JSON"""
        if self.agrolink_data_snapshot_json:
            import json
            return json.loads(self.agrolink_data_snapshot_json)
        return {}
    
    def set_agrolink_data_snapshot(self, data):
        """Store Tradoja data snapshot as JSON"""
        import json
        self.agrolink_data_snapshot_json = json.dumps(data)
    
    def __repr__(self):
        return f'<LoanApplication {self.id}: ₦{self.loan_amount_requested:,.0f}>'


class TransportProfile(db.Model):
    """Transport company profile for logistics providers"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(200), nullable=False)
    cac_number = db.Column(db.String(50))  # Corporate Affairs Commission number
    fleet_size = db.Column(db.Integer, default=1)
    vehicle_types = db.Column(db.Text)  # JSON list: ["truck", "van", "pickup", "trailer"]
    routes_covered = db.Column(db.Text)  # JSON list: [["Lagos", "Oyo"], ["Lagos", "Kano"]]
    price_per_ton_km = db.Column(db.Float, default=100.0)  # Base rate in Naira
    cold_chain_capable = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=5.0)  # 1-5 rating
    total_trips = db.Column(db.Integer, default=0)
    successful_trips = db.Column(db.Integer, default=0)  # For on-time % calculation
    insurance_file = db.Column(db.String(255))  # File path
    cac_file = db.Column(db.String(255))  # File path
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # T2 wallet balance for transport payments
    wallet_balance = db.Column(db.Float, default=0.0)
    
    # LITE registration fields for USSD/SMS transporters
    profile_complete = db.Column(db.Boolean, default=False)  # True when full profile submitted
    main_location = db.Column(db.String(100))  # Primary operating location/state
    registration_channel = db.Column(db.String(50), default='web')  # ussd_lite, sms_lite, web, agent
    transporter_id = db.Column(db.String(20), unique=True)  # TRK-XXXXX unique ID
    
    # Relationship
    user = db.relationship('User', backref='transport_profile')
    
    @staticmethod
    def generate_transporter_id():
        """Generate unique transporter ID like TRK-12345"""
        import random
        while True:
            new_id = f"TRK-{random.randint(10000, 99999)}"
            existing = TransportProfile.query.filter_by(transporter_id=new_id).first()
            if not existing:
                return new_id
    
    def get_vehicle_types_list(self):
        """Parse vehicle types from JSON"""
        import json
        if self.vehicle_types:
            return json.loads(self.vehicle_types)
        return []
    
    def set_vehicle_types_list(self, types_list):
        """Store vehicle types as JSON"""
        import json
        self.vehicle_types = json.dumps(types_list)
    
    def get_routes_covered_list(self):
        """Parse routes from JSON"""
        import json
        if self.routes_covered:
            return json.loads(self.routes_covered)
        return []
    
    def set_routes_covered_list(self, routes_list):
        """Store routes as JSON"""
        import json
        self.routes_covered = json.dumps(routes_list)
    
    def covers_route(self, from_state, to_state):
        """Check if transporter covers specific route"""
        routes = self.get_routes_covered_list()
        for route in routes:
            if len(route) >= 2:
                if (route[0].lower() == from_state.lower() and route[1].lower() == to_state.lower()) or \
                   (route[1].lower() == from_state.lower() and route[0].lower() == to_state.lower()):
                    return True
        return False
    
    def on_time_percentage(self):
        """Calculate on-time delivery percentage"""
        if self.total_trips == 0:
            return 100.0
        return (self.successful_trips / self.total_trips) * 100
    
    def __repr__(self):
        return f'<TransportProfile {self.company_name}>'


class ColdChainDevice(db.Model):
    """Cold chain monitoring device attached to transport vehicle"""
    id = db.Column(db.Integer, primary_key=True)
    transporter_id = db.Column(db.Integer, db.ForeignKey('transport_profile.id'), nullable=False)
    device_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique device identifier
    vehicle_registration = db.Column(db.String(50), nullable=False)
    max_temp_allowed = db.Column(db.Float, default=4.0)  # Maximum allowed temperature in Celsius
    min_temp_allowed = db.Column(db.Float, default=-2.0)  # Minimum allowed temperature
    is_active = db.Column(db.Boolean, default=True)
    last_reading_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    transporter = db.relationship('TransportProfile', backref='cold_chain_devices')
    
    def __repr__(self):
        return f'<ColdChainDevice {self.device_id} on {self.vehicle_registration}>'


class ColdChainLog(db.Model):
    """Temperature and location log from cold chain device"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(100), nullable=False)  # Links to ColdChainDevice.device_id
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'), nullable=False)
    temperature_celsius = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    trip_verified = db.Column(db.Boolean, nullable=True)  # Null = pending, True = passed, False = failed
    
    # Relationship
    logistics_request = db.relationship('LogisticsRequest', backref='cold_chain_logs')
    
    def is_within_range(self, max_temp, min_temp=-2.0):
        """Check if temperature is within acceptable range"""
        return min_temp <= self.temperature_celsius <= max_temp
    
    def __repr__(self):
        return f'<ColdChainLog {self.temperature_celsius}°C at {self.timestamp}>'


class LogisticsBid(db.Model):
    """Bid from transporter on logistics request"""
    id = db.Column(db.Integer, primary_key=True)
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'), nullable=False)
    transporter_id = db.Column(db.Integer, db.ForeignKey('transport_profile.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)  # Total bid in Naira
    eta_hours = db.Column(db.Integer, default=24)  # Estimated time of arrival in hours
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'accepted', 'rejected', 'withdrawn'
    source_channel = db.Column(db.String(20), default='web')  # 'web', 'ussd', 'sms', 'whatsapp'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    transporter = db.relationship('TransportProfile', backref='bids')
    
    def formatted_amount(self):
        """Return formatted bid amount"""
        return f"₦{self.bid_amount:,.0f}"
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'accepted': 'bg-success',
            'rejected': 'bg-danger',
            'withdrawn': 'bg-secondary'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def __repr__(self):
        return f'<LogisticsBid ₦{self.bid_amount:,.0f} by {self.transporter.company_name}>'


class AgentProfile(db.Model):
    """Agent profile for field agents who register farmers/buyers"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    agent_id = db.Column(db.String(20), unique=True)  # AGT-XXXXX unique ID
    lga = db.Column(db.String(100))  # Local Government Area
    referral_code_used = db.Column(db.String(50))  # Referral/NYSC code used during registration
    registration_channel = db.Column(db.String(50), default='web')  # ussd_lite, sms_lite, web
    is_approved = db.Column(db.Boolean, default=False)  # Manual approval required (auto for NYSC)
    is_nysc = db.Column(db.Boolean, default=False)  # Auto-approved if NYSC member
    
    # Performance tracking
    total_farmers_registered = db.Column(db.Integer, default=0)
    total_buyers_registered = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)  # Cumulative earnings in Naira
    pending_earnings = db.Column(db.Float, default=0.0)  # Earnings not yet paid out
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationship
    user = db.relationship('User', foreign_keys=[user_id], backref='agent_profile')
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    @staticmethod
    def generate_agent_id():
        """Generate unique agent ID like AGT-04821"""
        import random
        while True:
            new_id = f"AGT-{random.randint(10000, 99999)}"
            existing = AgentProfile.query.filter_by(agent_id=new_id).first()
            if not existing:
                return new_id
    
    @staticmethod
    def is_valid_nysc_code(code):
        """Check if code looks like a valid NYSC state code (e.g., NYSC-EN/24C/1234)"""
        if not code:
            return False
        code_upper = code.upper()
        if code_upper.startswith('NYSC-') or code_upper.startswith('NYSC/'):
            return True
        # Also accept state codes like EN/24C/1234
        import re
        if re.match(r'^[A-Z]{2}/\d{2}[A-Z]/\d+$', code_upper):
            return True
        return False
    
    def calculate_bonus(self):
        """Calculate bonus based on registrations (₦200 per 10 farmers)"""
        bonus_per_batch = 200.0
        farmers_per_batch = 10
        batches = self.total_farmers_registered // farmers_per_batch
        return batches * bonus_per_batch
    
    def __repr__(self):
        return f'<AgentProfile {self.agent_id} - {self.user.name if self.user else "Unknown"}>'


class ScamFlag(db.Model):
    """Scam detection flags for admin review (Layer 5)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    action_type = db.Column(db.String(30), nullable=False)  # 'registration', 'produce_listing', 'logistics_bid', 'payout_request'
    scam_score = db.Column(db.Integer, nullable=False)  # 0-100
    reason = db.Column(db.Text, nullable=False)  # Detailed reason for flagging
    
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'banned', 'agent_call_pending', 'verified'
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    
    user = db.relationship('User', foreign_keys=[user_id], backref='scam_flags')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'pending': 'bg-warning',
            'approved': 'bg-success',
            'banned': 'bg-danger',
            'agent_call_pending': 'bg-info',
            'verified': 'bg-primary'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_score_badge_class(self):
        """Return Bootstrap badge class for scam score"""
        if self.scam_score >= 70:
            return 'bg-danger'
        elif self.scam_score >= 50:
            return 'bg-warning'
        else:
            return 'bg-success'
    
    def formatted_timestamp(self):
        """Return formatted timestamp"""
        return self.detected_at.strftime('%Y-%m-%d %H:%M')
    
    def __repr__(self):
        return f'<ScamFlag {self.id}: {self.user.name if self.user else "Unknown"} - Score {self.scam_score}>'


class SabiBuy(db.Model):
    """
    SabiBuy Group-Buy Campaign Model
    Zero-stock group-buying engine where anyone can become a trader
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Campaign identification
    code = db.Column(db.String(30), unique=True, nullable=False)  # e.g., NGOZI-SABIBUY-48K
    
    # Organizer (SabiBuyer)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Linked produce listing from farmer
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=False)
    
    # Pricing
    farm_price = db.Column(db.Float, nullable=False)  # Price from farmer per unit
    selling_price = db.Column(db.Float, nullable=False)  # SabiBuyer's selling price per unit
    price_unit = db.Column(db.String(20), default='bag')  # bag, kg, crate, etc.
    profit_margin = db.Column(db.Float)  # Auto-calculated profit per unit
    
    # Batch configuration
    minimum_quantity = db.Column(db.Integer, default=50)  # Min to close batch
    maximum_quantity = db.Column(db.Integer, default=500)  # Max capacity
    current_quantity = db.Column(db.Integer, default=0)  # Orders collected
    
    # Delivery
    delivery_lga = db.Column(db.String(100))  # Drop-off LGA
    delivery_market = db.Column(db.String(200))  # Specific market/location
    delivery_state = db.Column(db.String(50))
    estimated_delivery_date = db.Column(db.DateTime)
    actual_delivery_date = db.Column(db.DateTime)
    
    # Campaign status
    status = db.Column(db.String(20), default='active')  # active, closed, booked, in_transit, delivered, cancelled, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)  # When minimum reached
    expires_at = db.Column(db.DateTime)  # Auto-expire if not filled
    
    # Escrow tracking
    total_escrow = db.Column(db.Float, default=0.0)  # Total collected in escrow
    escrow_released = db.Column(db.Boolean, default=False)
    
    # CAPTAIN BOND SYSTEM (forfeit on abandonment)
    bond_required = db.Column(db.Boolean, default=False)  # Captain campaigns require bond
    bond_amount = db.Column(db.Float, default=0.0)  # ₦2,000 - ₦10,000 based on batch size
    bond_paid = db.Column(db.Boolean, default=False)
    bond_payment_ref = db.Column(db.String(100))
    bond_status = db.Column(db.String(20), default='none')  # none, held, released, forfeited
    bond_forfeited_at = db.Column(db.DateTime)
    bond_forfeit_reason = db.Column(db.String(200))
    
    # AUTO-CANCELLATION & REFUND
    auto_refunded = db.Column(db.Boolean, default=False)  # True if batch expired and refunded
    refund_initiated_at = db.Column(db.DateTime)
    total_refunded = db.Column(db.Float, default=0.0)
    cancellation_reason = db.Column(db.String(200))
    
    # Logistics integration
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'))
    
    # Financial tracking
    total_revenue = db.Column(db.Float, default=0.0)
    organizer_profit = db.Column(db.Float, default=0.0)
    profit_paid = db.Column(db.Boolean, default=False)
    profit_paid_at = db.Column(db.DateTime)
    
    # Source channel
    source_channel = db.Column(db.String(20), default='web')  # web, ussd, sms
    
    # Relationships
    organizer = db.relationship('User', backref='sabibuy_campaigns')
    produce = db.relationship('Produce', backref='sabibuy_campaigns')
    logistics_request = db.relationship('LogisticsRequest', backref='sabibuy')
    orders = db.relationship('SabiBuyOrder', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')
    
    @staticmethod
    def generate_code(organizer_name, price):
        """Generate unique SabiBuy code like NGOZI-SABIBUY-48K"""
        import random
        import re
        
        # Clean name - take first name, uppercase, max 8 chars
        first_name = organizer_name.split()[0].upper()[:8]
        first_name = re.sub(r'[^A-Z]', '', first_name)
        if not first_name:
            first_name = 'SABI'
        
        # Format price (e.g., 48000 -> 48K, 150000 -> 150K)
        if price >= 1000:
            price_str = f"{int(price/1000)}K"
        else:
            price_str = str(int(price))
        
        # Generate unique code
        while True:
            suffix = random.randint(10, 99)
            code = f"{first_name}-SABIBUY-{price_str}{suffix}"
            existing = SabiBuy.query.filter_by(code=code).first()
            if not existing:
                return code
    
    def calculate_progress_percentage(self):
        """Calculate batch fill percentage"""
        if self.minimum_quantity == 0:
            return 100
        return min(100, int((self.current_quantity / self.minimum_quantity) * 100))
    
    def is_ready_to_close(self):
        """Check if minimum quantity reached"""
        return self.current_quantity >= self.minimum_quantity
    
    def calculate_organizer_profit(self):
        """Calculate total profit for organizer"""
        return (self.selling_price - self.farm_price) * self.current_quantity
    
    def get_status_badge_class(self):
        """Return Bootstrap badge class for status"""
        status_classes = {
            'active': 'bg-primary',
            'closed': 'bg-info',
            'booked': 'bg-warning',
            'in_transit': 'bg-secondary',
            'delivered': 'bg-success',
            'cancelled': 'bg-danger',
            'expired': 'bg-dark'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_localized_name(self, language='en'):
        """Get localized SabiBuy name"""
        names = {
            'en': 'SabiBuy',
            'pcm': 'SabiBuy',
            'yo': 'SabiRa',
            'ha': 'SaniSaya',
            'ig': 'SabiBuy'
        }
        return names.get(language, 'SabiBuy')
    
    def __repr__(self):
        return f'<SabiBuy {self.code}: {self.current_quantity}/{self.minimum_quantity} {self.status}>'


class SabiBuyOrder(db.Model):
    """
    Individual orders/participations in a SabiBuy campaign
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Campaign link
    sabibuy_id = db.Column(db.Integer, db.ForeignKey('sabi_buy.id'), nullable=False)
    
    # Buyer details
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # If registered user
    buyer_phone = db.Column(db.String(20), nullable=False)  # Phone for all orders
    buyer_name = db.Column(db.String(100))  # Name (optional for SMS orders)
    
    # Order details
    quantity = db.Column(db.Integer, nullable=False)  # Number of bags/units
    unit_price = db.Column(db.Float, nullable=False)  # Price per unit at time of order
    total_amount = db.Column(db.Float, nullable=False)  # quantity * unit_price
    
    # Payment status
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded, released
    payment_method = db.Column(db.String(20))  # t2_wallet, paystack, cash
    payment_reference = db.Column(db.String(100))  # Transaction reference
    paid_at = db.Column(db.DateTime)
    
    # Escrow
    in_escrow = db.Column(db.Boolean, default=False)
    escrow_released_at = db.Column(db.DateTime)
    
    # Refund tracking
    refund_amount = db.Column(db.Float)
    refund_reference = db.Column(db.String(100))
    refund_reason = db.Column(db.String(200))
    refunded_at = db.Column(db.DateTime)
    
    # Delivery tracking
    delivered = db.Column(db.Boolean, default=False)
    delivered_at = db.Column(db.DateTime)
    delivery_confirmed_by = db.Column(db.String(100))  # Phone/name of person who received
    
    # Order source
    source_channel = db.Column(db.String(20), default='web')  # web, ussd, sms
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Language preference for notifications
    preferred_language = db.Column(db.String(10), default='en')
    
    # Relationships
    buyer = db.relationship('User', backref='sabibuy_orders')
    
    def get_status_display(self):
        """Get human-readable status"""
        statuses = {
            'pending': 'Awaiting Payment',
            'paid': 'Paid - In Escrow',
            'refunded': 'Refunded',
            'released': 'Completed'
        }
        return statuses.get(self.payment_status, 'Unknown')
    
    def __repr__(self):
        return f'<SabiBuyOrder {self.id}: {self.quantity} units - {self.payment_status}>'


class SabiBuyerProfile(db.Model):
    """
    SabiBuyer tier and profile management
    Tracks earnings, tier upgrades, and subscription status
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Tier system
    tier = db.Column(db.String(20), default='free')  # free, captain, premium
    tier_upgraded_at = db.Column(db.DateTime)
    captain_fee_paid = db.Column(db.Boolean, default=False)  # ₦5,000 one-time
    captain_payment_ref = db.Column(db.String(100))
    
    # Premium subscription
    is_premium = db.Column(db.Boolean, default=False)
    premium_start_date = db.Column(db.DateTime)
    premium_end_date = db.Column(db.DateTime)
    premium_subscription_code = db.Column(db.String(100))  # Paystack subscription
    
    # Stats
    total_campaigns = db.Column(db.Integer, default=0)
    successful_campaigns = db.Column(db.Integer, default=0)
    total_earnings = db.Column(db.Float, default=0.0)
    pending_earnings = db.Column(db.Float, default=0.0)
    total_gmv = db.Column(db.Float, default=0.0)  # Gross Merchandise Value
    
    # Active campaign tracking (free tier max 3)
    active_campaigns_count = db.Column(db.Integer, default=0)
    
    # Badge display
    has_gold_badge = db.Column(db.Boolean, default=False)
    
    # Registration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='sabibuyer_profile', uselist=False)
    
    def can_create_campaign(self):
        """Check if user can create a new SabiBuy campaign based on tier"""
        if self.tier == 'premium' or self.tier == 'captain':
            return True
        # Free tier: max 3 active campaigns
        return self.active_campaigns_count < 3
    
    def get_max_campaigns(self):
        """Get maximum allowed active campaigns"""
        if self.tier == 'premium' or self.tier == 'captain':
            return 999  # Unlimited
        return 3
    
    def get_tier_display(self):
        """Get human-readable tier name"""
        tiers = {
            'free': 'Free Tier',
            'captain': 'SabiBuyer Captain 🏆',
            'premium': 'Premium Member ⭐'
        }
        return tiers.get(self.tier, 'Free Tier')
    
    def get_tier_badge_class(self):
        """Return Bootstrap badge class for tier"""
        tier_classes = {
            'free': 'bg-secondary',
            'captain': 'bg-warning text-dark',
            'premium': 'bg-primary'
        }
        return tier_classes.get(self.tier, 'bg-secondary')
    
    def get_localized_tier(self, language='en'):
        """Get localized tier name"""
        tier_names = {
            'en': {
                'free': 'SabiBuyer',
                'captain': 'SabiBuyer Captain',
                'premium': 'Premium SabiBuyer'
            },
            'pcm': {
                'free': 'SabiBuyer',
                'captain': 'SabiBuyer Captain',
                'premium': 'Premium SabiBuyer'
            },
            'yo': {
                'free': 'Oníṣòwò Sabi',
                'captain': 'Olórí Oníṣòwò Sabi',
                'premium': 'Oníṣòwò Sabi Pataki'
            },
            'ha': {
                'free': 'Mai Hankali',
                'captain': 'Shugaban Mai Hankali',
                'premium': 'Mai Hankali Na Musamman'
            },
            'ig': {
                'free': 'Onye Sabi',
                'captain': 'Onyeisi Sabi',
                'premium': 'Onye Sabi Puru Iche'
            }
        }
        lang_tiers = tier_names.get(language, tier_names['en'])
        return lang_tiers.get(self.tier, lang_tiers['free'])
    
    def __repr__(self):
        return f'<SabiBuyerProfile {self.user.name if self.user else "Unknown"}: {self.tier}>'


class TraderFeedback(db.Model):
    """Feedback from farmers about traders - used for continuous verification"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Who is rating whom
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Related transaction
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'))
    
    # Ratings (1-5 stars)
    overall_rating = db.Column(db.Integer, nullable=False)  # 1-5
    payment_speed_rating = db.Column(db.Integer)  # How fast they paid
    communication_rating = db.Column(db.Integer)  # Communication quality
    fairness_rating = db.Column(db.Integer)  # Fair pricing/negotiation
    
    # Flags
    would_work_again = db.Column(db.Boolean, default=True)
    provided_transport = db.Column(db.Boolean, default=False)  # Did trader actually provide transport?
    paid_upfront = db.Column(db.Boolean, default=False)  # Did trader pay before resale?
    added_value = db.Column(db.Boolean, default=True)  # Overall - did trader add value?
    
    # Comments
    feedback_text = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref='given_feedback')
    trader = db.relationship('User', foreign_keys=[trader_id], backref='received_feedback')
    produce = db.relationship('Produce', backref='trader_feedback')
    
    def __repr__(self):
        return f'<TraderFeedback {self.farmer_id} -> {self.trader_id}: {self.overall_rating}/5>'


class Dispute(db.Model):
    """Dispute/complaint system with tiered SLAs"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Parties
    complainant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    respondent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Related entities
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'))
    logistics_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'))
    sabibuy_id = db.Column(db.Integer, db.ForeignKey('sabi_buy.id'))
    
    # Dispute details
    dispute_type = db.Column(db.String(50), nullable=False)  # 'quality', 'non_delivery', 'payment', 'fraud', 'other'
    severity = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high', 'critical'
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence_files = db.Column(db.Text)  # JSON list of file paths
    
    # Status and SLA
    status = db.Column(db.String(30), default='open')  # 'open', 'investigating', 'awaiting_response', 'resolved', 'escalated', 'closed'
    sla_response_by = db.Column(db.DateTime)  # Must respond within 24hrs
    sla_resolution_by = db.Column(db.DateTime)  # Must resolve within 72hrs
    sla_breached = db.Column(db.Boolean, default=False)
    
    # Resolution
    resolution_type = db.Column(db.String(50))  # 'refund_full', 'refund_partial', 'replacement', 'credit', 'dismissed', 'escalated'
    resolution_amount = db.Column(db.Float)  # Refund amount if applicable
    resolution_notes = db.Column(db.Text)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_at = db.Column(db.DateTime)
    
    # Channel
    source_channel = db.Column(db.String(20), default='web')  # 'web', 'sms', 'ussd', 'whatsapp'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    complainant = db.relationship('User', foreign_keys=[complainant_id], backref='disputes_filed')
    respondent = db.relationship('User', foreign_keys=[respondent_id], backref='disputes_received')
    resolver = db.relationship('User', foreign_keys=[resolved_by])
    produce = db.relationship('Produce', backref='disputes')
    
    def set_sla_deadlines(self):
        """Set SLA deadlines based on severity"""
        now = datetime.utcnow()
        if self.severity == 'critical':
            self.sla_response_by = now + timedelta(hours=4)
            self.sla_resolution_by = now + timedelta(hours=24)
        elif self.severity == 'high':
            self.sla_response_by = now + timedelta(hours=12)
            self.sla_resolution_by = now + timedelta(hours=48)
        elif self.severity == 'medium':
            self.sla_response_by = now + timedelta(hours=24)
            self.sla_resolution_by = now + timedelta(hours=72)
        else:  # low
            self.sla_response_by = now + timedelta(hours=48)
            self.sla_resolution_by = now + timedelta(days=7)
    
    def check_sla_breach(self):
        """Check if SLA has been breached"""
        now = datetime.utcnow()
        if self.status == 'open' and self.sla_response_by and now > self.sla_response_by:
            self.sla_breached = True
        if self.status not in ['resolved', 'closed'] and self.sla_resolution_by and now > self.sla_resolution_by:
            self.sla_breached = True
        return self.sla_breached
    
    def get_status_badge(self):
        """Get Bootstrap badge class for status"""
        status_badges = {
            'open': ('warning', 'Open'),
            'investigating': ('info', 'Investigating'),
            'awaiting_response': ('secondary', 'Awaiting Response'),
            'resolved': ('success', 'Resolved'),
            'escalated': ('danger', 'Escalated'),
            'closed': ('dark', 'Closed')
        }
        return status_badges.get(self.status, ('secondary', 'Unknown'))
    
    def __repr__(self):
        return f'<Dispute #{self.id}: {self.dispute_type} - {self.status}>'


class DeviceFingerprint(db.Model):
    """Track device fingerprints for anti-collusion detection"""
    id = db.Column(db.Integer, primary_key=True)
    
    fingerprint_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA256 hash
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # Linked users
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Metadata
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    times_seen = db.Column(db.Integer, default=1)
    
    # Relationships
    user = db.relationship('User', backref='device_fingerprints')
    
    def __repr__(self):
        return f'<DeviceFingerprint {self.fingerprint_hash[:16]}... for user {self.user_id}>'


class RegistrationPolicy(db.Model):
    """Admin-configurable registration requirements per role"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Role this policy applies to
    role = db.Column(db.String(30), nullable=False, unique=True)  # farmer, buyer, trader, transporter, agent
    
    # Display settings
    display_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Required fields (JSON list of field names)
    required_fields = db.Column(db.Text, default='["name", "phone_number", "location"]')
    
    # Document requirements (JSON list)
    required_documents = db.Column(db.Text, default='[]')  # e.g., ["id_card", "business_registration"]
    
    # Verification settings
    requires_admin_approval = db.Column(db.Boolean, default=False)
    requires_agent_verification = db.Column(db.Boolean, default=False)
    auto_approve_lite = db.Column(db.Boolean, default=True)  # Auto-approve LITE accounts to start trading
    
    # Fee settings
    transaction_fee_percent = db.Column(db.Float, default=2.0)  # Default 2%
    
    # Trader-specific settings
    requires_value_add_proof = db.Column(db.Boolean, default=False)  # For traders
    requires_captain_bond = db.Column(db.Boolean, default=False)  # For SabiBuy captains
    bond_amount = db.Column(db.Float, default=10000.0)  # Captain bond in Naira
    
    # Verification expiry
    verification_expiry_days = db.Column(db.Integer, default=90)  # 90 days for traders
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def get_required_fields_list(self):
        """Get list of required fields"""
        import json
        try:
            return json.loads(self.required_fields or '[]')
        except:
            return []
    
    def get_required_documents_list(self):
        """Get list of required documents"""
        import json
        try:
            return json.loads(self.required_documents or '[]')
        except:
            return []
    
    def set_required_fields(self, fields_list):
        """Set required fields from list"""
        import json
        self.required_fields = json.dumps(fields_list)
    
    def set_required_documents(self, docs_list):
        """Set required documents from list"""
        import json
        self.required_documents = json.dumps(docs_list)
    
    @staticmethod
    def get_default_policies():
        """Get default policies for each role"""
        return {
            'farmer': {
                'display_name': 'Farmer',
                'description': 'Farmers who grow and sell produce',
                'required_fields': '["name", "phone_number", "location"]',
                'required_documents': '[]',
                'requires_admin_approval': False,
                'auto_approve_lite': True,
                'transaction_fee_percent': 1.5
            },
            'buyer': {
                'display_name': 'Direct Buyer',
                'description': 'Buyers who purchase for personal/business use',
                'required_fields': '["name", "phone_number", "email"]',
                'required_documents': '[]',
                'requires_admin_approval': False,
                'auto_approve_lite': True,
                'transaction_fee_percent': 2.0
            },
            'bulk_trader': {
                'display_name': 'Trader/Aggregator',
                'description': 'Traders who buy to resell - requires value-add verification',
                'required_fields': '["name", "phone_number", "email", "location", "business_name"]',
                'required_documents': '["business_registration", "value_add_proof"]',
                'requires_admin_approval': True,
                'requires_value_add_proof': True,
                'auto_approve_lite': False,
                'transaction_fee_percent': 3.5,
                'verification_expiry_days': 90
            },
            'transport_company': {
                'display_name': 'Transporter',
                'description': 'Logistics and transport service providers',
                'required_fields': '["name", "phone_number", "email", "company_name"]',
                'required_documents': '["vehicle_registration", "drivers_license"]',
                'requires_admin_approval': True,
                'auto_approve_lite': False,
                'transaction_fee_percent': 2.0
            },
            'agent': {
                'display_name': 'Field Agent',
                'description': 'Agents who help register rural farmers',
                'required_fields': '["name", "phone_number", "email", "location"]',
                'required_documents': '["id_card"]',
                'requires_admin_approval': True,
                'auto_approve_lite': False,
                'transaction_fee_percent': 0
            }
        }
    
    def __repr__(self):
        return f'<RegistrationPolicy {self.role}: {self.display_name}>'


class WalletTransaction(db.Model):
    """T2 Wallet transaction log for SMS/USSD users"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    transaction_type = db.Column(db.String(20), nullable=False)  # 'credit', 'debit', 'transfer_in', 'transfer_out'
    amount = db.Column(db.Float, nullable=False)
    balance_before = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float, nullable=False)
    
    description = db.Column(db.String(500))
    reference = db.Column(db.String(100), unique=True, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed', 'reversed'
    channel = db.Column(db.String(20), default='system')  # 'sms', 'ussd', 'web', 'system'
    
    related_transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'))
    related_produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'))
    related_escrow_id = db.Column(db.Integer, db.ForeignKey('escrow_hold.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='wallet_transactions')
    related_transaction = db.relationship('Transaction', backref='wallet_transactions')
    related_produce = db.relationship('Produce', backref='wallet_transactions')
    
    def __repr__(self):
        return f'<WalletTransaction {self.reference}: {self.transaction_type} N{self.amount}>'


class EscrowHold(db.Model):
    """Escrow holds for buyer protection"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500))
    reference = db.Column(db.String(100), unique=True, nullable=False)
    
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'))
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'))
    sabibuy_order_id = db.Column(db.Integer, db.ForeignKey('sabi_buy_order.id'))
    
    status = db.Column(db.String(20), default='held')  # 'held', 'released', 'refunded', 'disputed'
    hold_date = db.Column(db.DateTime, default=datetime.utcnow)
    release_date = db.Column(db.DateTime)
    released_to_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    dispute_reason = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    ai_verified = db.Column(db.Boolean, default=False)  # AI verified release
    ai_risk_score = db.Column(db.Integer)  # AI risk score at time of hold
    
    user = db.relationship('User', foreign_keys=[user_id], backref='escrow_holds')
    released_to = db.relationship('User', foreign_keys=[released_to_id])
    produce = db.relationship('Produce', backref='escrow_holds')
    logistics_request = db.relationship('LogisticsRequest', backref='escrow_holds')
    
    def __repr__(self):
        return f'<EscrowHold {self.reference}: N{self.amount} ({self.status})>'


class Order(db.Model):
    """Order model for tracking complete transaction lifecycle with OTP verification"""
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(20), unique=True, nullable=False)  # e.g., ORD-7842
    
    # Parties involved
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transporter_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Assigned transporter
    
    # Order details
    produce_id = db.Column(db.Integer, db.ForeignKey('produce.id'), nullable=False)
    quantity = db.Column(db.String(100))
    total_amount = db.Column(db.Float, nullable=False)
    logistics_fee = db.Column(db.Float, default=0.0)
    platform_fee = db.Column(db.Float, default=0.0)
    
    # Delivery type
    delivery_type = db.Column(db.String(20), default='delivery')  # 'delivery' or 'pickup'
    pickup_location = db.Column(db.String(300))
    destination = db.Column(db.String(300))
    
    # Status tracking
    status = db.Column(db.String(30), default='pending')  
    # pending, accepted, pickup_confirmed, in_transit, delivered, completed, cancelled, disputed
    
    # OTP Verification (Transaction Verification)
    delivery_otp = db.Column(db.String(6))  # 4-6 digit OTP sent to buyer
    otp_generated_at = db.Column(db.DateTime)
    otp_verified = db.Column(db.Boolean, default=False)
    otp_verified_at = db.Column(db.DateTime)
    otp_attempts = db.Column(db.Integer, default=0)  # Failed attempts count
    
    # Transaction verification timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)  # Farmer accepts order
    pickup_confirmed_at = db.Column(db.DateTime)  # Farmer confirms goods handed to transporter
    in_transit_at = db.Column(db.DateTime)  # Transporter starts journey
    delivered_at = db.Column(db.DateTime)  # Transporter confirms delivery with OTP
    completed_at = db.Column(db.DateTime)  # Escrow released
    cancelled_at = db.Column(db.DateTime)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who cancelled
    cancellation_reason = db.Column(db.String(300))  # Reason for cancellation
    transport_claimed_at = db.Column(db.DateTime)  # When transporter claimed job
    
    # Location tracking (for transporters)
    last_location = db.Column(db.String(300))  # Last reported location
    last_location_time = db.Column(db.DateTime)
    
    # Escrow tracking
    escrow_id = db.Column(db.Integer, db.ForeignKey('escrow_hold.id'))
    escrow_released = db.Column(db.Boolean, default=False)
    
    # Linked logistics request (if platform logistics used)
    logistics_request_id = db.Column(db.Integer, db.ForeignKey('logistics_request.id'))
    
    # SMS/USSD channel tracking
    source_channel = db.Column(db.String(20), default='web')  # 'web', 'sms', 'ussd'
    
    # Relationships
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref='orders_as_farmer')
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='orders_as_buyer')
    transporter = db.relationship('User', foreign_keys=[transporter_id], backref='orders_as_transporter')
    produce = db.relationship('Produce', backref='orders')
    escrow = db.relationship('EscrowHold', backref='order')
    logistics_request = db.relationship('LogisticsRequest', backref='order')
    
    def generate_order_code(self):
        """Generate unique order code"""
        import random
        self.order_code = f"ORD-{random.randint(1000, 9999)}"
        return self.order_code
    
    def generate_delivery_otp(self):
        """Generate 4-digit OTP for delivery verification"""
        import random
        self.delivery_otp = str(random.randint(1000, 9999))
        self.otp_generated_at = datetime.utcnow()
        self.otp_attempts = 0
        return self.delivery_otp
    
    def verify_otp(self, otp_input):
        """Verify OTP and update status with security checks"""
        # Check attempt limit
        if self.otp_attempts >= 3:
            return False, "Too many attempts. Contact support."
        
        # Check OTP expiry (24 hours)
        if self.otp_generated_at:
            expiry_time = self.otp_generated_at + timedelta(hours=24)
            if datetime.utcnow() > expiry_time:
                return False, "OTP expired. Contact seller for new code."
        
        # Verify OTP
        if str(otp_input) == str(self.delivery_otp):
            self.otp_verified = True
            self.otp_verified_at = datetime.utcnow()
            self.status = 'delivered'
            self.delivered_at = datetime.utcnow()
            return True, "Delivery confirmed!"
        else:
            self.otp_attempts += 1
            remaining = 3 - self.otp_attempts
            return False, f"Wrong OTP. {remaining} attempts left."
    
    def confirm_pickup(self):
        """Farmer confirms goods handed to transporter"""
        self.status = 'pickup_confirmed'
        self.pickup_confirmed_at = datetime.utcnow()
    
    def start_transit(self):
        """Transporter starts journey"""
        self.status = 'in_transit'
        self.in_transit_at = datetime.utcnow()
    
    def update_location(self, location):
        """Update transporter location"""
        self.last_location = location
        self.last_location_time = datetime.utcnow()
    
    def complete_order(self):
        """Mark order as completed and release escrow"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.escrow_released = True
    
    def get_status_display(self):
        """Human-readable status for SMS"""
        statuses = {
            'pending': 'Awaiting acceptance',
            'accepted': 'Accepted, awaiting pickup',
            'pickup_confirmed': 'Picked up, awaiting transport',
            'in_transit': f'In transit - {self.last_location or "Location unknown"}',
            'delivered': 'Delivered, awaiting confirmation',
            'completed': 'Completed - Payment released',
            'cancelled': 'Cancelled',
            'disputed': 'Under dispute'
        }
        return statuses.get(self.status, self.status)
    
    def get_status_badge_class(self):
        """Bootstrap badge class for status"""
        classes = {
            'pending': 'bg-warning',
            'accepted': 'bg-info',
            'pickup_confirmed': 'bg-primary',
            'in_transit': 'bg-primary',
            'delivered': 'bg-success',
            'completed': 'bg-success',
            'cancelled': 'bg-danger',
            'disputed': 'bg-danger'
        }
        return classes.get(self.status, 'bg-secondary')
    
    def __repr__(self):
        return f'<Order {self.order_code}: {self.status}>'


class CaptainBond(db.Model):
    """SabiBuy Captain bond deposits (N10,000 refundable)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False, default=10000.0)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    
    status = db.Column(db.String(20), default='active')  # 'active', 'refunded', 'forfeited'
    collected_date = db.Column(db.DateTime, default=datetime.utcnow)
    refunded_date = db.Column(db.DateTime)
    
    forfeit_reason = db.Column(db.Text)
    admin_notes = db.Column(db.Text)
    
    campaigns_run = db.Column(db.Integer, default=0)
    successful_campaigns = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref='captain_bonds')
    
    def __repr__(self):
        return f'<CaptainBond {self.user_id}: N{self.amount} ({self.status})>'


class FarmerVouch(db.Model):
    """Community vouching system - established farmers vouch for new farmers"""
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vouched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    voucher = db.relationship('User', foreign_keys=[voucher_id], backref='vouches_given')
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref='vouches_received')
    
    __table_args__ = (
        db.UniqueConstraint('voucher_id', 'farmer_id', name='unique_vouch'),
    )
    
    def __repr__(self):
        return f'<FarmerVouch {self.voucher_id} -> {self.farmer_id}>'
