"""
Database initialization script for AgroLink Lagos
This script creates the database tables and optionally seeds with sample data
"""

import os
from app import app, db
from models import User, Produce
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database and create tables"""
    with app.app_context():
        # Drop all tables and recreate (for development)
        db.drop_all()
        db.create_all()
        
        print("Database tables created successfully!")
        
        # Create admin user
        admin = User(
            name="AgroLink Admin",
            email="admin@agrolink.com",
            role="admin"
        )
        admin.set_password("admin123")
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
            print("Admin credentials: admin@agrolink.com / admin123")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()

if __name__ == "__main__":
    init_database()
