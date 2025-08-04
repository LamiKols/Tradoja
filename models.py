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
    role = db.Column(db.String(20), nullable=False)  # 'farmer', 'buyer', 'admin'
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
