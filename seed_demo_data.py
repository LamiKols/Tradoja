"""
Demo data seeding script for Tradoja
Creates sample users (farmer, buyer, admin) and produce listings for demonstration
"""

import os
from datetime import datetime, timedelta
from app import app, db
from models import User, Produce
from werkzeug.security import generate_password_hash


def seed_demo_data():
    """Seed database with demo users and produce"""
    with app.app_context():
        print("Seeding demo data...")
        
        # Check if demo data already exists
        existing_admin = User.query.filter_by(email='admin@tradoja.com').first()
        existing_farmer = User.query.filter_by(email='farmer@demo.com').first()
        existing_buyer = User.query.filter_by(email='buyer@demo.com').first()
        
        # Create Admin if not exists
        if not existing_admin:
            admin = User(
                name="Tradoja Admin",
                email="admin@tradoja.com",
                role="admin",
                phone_number="+2348012345670",
                location="Lagos, Nigeria",
                registration_status="verified"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            print("Created admin: admin@tradoja.com / admin123")
        else:
            admin = existing_admin
            print("Admin already exists")
        
        # Create Demo Farmer if not exists
        if not existing_farmer:
            farmer = User(
                name="Adebayo Okonkwo",
                email="farmer@demo.com",
                role="farmer",
                phone_number="+2348012345671",
                location="Ibadan, Oyo State",
                registration_status="verified",
                preferred_language="yo",
                average_rating=4.5,
                total_ratings=12
            )
            farmer.set_password("farmer123")
            db.session.add(farmer)
            db.session.flush()
            print("Created farmer: farmer@demo.com / farmer123")
            
            # Create sample produce listings for the farmer
            produce_items = [
                {
                    "name": "Tomatoes",
                    "quantity": "200 baskets",
                    "price": 15000,
                    "description": "Fresh Roma tomatoes from Ibadan farm. Harvested yesterday, ready for immediate pickup.",
                    "listing_location": "Ibadan, Oyo State"
                },
                {
                    "name": "Cassava",
                    "quantity": "500 kg",
                    "price": 8500,
                    "description": "High-quality cassava tubers suitable for garri processing. Organic farming methods.",
                    "listing_location": "Ibadan, Oyo State",
                    "gi_label": "Oyo Cassava"
                },
                {
                    "name": "Maize",
                    "quantity": "100 bags",
                    "price": 25000,
                    "description": "Dried yellow maize, perfect for poultry feed or corn meal production.",
                    "listing_location": "Ibadan, Oyo State"
                },
                {
                    "name": "Yams",
                    "quantity": "300 tubers",
                    "price": 2500,
                    "description": "Premium white yams from Oyo State. Each tuber weighs 3-5kg average.",
                    "listing_location": "Ibadan, Oyo State"
                }
            ]
            
            for item in produce_items:
                produce = Produce(
                    name=item["name"],
                    quantity=item["quantity"],
                    price=item["price"],
                    price_unit="NGN",
                    description=item["description"],
                    farmer_id=farmer.id,
                    listing_location=item.get("listing_location", "Lagos, Nigeria"),
                    gi_label=item.get("gi_label"),
                    source_channel="web"
                )
                db.session.add(produce)
            print(f"Created {len(produce_items)} produce listings for demo farmer")
        else:
            farmer = existing_farmer
            print("Farmer already exists")
        
        # Create Demo Buyer if not exists
        if not existing_buyer:
            buyer = User(
                name="Chidi Nwosu",
                email="buyer@demo.com",
                role="buyer",
                buyer_type="bulk_trader",
                phone_number="+2348012345672",
                location="Lagos Island, Lagos",
                registration_status="verified",
                preferred_language="en",
                trader_verified=True,
                trader_verification_status="verified",
                trader_value_services="transport,aggregation,storage",
                average_rating=4.2,
                total_ratings=8
            )
            buyer.set_password("buyer123")
            db.session.add(buyer)
            print("Created buyer: buyer@demo.com / buyer123")
        else:
            print("Buyer already exists")
        
        # Create Demo Agent if not exists
        existing_agent = User.query.filter_by(email='agent@demo.com').first()
        if not existing_agent:
            agent = User(
                name="Fatima Ibrahim",
                email="agent@demo.com",
                role="agent",
                phone_number="+2348012345673",
                location="Kano, Nigeria",
                registration_status="verified",
                preferred_language="ha"
            )
            agent.set_password("agent123")
            db.session.add(agent)
            print("Created agent: agent@demo.com / agent123")
        else:
            print("Agent already exists")
        
        # Create additional farmers for variety
        additional_farmers = [
            {
                "name": "Amina Yusuf",
                "email": "amina@demo.com",
                "location": "Kano, Nigeria",
                "language": "ha",
                "produce": [
                    {"name": "Groundnuts", "quantity": "50 bags", "price": 45000, "description": "Premium groundnuts from Kano. Ideal for oil extraction or confectionery."},
                    {"name": "Millet", "quantity": "80 bags", "price": 18000, "description": "Fresh millet grain for fura, tuwo, or animal feed."}
                ]
            },
            {
                "name": "Emeka Obi",
                "email": "emeka@demo.com",
                "location": "Enugu, Nigeria",
                "language": "ig",
                "produce": [
                    {"name": "Palm Oil", "quantity": "200 litres", "price": 1200, "description": "Organic palm oil from Enugu. Rich red color, no additives."},
                    {"name": "Oranges", "quantity": "500 pieces", "price": 150, "description": "Sweet Benue oranges. Perfect for juice or fresh eating."}
                ]
            }
        ]
        
        for farmer_data in additional_farmers:
            existing = User.query.filter_by(email=farmer_data["email"]).first()
            if not existing:
                new_farmer = User(
                    name=farmer_data["name"],
                    email=farmer_data["email"],
                    role="farmer",
                    phone_number=f"+234801234567{len(farmer_data['name'])}",
                    location=farmer_data["location"],
                    registration_status="verified",
                    preferred_language=farmer_data["language"]
                )
                new_farmer.set_password("demo123")
                db.session.add(new_farmer)
                db.session.flush()
                
                for item in farmer_data["produce"]:
                    produce = Produce(
                        name=item["name"],
                        quantity=item["quantity"],
                        price=item["price"],
                        price_unit="NGN",
                        description=item["description"],
                        farmer_id=new_farmer.id,
                        listing_location=farmer_data["location"],
                        source_channel="web"
                    )
                    db.session.add(produce)
                print(f"Created farmer: {farmer_data['email']} / demo123 with {len(farmer_data['produce'])} listings")
        
        # Commit all changes
        try:
            db.session.commit()
            print("\n=== Demo Data Seeded Successfully ===")
            print("\nDemo Accounts:")
            print("  Admin:  admin@tradoja.com / admin123")
            print("  Farmer: farmer@demo.com / farmer123")
            print("  Buyer:  buyer@demo.com / buyer123")
            print("  Agent:  agent@demo.com / agent123")
            print("  Farmer: amina@demo.com / demo123")
            print("  Farmer: emeka@demo.com / demo123")
            print("\nTotal produce listings created for marketplace demo.")
        except Exception as e:
            print(f"Error seeding data: {e}")
            db.session.rollback()


if __name__ == "__main__":
    seed_demo_data()
