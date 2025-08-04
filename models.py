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
    
    # Relationship with produce
    produce_listings = db.relationship('Produce', backref='farmer', lazy=True, cascade='all, delete-orphan')
    
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
    
    # Foreign key to User
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Produce {self.name}>'
    
    def formatted_price(self):
        """Return formatted price string"""
        return f"{self.price_unit} {self.price:,.2f}"


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
