"""
Africa's Talking SMS Service for AgroLink
Enables farmers to access platform features via SMS commands
"""

import re
import logging
import africastalking
from datetime import datetime
from flask import current_app
from models import db, User, Produce, SMSInteraction
from sqlalchemy import func

class SMSService:
    def __init__(self, username, api_key):
        """Initialize Africa's Talking SMS service"""
        self.username = username
        self.api_key = api_key
        
        # Check if credentials are properly configured
        if not username or not api_key or len(api_key) < 20:
            current_app.logger.warning("Africa's Talking credentials may be invalid")
            
        africastalking.initialize(username, api_key)
        self.sms = africastalking.SMS
        
    def send_sms(self, phone_number, message):
        """Send SMS to phone number"""
        try:
            # Format phone number for Africa's Talking (ensure it starts with +)
            if not phone_number.startswith('+'):
                phone_number = f'+{phone_number}'
                
            response = self.sms.send(message, [phone_number])
            
            # Log the SMS interaction
            self._log_sms_interaction(
                phone_number=phone_number,
                message_type='outgoing',
                content=message,
                status='sent'
            )
            
            return response
        except Exception as e:
            current_app.logger.error(f"SMS sending error: {e}")
            self._log_sms_interaction(
                phone_number=phone_number,
                message_type='outgoing',
                content=message,
                status='failed'
            )
            return None
    
    def process_incoming_sms(self, phone_number, message):
        """Process incoming SMS commands"""
        try:
            # Clean and normalize the message
            message = message.strip().upper()
            phone_number = self._normalize_phone_number(phone_number)
            
            # Log incoming SMS
            self._log_sms_interaction(
                phone_number=phone_number,
                message_type='incoming',
                content=message,
                status='received'
            )
            
            # Parse command
            command_parts = message.split()
            if not command_parts:
                return self._send_help_message(phone_number)
            
            command = command_parts[0]
            
            # Route to appropriate handler
            if command == 'JOIN':
                return self._handle_registration(phone_number, command_parts)
            elif command == 'LIST':
                return self._handle_produce_listing(phone_number, command_parts)
            elif command == 'PRICE':
                return self._handle_price_check(phone_number, command_parts)
            elif command == 'HELP':
                return self._send_help_message(phone_number)
            elif command == 'STOP':
                return self._handle_opt_out(phone_number)
            elif command.startswith('ACCEPT'):
                return self._handle_match_acceptance(phone_number, command_parts)
            elif command.startswith('DECLINE'):
                return self._handle_match_decline(phone_number, command_parts)
            else:
                return self._send_invalid_command_message(phone_number)
                
        except Exception as e:
            current_app.logger.error(f"SMS processing error: {e}")
            self._send_error_message(phone_number)
    
    def _handle_registration(self, phone_number, command_parts):
        """Handle farmer registration via SMS"""
        # Check if user already exists
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            return self.send_sms(phone_number, 
                f"Welcome back {existing_user.name}! You're already registered. Send HELP for commands.")
        
        if len(command_parts) == 1:
            # Initial JOIN command - ask for details
            message = ("Welcome to AgroLink! 🌾\n"
                      "Reply with: JOIN [your name] [location] [main crop]\n"
                      "Example: JOIN John Lagos Tomatoes")
            return self.send_sms(phone_number, message)
        
        if len(command_parts) < 4:
            message = ("Please provide your details:\n"
                      "JOIN [your name] [location] [main crop]\n"
                      "Example: JOIN John Lagos Tomatoes")
            return self.send_sms(phone_number, message)
        
        # Extract registration details
        name = command_parts[1]
        location = command_parts[2]
        main_crop = ' '.join(command_parts[3:])
        
        try:
            # Create new user account
            user = User(
                name=name,
                phone_number=phone_number,
                email=f"{phone_number.replace('+', '')}@sms.agrolink.com",  # Temporary email
                role='farmer',
                sms_enabled=True,
                sms_registration_date=datetime.utcnow()
            )
            
            # Set a temporary password (they'll use SMS only)
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash('sms_user_temp')
            
            db.session.add(user)
            db.session.commit()
            
            welcome_message = (f"Welcome {name}!\n"
                             f"You're registered as a farmer.\n"
                             f"Commands: LIST, PRICE, HELP\n"
                             f"Example: LIST TOMATOES 5T 150000")
            
            return self.send_sms(phone_number, welcome_message)
            
        except Exception as e:
            current_app.logger.error(f"Registration error: {e}")
            return self.send_sms(phone_number, 
                "Registration failed. Please try again or contact support.")
    
    def _handle_produce_listing(self, phone_number, command_parts):
        """Handle produce listing via SMS"""
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number, 
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 4:
            message = ("Format: LIST [crop] [quantity] [price]\n"
                      "Example: LIST TOMATOES 5T 150000\n"
                      "Quantity: use T for tons, KG for kilograms")
            return self.send_sms(phone_number, message)
        
        try:
            crop_name = command_parts[1]
            quantity_str = command_parts[2]
            price_str = command_parts[3]
            
            # Parse quantity (handle T for tons, KG for kilograms)
            quantity_match = re.match(r'(\d+\.?\d*)(T|KG|TONS?|KILOS?)', quantity_str.upper())
            if not quantity_match:
                return self.send_sms(phone_number, 
                    "Invalid quantity format. Use: 5T (tons) or 100KG (kilograms)")
            
            quantity_value = float(quantity_match.group(1))
            unit = quantity_match.group(2)
            
            # Convert to standard unit (kg)
            if unit in ['T', 'TON', 'TONS']:
                quantity_kg = quantity_value * 1000
                display_unit = 'tons'
            else:
                quantity_kg = quantity_value
                display_unit = 'kg'
            
            # Parse price (remove currency symbols)
            price = float(re.sub(r'[^\d.]', '', price_str))
            
            # Create produce listing
            produce = Produce(
                farmer_id=user.id,
                name=crop_name.title(),
                quantity_kg=quantity_kg,
                price_per_kg=price / quantity_kg,  # Calculate price per kg
                location=user.location,
                description=f"Listed via SMS by {user.name}",
                contact_method='sms',
                phone_number=phone_number
            )
            
            db.session.add(produce)
            db.session.commit()
            
            success_message = (f"✅ Listed: {quantity_value}{unit.lower()} {crop_name.title()}\n"
                             f"Price: ₦{price:,.0f}\n"
                             f"Per kg: ₦{price/quantity_kg:.0f}\n"
                             f"Buyers can now see your produce!")
            
            return self.send_sms(phone_number, success_message)
            
        except ValueError:
            return self.send_sms(phone_number, 
                "Invalid price format. Use numbers only (e.g., 150000)")
        except Exception as e:
            current_app.logger.error(f"Listing error: {e}")
            return self.send_sms(phone_number, 
                "Listing failed. Please check format and try again.")
    
    def _handle_price_check(self, phone_number, command_parts):
        """Handle market price check via SMS"""
        if len(command_parts) < 2:
            return self.send_sms(phone_number, 
                "Format: PRICE [crop]\nExample: PRICE TOMATOES")
        
        crop_name = ' '.join(command_parts[1:]).title()
        
        try:
            # Get recent prices for this crop (last 30 days)
            recent_produce = Produce.query.filter(
                Produce.name.ilike(f'%{crop_name}%'),
                Produce.date_listed >= datetime.utcnow().replace(day=1)  # This month
            ).all()
            
            if not recent_produce:
                return self.send_sms(phone_number, 
                    f"No recent prices for {crop_name}. Try: TOMATOES, YAM, CASSAVA, RICE")
            
            # Calculate price statistics
            prices = [p.price_per_kg for p in recent_produce if p.price_per_kg]
            if not prices:
                return self.send_sms(phone_number, 
                    f"No price data available for {crop_name}")
            
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            price_message = (f"📊 {crop_name} Market Prices:\n"
                           f"Average: ₦{avg_price:.0f}/kg\n"
                           f"Range: ₦{min_price:.0f} - ₦{max_price:.0f}\n"
                           f"Based on {len(prices)} recent listings")
            
            return self.send_sms(phone_number, price_message)
            
        except Exception as e:
            current_app.logger.error(f"Price check error: {e}")
            return self.send_sms(phone_number, 
                "Price check failed. Please try again.")
    
    def _handle_opt_out(self, phone_number):
        """Handle opt-out request"""
        user = User.query.filter_by(phone_number=phone_number).first()
        if user:
            user.sms_enabled = False
            db.session.commit()
        
        return self.send_sms(phone_number, 
            "You've been unsubscribed from AgroLink SMS. Send JOIN to re-register.")
    
    def _send_help_message(self, phone_number):
        """Send help message with available commands"""
        help_message = ("AgroLink SMS Commands:\n"
                       "JOIN [name] [location] [crop] - Register\n"
                       "LIST [crop] [quantity] [price] - List produce\n"
                       "PRICE [crop] - Check market prices\n"
                       "HELP - Show this message\n"
                       "STOP - Unsubscribe")
        
        return self.send_sms(phone_number, help_message)
    
    def _send_invalid_command_message(self, phone_number):
        """Send message for invalid commands"""
        return self.send_sms(phone_number, 
            "Invalid command. Send HELP for available commands.")
    
    def _send_error_message(self, phone_number):
        """Send generic error message"""
        return self.send_sms(phone_number, 
            "Sorry, there was an error. Please try again or send HELP.")
    
    def _normalize_phone_number(self, phone_number):
        """Normalize phone number format"""
        # Remove spaces and special characters
        phone_number = re.sub(r'[^\d+]', '', phone_number)
        
        # Ensure it starts with +
        if not phone_number.startswith('+'):
            # Assume Nigerian number if no country code
            if phone_number.startswith('0'):
                phone_number = '+234' + phone_number[1:]
            else:
                phone_number = '+' + phone_number
        
        return phone_number
    
    def _log_sms_interaction(self, phone_number, message_type, content, status):
        """Log SMS interaction to database"""
        try:
            interaction = SMSInteraction(
                phone_number=phone_number,
                message_type=message_type,
                content=content[:500],  # Limit content length
                status=status,
                timestamp=datetime.utcnow()
            )
            db.session.add(interaction)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"SMS logging error: {e}")
    
    def send_automated_alert(self, phone_number, alert_type, message):
        """Send automated alerts (logistics, weather, payments)"""
        try:
            user = User.query.filter_by(phone_number=phone_number).first()
            if user and user.sms_enabled:
                alert_message = f"🚨 AgroLink Alert ({alert_type.title()}):\n{message}"
                return self.send_sms(phone_number, alert_message)
        except Exception as e:
            current_app.logger.error(f"Alert sending error: {e}")
    
    def get_sms_metrics(self):
        """Get SMS usage metrics for admin dashboard"""
        try:
            total_sms = SMSInteraction.query.count()
            unique_users = SMSInteraction.query.with_entities(
                SMSInteraction.phone_number).distinct().count()
            
            # SMS by command type (approximation)
            join_messages = SMSInteraction.query.filter(
                SMSInteraction.content.like('JOIN%')).count()
            list_messages = SMSInteraction.query.filter(
                SMSInteraction.content.like('LIST%')).count()
            price_messages = SMSInteraction.query.filter(
                SMSInteraction.content.like('PRICE%')).count()
            
            # Listings created via SMS
            sms_listings = Produce.query.filter_by(contact_method='sms').count()
            total_listings = Produce.query.count()
            sms_percentage = (sms_listings / total_listings * 100) if total_listings > 0 else 0
            
            return {
                'total_sms_interactions': total_sms,
                'unique_sms_users': unique_users,
                'join_commands': join_messages,
                'list_commands': list_messages,
                'price_commands': price_messages,
                'sms_listings': sms_listings,
                'sms_listing_percentage': round(sms_percentage, 1)
            }
        except Exception as e:
            current_app.logger.error(f"Metrics error: {e}")
            return {}


# SMS Templates for future multilingual support
SMS_TEMPLATES = {
    'en': {
        'welcome': "Welcome to AgroLink! 🌾 Reply with: JOIN [name] [location] [crop]",
        'registration_success': "Welcome {name}! You're registered for {crop} in {location}.",
        'invalid_format': "Invalid format. Send HELP for commands.",
        'help': "Commands: JOIN, LIST, PRICE, HELP, STOP",
    },
    # Future: Yoruba, Hausa, Pidgin templates
}