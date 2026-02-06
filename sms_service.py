"""
Africa's Talking SMS Service for Tradoja
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
        self._simulation_mode = False
        
        # Check if credentials are properly configured
        if not username or not api_key or len(api_key) < 20:
            current_app.logger.warning("Africa's Talking credentials may be invalid")
            
        africastalking.initialize(username, api_key)
        self.sms = africastalking.SMS
        
    def send_sms(self, phone_number, message, simulate=False):
        """Send SMS to phone number (or simulate for demo)"""
        try:
            # Format phone number for Africa's Talking (ensure it starts with +)
            if not phone_number.startswith('+'):
                phone_number = f'+{phone_number}'
            
            # In simulation mode (explicit or via _simulation_mode flag), just return the message
            if simulate or getattr(self, '_simulation_mode', False):
                self._log_sms_interaction(
                    phone_number=phone_number,
                    message_type='outgoing',
                    content=message,
                    status='simulated'
                )
                return message
                
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
            return message
    
    def simulate_incoming_sms(self, phone_number, message):
        """Simulate incoming SMS for demo - returns the response text without sending real SMS"""
        self._simulation_mode = True
        try:
            result = self.process_incoming_sms(phone_number, message)
            return result
        finally:
            self._simulation_mode = False
    
    def _apply_device_fingerprint(self, user, phone_number):
        """Apply device fingerprinting to a user during SMS/USSD registration"""
        import hashlib
        import json
        
        metadata = getattr(self, '_current_metadata', {})
        if metadata:
            fingerprint_data = {
                'channel': metadata.get('channel', 'sms'),
                'network_code': metadata.get('network_code', ''),
                'phone_prefix': phone_number[:7] if phone_number else '',
                'registration_time': datetime.utcnow().strftime('%Y-%m-%d')
            }
            fingerprint_hash = hashlib.sha256(
                json.dumps(fingerprint_data, sort_keys=True).encode()
            ).hexdigest()[:32]
            
            user.device_fingerprint = fingerprint_hash
            user.registration_ip = metadata.get('gateway_ip', '')
            user.user_agent_hash = hashlib.sha256(
                metadata.get('user_agent', '').encode()
            ).hexdigest()[:32] if metadata.get('user_agent') else None
            
            if metadata.get('gateway_ip'):
                user.known_ips = json.dumps([metadata.get('gateway_ip')])
    
    def _send_simulated(self, phone_number, message):
        """Return message for simulation without using real API"""
        self._log_sms_interaction(
            phone_number=phone_number,
            message_type='outgoing',
            content=message,
            status='simulated'
        )
        return message
    
    def process_incoming_sms(self, phone_number, message, metadata=None):
        """Process incoming SMS commands with AI natural language fallback"""
        try:
            # Store metadata for handlers to use
            self._current_metadata = metadata or {}
            
            # Store original message before uppercasing for AI parsing
            original_message = message.strip()
            
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
            
            # Route to appropriate handler (with common aliases)
            if command == 'JOIN' or command == 'REG' or command == 'REGISTER':
                if len(command_parts) > 1 and command_parts[1] in ('TRK', 'TRANSPORT'):
                    return self._handle_transport_registration(phone_number, command_parts)
                if len(command_parts) > 1 and command_parts[1] in ('BUYER', 'BUY'):
                    return self._handle_buyer_registration(phone_number, command_parts)
                if len(command_parts) > 1 and command_parts[1] == 'AGENT':
                    return self._handle_agent_registration(phone_number, command_parts)
                return self._handle_registration(phone_number, command_parts)
            elif command == 'LIST' or command == 'SELL':
                return self._handle_produce_listing(phone_number, command_parts)
            elif command == 'PRICE':
                return self._handle_price_check(phone_number, command_parts)
            elif command == 'HELP':
                return self._send_help_message(phone_number)
            elif command == 'STOP':
                return self._handle_opt_out(phone_number)
            elif command.startswith('ACCEPT'):
                # Check if accepting an order (ORD-xxx) or a match
                if len(command_parts) > 1 and command_parts[1].upper().startswith('ORD'):
                    return self._handle_order_acceptance(phone_number, command_parts)
                return self._handle_match_acceptance(phone_number, command_parts)
            elif command.startswith('DECLINE'):
                return self._handle_match_decline(phone_number, command_parts)
            elif command == 'BID':
                return self._handle_transport_bid(phone_number, command_parts)
            elif command == 'JOBS':
                return self._handle_view_jobs(phone_number)
            elif command == 'MYBIDS':
                return self._handle_view_my_bids(phone_number)
            elif command == 'START':
                return self._handle_start_trip(phone_number, command_parts)
            elif command == 'DOC':
                return self._handle_doc_request(phone_number)
            elif command == 'SABIBUY' or command == 'SABI' or command == 'SB':
                return self._handle_sabibuy_command(phone_number, command_parts)
            elif command == 'CAMPAIGNS' or command == 'MYSABIBUY' or command == 'MYSB':
                return self._handle_my_sabibuy(phone_number)
            elif '-SABIBUY-' in command or command.startswith('SB-'):
                return self._handle_sabibuy_join_code(phone_number, command, command_parts)
            elif command == 'MYLIST' or command == 'MYLISTINGS':
                return self._handle_my_listings(phone_number)
            elif command == 'BAL' or command == 'BALANCE':
                return self._handle_balance_check(phone_number)
            elif command == 'SBEARNINGS' or command == 'EARNINGS':
                return self._handle_sabibuy_earnings(phone_number)
            elif command == 'AGENTBAL' or command == 'AGBAL':
                return self._handle_agent_balance(phone_number)
            elif command == 'AGENTADD' or command == 'AGADD':
                return self._handle_agent_add_farmer(phone_number, command_parts)
            elif command == 'TRIPBAL' or command == 'TBAL':
                return self._handle_transport_balance(phone_number)
            elif command == 'COMPLAINT' or command == 'REPORT' or command == 'DISPUTE':
                return self._handle_complaint(phone_number, command_parts)
            elif command == 'TRACK':
                return self._handle_order_tracking(phone_number, command_parts)
            elif command == 'PICKUP':
                return self._handle_pickup_confirmation(phone_number, command_parts)
            elif command == 'LOCATION':
                return self._handle_location_update(phone_number, command_parts)
            elif command == 'DELIVER':
                return self._handle_delivery_confirmation(phone_number, command_parts)
            elif command == 'RATE':
                return self._handle_rating(phone_number, command_parts)
            elif command == 'STATUS':
                return self._handle_status_check(phone_number, command_parts)
            elif command == 'PAY':
                return self._handle_pay_command(phone_number, command_parts)
            elif command == 'WALLET':
                return self._handle_wallet_command(phone_number, command_parts)
            elif command == 'TOPUP' or command == 'ADDMONEY':
                return self._handle_topup_command(phone_number, command_parts)
            elif command == 'BOND':
                return self._handle_bond_command(phone_number, command_parts)
            elif command == 'HISTORY' or command == 'TXN':
                return self._handle_transaction_history(phone_number)
            elif command == 'CONFIRM':
                return self._handle_delivery_confirmation(phone_number, command_parts)
            elif command == 'SUBSCRIBE' or command == 'SUB' or command == 'PREMIUM':
                return self._handle_subscribe_command(phone_number, command_parts)
            elif command == 'SETTLE':
                return self._handle_transport_settlement(phone_number, command_parts)
            elif command == 'CREATE':
                return self._handle_sabibuy_create(phone_number, command_parts)
            elif command == 'CANCEL':
                return self._handle_order_cancel(phone_number, command_parts)
            elif command == 'CLAIM':
                return self._handle_claim_job(phone_number, command_parts)
            elif command == 'VOUCH':
                return self._handle_vouch_farmer(phone_number, command_parts)
            elif command == 'AI':
                return self._handle_ai_command(phone_number, command_parts, original_message)
            elif command == 'ADVICE':
                return self._handle_price_advice(phone_number, command_parts)
            elif command == 'RISK':
                return self._handle_risk_check(phone_number, command_parts)
            elif command == 'TRACE':
                return self._handle_trace_command(phone_number, command_parts)
            elif command == 'QUALITY':
                return self._handle_quality_check(phone_number, command_parts)
            else:
                # Try AI natural language parsing as fallback
                return self._try_ai_parse(phone_number, original_message, command_parts)
                
        except Exception as e:
            current_app.logger.error(f"SMS processing error: {e}")
            return self._send_error_message(phone_number)
    
    def _handle_registration(self, phone_number, command_parts):
        """Handle farmer registration via SMS - creates LITE account"""
        # Check if user already exists
        existing_user = User.query.filter_by(phone_number=phone_number).first()
        if existing_user:
            if len(command_parts) >= 4:
                try:
                    existing_user.name = command_parts[1]
                    existing_user.location = command_parts[2]
                    db.session.commit()
                    return self.send_sms(phone_number,
                        f"Profile updated, {existing_user.name}!\n"
                        f"Location: {command_parts[2]}\n"
                        f"Crop: {' '.join(command_parts[3:])}\n"
                        f"Send HELP for commands.")
                except Exception as e:
                    current_app.logger.error(f"Profile update error: {e}")
                    db.session.rollback()
            
            status = "LITE" if existing_user.is_lite_account() else "Verified"
            produce_count = 0
            try:
                from models import Produce
                produce_count = Produce.query.filter_by(farmer_id=existing_user.id).count()
            except Exception:
                pass
            
            msg = (f"Hi {existing_user.name}! You're already registered ({status}).\n"
                   f"Location: {existing_user.location or 'Not set'}\n")
            if produce_count > 0:
                msg += f"Listings: {produce_count}\n"
            msg += f"\nCommands: SELL, PRICE, HELP\n"
            msg += f"Update profile: JOIN [name] [location] [crop]"
            return self.send_sms(phone_number, msg)
        
        if len(command_parts) == 1:
            # Initial JOIN command - ask for details
            message = ("Welcome to Tradoja!\n"
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
            # Create LITE user account (SMS/USSD registration)
            user = User(
                name=name,
                phone_number=phone_number,
                email=f"{phone_number.replace('+', '')}@sms.tradoja.com",  # Temporary email
                role='farmer',
                sms_enabled=True,
                sms_registration_date=datetime.utcnow(),
                source_channel='sms',
                location=location,
                registration_status='lite',  # LITE account - not yet verified
                lite_registration_date=datetime.utcnow()
            )
            
            # Capture device fingerprinting for anti-collusion detection
            self._apply_device_fingerprint(user, phone_number)
            
            # Set a temporary password (they'll use SMS only initially)
            from werkzeug.security import generate_password_hash
            import secrets
            temp_password = secrets.token_hex(8)
            user.password_hash = generate_password_hash(temp_password)
            
            db.session.add(user)
            db.session.commit()
            
            # Welcome message with verification prompt
            welcome_message = (f"Welcome {name}!\n"
                             f"You're registered (LITE).\n"
                             f"Commands: LIST, PRICE, HELP\n"
                             f"Get VERIFIED at tradoja.com for more trust!")
            
            return self.send_sms(phone_number, welcome_message)
            
        except Exception as e:
            current_app.logger.error(f"Registration error: {e}")
            return self.send_sms(phone_number, 
                "Registration failed. Please try again or contact support.")
    
    def _handle_produce_listing(self, phone_number, command_parts):
        """Handle produce listing via SMS
        
        Enhanced format: LIST [crop] [quantity] [price] [location (optional)]
        Examples:
        - LIST RICE 50BAGS 45000
        - LIST TOMATOES 5T 150000 ONITSHA
        - LIST YAM 100TUBERS 2500 LAGOS
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number, 
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 4:
            message = ("Format: LIST [crop] [quantity] [price] [location]\n"
                      "Example: LIST RICE 50BAGS 45000 ONITSHA\n"
                      "Units: BAGS, KG, T(tons), TUBERS, BUNCHES")
            return self.send_sms(phone_number, message)
        
        try:
            crop_name = command_parts[1]
            quantity_str = command_parts[2]
            price_str = command_parts[3]
            location = ' '.join(command_parts[4:]) if len(command_parts) > 4 else (user.location or 'Nigeria')
            
            # Enhanced quantity parsing (BAGS, KG, T, TUBERS, BUNCHES)
            quantity_match = re.match(
                r'(\d+\.?\d*)(BAGS?|KG|KILOS?|T|TONS?|TUBERS?|BUNCHES?)', 
                quantity_str.upper()
            )
            if not quantity_match:
                return self.send_sms(phone_number, 
                    "Invalid quantity. Use: 50BAGS, 5T, 100KG, 100TUBERS, 20BUNCHES")
            
            quantity_value = float(quantity_match.group(1))
            unit = quantity_match.group(2)
            
            # Normalize unit for display
            unit_display_map = {
                'BAG': 'bags', 'BAGS': 'bags',
                'KG': 'kg', 'KILO': 'kg', 'KILOS': 'kg',
                'T': 'tons', 'TON': 'tons', 'TONS': 'tons',
                'TUBER': 'tubers', 'TUBERS': 'tubers',
                'BUNCH': 'bunches', 'BUNCHES': 'bunches'
            }
            display_unit = unit_display_map.get(unit, unit.lower())
            quantity_display = f"{int(quantity_value) if quantity_value.is_integer() else quantity_value}{display_unit}"
            
            # Parse price (remove currency symbols and commas)
            price = float(re.sub(r'[^\d.]', '', price_str))
            
            # Create produce listing with enhanced fields
            produce = Produce(
                farmer_id=user.id,
                name=crop_name.title(),
                quantity=quantity_display,
                price=price,
                price_unit='NGN',
                listing_location=location.title(),
                description=f"Listed via SMS by {user.name}",
                contact_method='sms',
                source_channel='sms',
                is_available=True
            )
            
            db.session.add(produce)
            db.session.commit()
            
            success_message = (f"Listed: {quantity_display} {crop_name.title()}\n"
                             f"Price: N{price:,.0f}\n"
                             f"Location: {location.title()}\n"
                             f"Buyers can now find you!")
            
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
    
    def _handle_match_acceptance(self, phone_number, command_parts):
        """Handle match acceptance via SMS"""
        from models import MatchRecommendation
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number, "Please register first. Send: JOIN [name] [location] [crop]")
        
        # Get the most recent pending recommendation for this user
        recommendation = MatchRecommendation.query.filter(
            ((MatchRecommendation.farmer_id == user.id) | (MatchRecommendation.buyer_id == user.id)),
            MatchRecommendation.status == 'pending'
        ).order_by(MatchRecommendation.recommended_at.desc()).first()
        
        if not recommendation:
            return self.send_sms(phone_number, "No pending matches to accept. Check back later for new matches.")
        
        try:
            recommendation.status = 'accepted'
            recommendation.response_at = datetime.utcnow()
            recommendation.response_method = 'sms'
            db.session.commit()
            
            # Get the other party's details
            if user.id == recommendation.farmer_id:
                other_user = User.query.get(recommendation.buyer_id)
                role = "Buyer"
            else:
                other_user = User.query.get(recommendation.farmer_id)
                role = "Farmer"
            
            if other_user:
                contact = other_user.phone_number or other_user.email
                msg = f"Match accepted! {role}: {other_user.name}\nContact: {contact}"
            else:
                msg = "Match accepted! You'll receive contact details shortly."
            
            return self.send_sms(phone_number, msg)
            
        except Exception as e:
            current_app.logger.error(f"Match acceptance error: {e}")
            return self.send_sms(phone_number, "Error accepting match. Please try again.")
    
    def _handle_order_acceptance(self, phone_number, command_parts):
        """Handle farmer accepting an order
        
        Format: ACCEPT [order-code]
        Example: ACCEPT ORD-7842
        
        This generates OTP and sends to buyer for delivery verification.
        """
        from models import Order
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "Format: ACCEPT [order-code]\nExample: ACCEPT ORD-7842")
        
        order_code = command_parts[1].upper()
        
        try:
            order = Order.query.filter_by(order_code=order_code).first()
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            # Verify user is the farmer
            if order.farmer_id != user.id:
                return self.send_sms(phone_number,
                    "You are not the seller for this order.")
            
            # Check order status
            if order.status != 'pending':
                return self.send_sms(phone_number,
                    f"Order already {order.status}. Cannot accept.")
            
            # Accept order
            order.status = 'accepted'
            order.accepted_at = datetime.utcnow()
            
            # Generate OTP for buyer
            otp = order.generate_delivery_otp()
            db.session.commit()
            
            # Create traceability chain for this order
            try:
                from services.traceability_service import traceability_service
                trace_result = traceability_service.record_order_events(
                    order_id=order.id,
                    event_type='packaging',
                    user_id=user.id,
                    role='farmer',
                    location=user.location if hasattr(user, 'location') else order.pickup_location,
                    source_channel='sms'
                )
            except Exception as te:
                current_app.logger.error(f"Trace creation on accept: {te}")
            
            # Send OTP to buyer
            if order.buyer.phone_number:
                self.send_sms(order.buyer.phone_number,
                    f"Order {order_code} accepted!\n"
                    f"Amount: N{order.total_amount:,.0f} (held in escrow)\n"
                    f"Your delivery code is: {otp}\n"
                    f"Give this code to transporter on delivery.")
            
            # Notify transporter if assigned
            if order.transporter and order.transporter.phone_number:
                self.send_sms(order.transporter.phone_number,
                    f"Job assigned: {order_code}\n"
                    f"Pickup: {order.pickup_location}\n"
                    f"Deliver to: {order.destination}\n"
                    f"Collect OTP from buyer at delivery.")
            
            return self.send_sms(phone_number,
                f"Order {order_code} accepted!\n"
                f"Amount: N{order.total_amount:,.0f} held in escrow.\n"
                f"Buyer notified with delivery code.\n"
                f"When picked up, send: PICKUP {order_code}")
            
        except Exception as e:
            current_app.logger.error(f"Order acceptance error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error accepting order. Please try again.")
    
    def _handle_match_decline(self, phone_number, command_parts):
        """Handle match decline via SMS"""
        from models import MatchRecommendation
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number, "Please register first. Send: JOIN [name] [location] [crop]")
        
        recommendation = MatchRecommendation.query.filter(
            ((MatchRecommendation.farmer_id == user.id) | (MatchRecommendation.buyer_id == user.id)),
            MatchRecommendation.status == 'pending'
        ).order_by(MatchRecommendation.recommended_at.desc()).first()
        
        if not recommendation:
            return self.send_sms(phone_number, "No pending matches to decline.")
        
        try:
            recommendation.status = 'declined'
            recommendation.response_at = datetime.utcnow()
            recommendation.response_method = 'sms'
            db.session.commit()
            
            return self.send_sms(phone_number, "Match declined. We'll keep looking for better matches!")
            
        except Exception as e:
            current_app.logger.error(f"Match decline error: {e}")
            return self.send_sms(phone_number, "Error declining match. Please try again.")
    
    def _handle_opt_out(self, phone_number):
        """Handle opt-out request"""
        user = User.query.filter_by(phone_number=phone_number).first()
        if user:
            user.sms_enabled = False
            db.session.commit()
        
        return self.send_sms(phone_number, 
            "You've been unsubscribed from Tradoja SMS. Send JOIN to re-register.")
    
    def _handle_transport_bid(self, phone_number, command_parts):
        """Handle transport bid via SMS
        
        Format: BID [job_id] [amount]
        Example: BID 123 50000
        """
        from models import TransportProfile, LogisticsRequest, LogisticsBid
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        # Check if user is a transporter
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not registered as a transporter. Visit tradoja.com/transport to register.")
        
        if len(command_parts) < 3:
            return self.send_sms(phone_number,
                "Format: BID [job_id] [amount]\nExample: BID 123 50000")
        
        try:
            job_id = int(command_parts[1])
            bid_amount = float(re.sub(r'[^\d.]', '', command_parts[2]))
            
            if bid_amount < 1000:
                return self.send_sms(phone_number, "Minimum bid is ₦1,000")
            
            # Get the job
            job = LogisticsRequest.query.get(job_id)
            if not job:
                return self.send_sms(phone_number, f"Job #{job_id} not found.")
            
            if job.status not in ['pending', 'bidding']:
                return self.send_sms(phone_number, f"Job #{job_id} is no longer accepting bids.")
            
            # Check for existing bid
            existing = LogisticsBid.query.filter_by(
                logistics_request_id=job_id,
                transporter_id=profile.id
            ).first()
            
            if existing:
                existing.bid_amount = bid_amount
                existing.source_channel = 'sms'
            else:
                bid = LogisticsBid(
                    logistics_request_id=job_id,
                    transporter_id=profile.id,
                    bid_amount=bid_amount,
                    eta_hours=24,
                    source_channel='sms'
                )
                db.session.add(bid)
            
            # Update job status
            if job.status == 'pending':
                job.status = 'bidding'
            
            db.session.commit()
            
            route = f"{job.pickup_state or 'N/A'} -> {job.destination_state or 'N/A'}"
            return self.send_sms(phone_number,
                f"Bid of ₦{bid_amount:,.0f} placed on Job #{job_id}!\n{route}\nYou'll be notified if accepted.")
            
        except ValueError:
            return self.send_sms(phone_number, "Invalid bid. Use numbers: BID 123 50000")
        except Exception as e:
            current_app.logger.error(f"Transport bid error: {e}")
            return self.send_sms(phone_number, "Error placing bid. Please try again.")
    
    def _handle_view_jobs(self, phone_number):
        """View available transport jobs via SMS"""
        from models import TransportProfile, LogisticsRequest
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not registered as a transporter. Visit tradoja.com/transport to register.")
        
        # Get available jobs
        jobs = LogisticsRequest.query.filter(
            LogisticsRequest.status.in_(['pending', 'bidding'])
        ).order_by(LogisticsRequest.timestamp.desc()).limit(5).all()
        
        if not jobs:
            return self.send_sms(phone_number, "No jobs available now. Check back later!")
        
        message = "AVAILABLE JOBS:\n"
        for job in jobs:
            cc = "[CC]" if job.requires_cold_chain else ""
            route = f"{job.pickup_state or 'N/A'}->{job.destination_state or 'N/A'}"
            message += f"#{job.id}: {route} {job.quantity_tons or 'N/A'}T {cc}\n"
        
        message += "\nTo bid: BID [job_id] [amount]"
        
        return self.send_sms(phone_number, message)
    
    def _handle_view_my_bids(self, phone_number):
        """View user's transport bids via SMS"""
        from models import TransportProfile, LogisticsBid
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not registered as a transporter.")
        
        bids = LogisticsBid.query.filter_by(
            transporter_id=profile.id
        ).order_by(LogisticsBid.created_at.desc()).limit(5).all()
        
        if not bids:
            return self.send_sms(phone_number, "No bids yet. Send JOBS to see available transport jobs.")
        
        message = "YOUR BIDS:\n"
        for bid in bids:
            status = bid.status.upper()
            message += f"#{bid.logistics_request_id}: ₦{bid.bid_amount:,.0f} [{status}]\n"
        
        return self.send_sms(phone_number, message)
    
    def _handle_start_trip(self, phone_number, command_parts):
        """Start a trip via SMS
        
        Format: START [job_id]
        """
        from models import TransportProfile, LogisticsRequest, LogisticsBid
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Please register first. Send: JOIN [name] [location] [crop]")
        
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not registered as a transporter.")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number, "Format: START [job_id]\nExample: START 123")
        
        try:
            job_id = int(command_parts[1])
            job = LogisticsRequest.query.get(job_id)
            
            if not job:
                return self.send_sms(phone_number, f"Job #{job_id} not found.")
            
            # Verify this transporter won the bid
            winning_bid = LogisticsBid.query.filter_by(
                logistics_request_id=job_id,
                transporter_id=profile.id,
                status='accepted'
            ).first()
            
            if not winning_bid:
                return self.send_sms(phone_number, f"You don't have an accepted bid for Job #{job_id}.")
            
            if job.status != 'assigned':
                return self.send_sms(phone_number, f"Job #{job_id} is not ready to start or already in transit.")
            
            job.status = 'in_transit'
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"Trip #{job_id} started!\nSafe travels. Deliver on time for best rating.")
            
        except ValueError:
            return self.send_sms(phone_number, "Invalid job ID. Use: START 123")
        except Exception as e:
            current_app.logger.error(f"Start trip error: {e}")
            return self.send_sms(phone_number, "Error starting trip. Please try again.")
    
    def _handle_transport_registration(self, phone_number, command_parts):
        """Handle transport company LITE registration via SMS
        
        Format: JOIN TRK [name] [location] [vehicle_type]
        or:     JOIN TRANSPORT [name] [location] [vehicle_type]
        
        Examples:
            JOIN TRK Chinedu Onitsha Cold
            JOIN TRANSPORT Mama Ngozi Kano 10ton
        """
        from models import TransportProfile
        from werkzeug.security import generate_password_hash
        import json
        
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if user:
            profile = TransportProfile.query.filter_by(user_id=user.id).first()
            if profile:
                return self.send_sms(phone_number,
                    f"You're already registered as transporter.\nID: {profile.transporter_id or 'TRK-XXXXX'}\nText JOBS to see available jobs.")
        
        if len(command_parts) < 5:
            message = ("Register as transporter:\nJOIN TRK [name] [location] [type]\n\n"
                      "Types: PICKUP, 10TON, 30TON, COLD\n\n"
                      "Examples:\nJOIN TRK Chinedu Onitsha COLD\n"
                      "JOIN TRK Ade Lagos 10TON")
            return self.send_sms(phone_number, message)
        
        vehicle_input = command_parts[-1].upper()
        location = command_parts[-2].title()
        name = ' '.join(command_parts[2:-2]).title() if len(command_parts) > 5 else command_parts[2].title()
        
        vehicle_map = {
            'PICKUP': ('pickup', False),
            'OKADA': ('pickup', False),
            'MOTORCYCLE': ('pickup', False),
            '5TON': ('medium_truck', False),
            '10TON': ('medium_truck', False),
            '15TON': ('large_truck', False),
            '30TON': ('large_truck', False),
            'COLD': ('refrigerated', True),
            'FRIDGE': ('refrigerated', True),
            'REFRIGERATED': ('refrigerated', True)
        }
        
        if vehicle_input not in vehicle_map:
            return self.send_sms(phone_number,
                "Invalid vehicle type.\nUse: PICKUP, 10TON, 30TON, or COLD\n\nExample: JOIN TRK Chinedu Lagos 10TON")
        
        vehicle_type, is_cold_chain = vehicle_map[vehicle_input]
        
        try:
            if not user:
                user = User(
                    name=name,
                    phone_number=phone_number,
                    email=f"{phone_number.replace('+', '').replace('-', '')}@transport.tradoja.com",
                    role='transport_company',
                    sms_enabled=True,
                    sms_registration_date=datetime.utcnow(),
                    source_channel='sms',
                    location=location,
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                user.password_hash = generate_password_hash('sms_transporter_temp')
                self._apply_device_fingerprint(user, phone_number)
                db.session.add(user)
                db.session.flush()
            
            transporter_id = TransportProfile.generate_transporter_id()
            
            profile = TransportProfile(
                user_id=user.id,
                company_name=name,
                main_location=location,
                vehicle_types=json.dumps([vehicle_type]),
                cold_chain_capable=is_cold_chain,
                profile_complete=False,
                registration_channel='sms_lite',
                transporter_id=transporter_id,
                routes_covered=json.dumps([[location]])
            )
            
            db.session.add(profile)
            db.session.commit()
            
            success_message = (f"Thank you {name}!\n"
                              f"You're registered as transporter.\n"
                              f"ID: {transporter_id}\n"
                              f"You'll receive jobs immediately.\n"
                              f"Send DOC to complete profile.")
            
            return self.send_sms(phone_number, success_message)
            
        except Exception as e:
            current_app.logger.error(f"SMS transport registration error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number, "Registration failed. Please try again or dial *712*55#")
    
    def _handle_buyer_registration(self, phone_number, command_parts):
        """Handle buyer LITE registration via SMS
        
        Format: JOIN BUYER [name] [location]
        or:     JOIN BUY [name] [location]
        
        Examples:
            JOIN BUYER Mama Ngozi Lagos
            JOIN BUY Chinedu Onitsha
        """
        from models import User
        from werkzeug.security import generate_password_hash
        from app import db
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if user:
            if user.role == 'buyer':
                return self.send_sms(phone_number,
                    f"You're already registered as buyer.\nText PRICE [crop] to check prices.")
        
        if len(command_parts) < 4:
            message = ("Register as buyer:\nJOIN BUYER [name] [location]\n\n"
                      "Examples:\nJOIN BUYER Mama Lagos\n"
                      "JOIN BUY Chinedu Onitsha")
            return self.send_sms(phone_number, message)
        
        location = command_parts[-1].title()
        name = ' '.join(command_parts[2:-1]).title() if len(command_parts) > 4 else command_parts[2].title()
        
        try:
            if user:
                user.role = 'buyer'
                user.buyer_type = 'retail_buyer'
                user.location = location
                user.sms_enabled = True
                user.source_channel = 'sms'
            else:
                user = User(
                    name=name,
                    phone_number=phone_number,
                    email=f"{phone_number.replace('+', '').replace('-', '')}@buyer.tradoja.com",
                    role='buyer',
                    buyer_type='retail_buyer',
                    sms_enabled=True,
                    source_channel='sms',
                    location=location,
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                user.password_hash = generate_password_hash('sms_buyer_temp')
                self._apply_device_fingerprint(user, phone_number)
                db.session.add(user)
            
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"Welcome {name}!\nYou're registered as buyer.\n"
                f"Location: {location}\n\n"
                f"Commands:\nPRICE [crop] - Check prices\n"
                f"Dial *712*55# for full menu")
        
        except Exception as e:
            current_app.logger.error(f"SMS buyer registration error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number, "Registration failed. Please try again or dial *712*55#")
    
    def _handle_agent_registration(self, phone_number, command_parts):
        """Handle agent LITE registration via SMS
        
        Format: JOIN AGENT [name] [location]
        or with NYSC: JOIN AGENT [name] NYSC-XX/XXX/XXXX
        
        Examples:
            JOIN AGENT Ahmed Katsina
            JOIN AGENT Ngozi NYSC-EN/24C/1234
        """
        from models import User, AgentProfile
        from werkzeug.security import generate_password_hash
        from app import db
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if user:
            profile = AgentProfile.query.filter_by(user_id=user.id).first()
            if profile:
                return self.send_sms(phone_number,
                    f"You're already registered as agent.\nID: {profile.agent_id}\nDial *712*55# > 9 for agent menu.")
        
        if len(command_parts) < 4:
            message = ("Register as agent:\nJOIN AGENT [name] [location]\n\n"
                      "Examples:\nJOIN AGENT Ahmed Katsina\n"
                      "JOIN AGENT Ngozi NYSC-EN/24C/1234")
            return self.send_sms(phone_number, message)
        
        location = command_parts[-1].title()
        name = ' '.join(command_parts[2:-1]).title() if len(command_parts) > 4 else command_parts[2].title()
        
        referral_code = None
        is_nysc = False
        if AgentProfile.is_valid_nysc_code(location):
            referral_code = location.upper()
            is_nysc = True
            location = command_parts[-2].title() if len(command_parts) > 4 else "Nigeria"
        
        try:
            if user:
                user.role = 'agent'
                user.location = location
                user.sms_enabled = True
                user.source_channel = 'sms'
            else:
                user = User(
                    name=name,
                    phone_number=phone_number,
                    email=f"{phone_number.replace('+', '').replace('-', '')}@agent.tradoja.com",
                    role='agent',
                    sms_enabled=True,
                    source_channel='sms',
                    location=location,
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                user.password_hash = generate_password_hash('sms_agent_temp')
                self._apply_device_fingerprint(user, phone_number)
                db.session.add(user)
                db.session.flush()
            
            agent_id = AgentProfile.generate_agent_id()
            
            profile = AgentProfile(
                user_id=user.id,
                agent_id=agent_id,
                lga=location,
                referral_code_used=referral_code,
                registration_channel='sms_lite',
                is_approved=is_nysc,
                is_nysc=is_nysc
            )
            
            db.session.add(profile)
            db.session.commit()
            
            approval_msg = "Auto-approved! Start registering now!" if is_nysc else "Approval in 24 hrs."
            
            return self.send_sms(phone_number,
                f"You are now an Tradoja Agent!\n"
                f"Your ID: {agent_id}\n"
                f"You will earn ₦200 airtime for every 10 farmers you register.\n"
                f"{approval_msg}\n"
                f"Dial *712*55# > 9 for agent menu.")
        
        except Exception as e:
            current_app.logger.error(f"SMS agent registration error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number, "Registration failed. Please try again or dial *712*55#")
    
    def _handle_doc_request(self, phone_number):
        """Handle DOC command to send profile completion link"""
        from models import TransportProfile
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Please register first.\nFarmers: JOIN [name] [location] [crop]\nTransporters: JOIN TRK [name] [location] [type]")
        
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        
        if not profile:
            return self.send_sms(phone_number,
                "You're not registered as a transporter.\nTo register: JOIN TRK [name] [location] [type]")
        
        if profile.profile_complete:
            return self.send_sms(phone_number,
                f"Your profile is already complete!\nID: {profile.transporter_id}\nRating: {profile.rating}/5\nText JOBS to see available jobs.")
        
        completion_message = (f"Complete your profile to:\n"
                            f"- Get higher job ranking\n"
                            f"- Earn cold-chain bonus (15%)\n"
                            f"- Upload documents\n\n"
                            f"Visit: tradoja.com/transport/complete\n"
                            f"Or call agent: 08012345678\n"
                            f"Your ID: {profile.transporter_id}")
        
        return self.send_sms(phone_number, completion_message)
    
    def _handle_my_listings(self, phone_number):
        """Handle MYLIST command - view farmer's own produce listings"""
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        listings = Produce.query.filter_by(farmer_id=user.id).order_by(
            Produce.created_at.desc()
        ).limit(5).all()
        
        if not listings:
            return self.send_sms(phone_number,
                "No produce listings yet.\n"
                "To list: LIST [crop] [qty] [price]\n"
                "Example: LIST TOMATOES 5T 150000")
        
        listing_text = []
        for p in listings:
            status = "Active" if p.status == 'available' else p.status.title()
            listing_text.append(f"{p.crop_type}: {p.quantity} @ N{p.price:,.0f} [{status}]")
        
        return self.send_sms(phone_number,
            f"Your Listings ({len(listings)}):\n" + "\n".join(listing_text))
    
    def _handle_balance_check(self, phone_number):
        """Handle BAL command - check account/wallet balance"""
        from models import SabiBuy, SabiBuyOrder, AgentProfile, TransportProfile, LogisticsBid
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        balances = []
        
        if user.t2_wallet_balance and user.t2_wallet_balance > 0:
            balances.append(f"T2 Wallet: N{user.t2_wallet_balance:,.0f}")
        
        campaigns = SabiBuy.query.filter_by(organizer_id=user.id).all()
        if campaigns:
            total_sb_earnings = sum(c.organizer_profit or 0 for c in campaigns if c.status == 'delivered')
            pending_sb = sum(c.organizer_profit or 0 for c in campaigns if c.status in ['active', 'closed', 'booked', 'in_transit'])
            if total_sb_earnings > 0 or pending_sb > 0:
                balances.append(f"SabiBuy Paid: N{total_sb_earnings:,.0f}")
                balances.append(f"SabiBuy Pending: N{pending_sb:,.0f}")
        
        agent_profile = AgentProfile.query.filter_by(user_id=user.id).first()
        if agent_profile:
            balances.append(f"Agent Earnings: N{agent_profile.total_earnings or 0:,.0f}")
        
        transport_profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if transport_profile:
            completed_bids = LogisticsBid.query.filter_by(
                transporter_id=transport_profile.id,
                status='completed'
            ).all()
            total_transport = sum(b.bid_amount or 0 for b in completed_bids)
            balances.append(f"Transport Earnings: N{total_transport:,.0f}")
        
        if not balances:
            return self.send_sms(phone_number,
                "No earnings yet.\n"
                "Start earning:\n"
                "- SabiBuy: Dial *712*55# > 10\n"
                "- Transport: JOIN TRK [name] [loc] [type]\n"
                "- Agent: JOIN AGENT [name] [loc]")
        
        return self.send_sms(phone_number,
            f"Balance Summary:\n" + "\n".join(balances))
    
    def _handle_sabibuy_earnings(self, phone_number):
        """Handle SBEARNINGS command - check SabiBuy campaign earnings"""
        from models import SabiBuy
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        campaigns = SabiBuy.query.filter_by(organizer_id=user.id).all()
        
        if not campaigns:
            return self.send_sms(phone_number,
                "No SabiBuy campaigns yet.\n"
                "Start earning N4k-N15k per batch!\n"
                "Dial *712*55# > 10 to start")
        
        total_profit = sum(c.organizer_profit or 0 for c in campaigns if c.status == 'delivered')
        pending = sum(c.organizer_profit or 0 for c in campaigns if c.status in ['active', 'closed', 'booked', 'in_transit'])
        active_campaigns = len([c for c in campaigns if c.status == 'active'])
        completed = len([c for c in campaigns if c.status == 'delivered'])
        
        return self.send_sms(phone_number,
            f"SabiBuy Earnings:\n"
            f"Total Paid: N{total_profit:,.0f}\n"
            f"Pending: N{pending:,.0f}\n"
            f"Active: {active_campaigns} campaigns\n"
            f"Completed: {completed} batches")
    
    def _handle_agent_balance(self, phone_number):
        """Handle AGENTBAL command - check agent referral earnings"""
        from models import AgentProfile
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN AGENT [name] [location]")
        
        profile = AgentProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not an agent.\n"
                "To become one: JOIN AGENT [name] [location]")
        
        farmers_count = User.query.filter_by(registered_by_agent_id=user.id).count()
        
        airtime_earned = (farmers_count // 10) * 200
        next_milestone = 10 - (farmers_count % 10)
        
        return self.send_sms(phone_number,
            f"Agent Earnings:\n"
            f"Agent ID: {profile.agent_id}\n"
            f"Farmers Registered: {farmers_count}\n"
            f"Airtime Earned: N{airtime_earned:,.0f}\n"
            f"Next N200: {next_milestone} more farmers\n"
            f"Total Earnings: N{profile.total_earnings or 0:,.0f}")
    
    def _handle_agent_add_farmer(self, phone_number, command_parts):
        """Handle AGENTADD command - register farmer on behalf of agent
        
        Format: AGENTADD [farmer_phone] [name] [location] [crop]
        Example: AGENTADD 08012345678 John Lagos Tomatoes
        """
        from models import AgentProfile
        from werkzeug.security import generate_password_hash
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register as agent first!\nJOIN AGENT [name] [location]")
        
        profile = AgentProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not an agent.\nTo become one: JOIN AGENT [name] [location]")
        
        if not profile.is_approved:
            return self.send_sms(phone_number,
                "Your agent account is pending approval.\nPlease wait 24 hours or contact support.")
        
        if len(command_parts) < 5:
            return self.send_sms(phone_number,
                "Format: AGENTADD [phone] [name] [location] [crop]\n"
                "Example: AGENTADD 08012345678 John Lagos Tomatoes")
        
        farmer_phone = self._normalize_phone_number(command_parts[1])
        farmer_name = command_parts[2].title()
        location = command_parts[3].title()
        main_crop = ' '.join(command_parts[4:])
        
        existing = User.query.filter_by(phone_number=farmer_phone).first()
        if existing:
            return self.send_sms(phone_number,
                f"Farmer {farmer_phone} is already registered.\n"
                f"Name: {existing.name}")
        
        try:
            farmer = User(
                name=farmer_name,
                phone_number=farmer_phone,
                email=f"{farmer_phone.replace('+', '')}@agent.tradoja.com",
                role='farmer',
                sms_enabled=True,
                sms_registration_date=datetime.utcnow(),
                source_channel='agent',
                location=location,
                registered_by_agent_id=user.id,
                agent_verified=True,
                registration_status='lite',
                lite_registration_date=datetime.utcnow()
            )
            farmer.password_hash = generate_password_hash('agent_registered_temp')
            
            db.session.add(farmer)
            
            farmers_by_agent = User.query.filter_by(registered_by_agent_id=user.id).count() + 1
            if farmers_by_agent % 10 == 0:
                profile.total_earnings = (profile.total_earnings or 0) + 200
            
            db.session.commit()
            
            self.send_sms(farmer_phone,
                f"Welcome to Tradoja!\n"
                f"Agent {user.name} registered you.\n"
                f"Text HELP for commands.\n"
                f"Your crop: {main_crop}")
            
            milestone_msg = ""
            if farmers_by_agent % 10 == 0:
                milestone_msg = f"\nMilestone! N200 airtime earned!"
            
            return self.send_sms(phone_number,
                f"Farmer registered!\n"
                f"Name: {farmer_name}\n"
                f"Phone: {farmer_phone}\n"
                f"Location: {location}\n"
                f"Total farmers: {farmers_by_agent}{milestone_msg}")
        
        except Exception as e:
            current_app.logger.error(f"Agent farmer registration error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number, "Registration failed. Please try again.")
    
    def _handle_transport_balance(self, phone_number):
        """Handle TRIPBAL command - check transport earnings"""
        from models import TransportProfile, LogisticsBid, LogisticsRequest
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! JOIN TRK [name] [location] [type]")
        
        profile = TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return self.send_sms(phone_number,
                "You're not a transporter.\nTo register: JOIN TRK [name] [location] [type]")
        
        completed_bids = LogisticsBid.query.filter_by(
            transporter_id=profile.id,
            status='completed'
        ).all()
        
        active_bids = LogisticsBid.query.filter_by(
            transporter_id=profile.id,
            status='accepted'
        ).all()
        
        total_earned = sum(b.bid_amount or 0 for b in completed_bids)
        pending = sum(b.bid_amount or 0 for b in active_bids)
        
        return self.send_sms(phone_number,
            f"Transport Earnings:\n"
            f"ID: {profile.transporter_id}\n"
            f"Completed: {len(completed_bids)} trips\n"
            f"Active: {len(active_bids)} trips\n"
            f"Total Earned: N{total_earned:,.0f}\n"
            f"Pending: N{pending:,.0f}")
    
    def _send_help_message(self, phone_number):
        """Send help message with available commands"""
        from models import TransportProfile, AgentProfile
        
        user = User.query.filter_by(phone_number=phone_number).first()
        transport_profile = TransportProfile.query.filter_by(user_id=user.id).first() if user else None
        agent_profile = AgentProfile.query.filter_by(user_id=user.id).first() if user else None
        
        help_message = ("Tradoja SMS Commands:\n\n"
                       "REGISTRATION:\n"
                       "REG [name] [loc] [crop]\n"
                       "REG BUYER [name] [loc]\n\n"
                       "FARMER:\n"
                       "SELL [crop] [qty] [price]\n"
                       "ACCEPT ORD-xxxx\n"
                       "PICKUP ORD-xxxx\n"
                       "PRICE [crop]\n\n"
                       "TRANSPORT:\n"
                       "JOBS - See jobs\n"
                       "CLAIM ORD-xxxx\n"
                       "DELIVER ORD-xxxx [OTP]\n\n"
                       "AI FEATURES:\n"
                       "AI [request] - Smart assistant\n"
                       "ADVICE [crop] - Price advice\n"
                       "RISK ORD-xxxx - Check safety\n\n"
                       "TRACEABILITY:\n"
                       "TRACE ORD-xxxx - Produce journey\n"
                       "QUALITY ORD-xxxx A - Record grade\n\n"
                       "TRACKING:\n"
                       "TRACK/CANCEL/STATUS/BAL\n")
        
        if transport_profile:
            help_message += ("\nTRANSPORT:\n"
                            "JOBS - Available jobs\n"
                            "BID [job_id] [amt]\n"
                            "MYBIDS - Your bids\n"
                            "START [job_id]\n"
                            "TRIPBAL - Earnings\n"
                            "DOC - Complete profile\n")
        
        if agent_profile:
            help_message += ("\nAGENT:\n"
                            "AGENTADD [phone] [name] [loc] [crop]\n"
                            "AGENTBAL - Your earnings\n")
        
        help_message += "\nHELP - This menu\nSTOP - Unsubscribe"
        
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
                alert_message = f"Tradoja Alert ({alert_type.title()}):\n{message}"
                return self.send_sms(phone_number, alert_message)
        except Exception as e:
            current_app.logger.error(f"Alert sending error: {e}")
    
    def notify_order_placed(self, farmer_phone, buyer_name, produce_name, quantity, amount):
        """Notify farmer when buyer places an order"""
        try:
            message = (f"New order!\n"
                      f"Buyer: {buyer_name}\n"
                      f"Product: {produce_name}\n"
                      f"Qty: {quantity}\n"
                      f"Amount: N{amount:,.0f}\n"
                      f"Check your dashboard or reply ACCEPT")
            return self.send_sms(farmer_phone, message)
        except Exception as e:
            current_app.logger.error(f"Order notification error: {e}")
    
    def notify_payment_received(self, seller_phone, amount, order_id, buyer_name):
        """Notify seller when payment is confirmed"""
        try:
            message = (f"Payment received!\n"
                      f"Amount: N{amount:,.0f}\n"
                      f"Order #{order_id}\n"
                      f"From: {buyer_name}\n"
                      f"Prepare for delivery.")
            return self.send_sms(seller_phone, message)
        except Exception as e:
            current_app.logger.error(f"Payment notification error: {e}")
    
    def notify_bid_received(self, farmer_phone, transporter_name, job_id, bid_amount, delivery_date=None):
        """Notify farmer when transporter bids on their logistics request"""
        try:
            message = (f"Transport bid!\n"
                      f"Job #{job_id}\n"
                      f"From: {transporter_name}\n"
                      f"Amount: N{bid_amount:,.0f}")
            if delivery_date:
                message += f"\nDelivery: {delivery_date}"
            message += "\nReply ACCEPT to confirm"
            return self.send_sms(farmer_phone, message)
        except Exception as e:
            current_app.logger.error(f"Bid notification error: {e}")
    
    def notify_bid_accepted(self, transporter_phone, job_id, pickup_location, delivery_location, amount):
        """Notify transporter when their bid is accepted"""
        try:
            message = (f"Bid accepted!\n"
                      f"Job #{job_id}\n"
                      f"Pickup: {pickup_location}\n"
                      f"Deliver: {delivery_location}\n"
                      f"Amount: N{amount:,.0f}\n"
                      f"Reply START {job_id} when ready")
            return self.send_sms(transporter_phone, message)
        except Exception as e:
            current_app.logger.error(f"Bid accepted notification error: {e}")
    
    def notify_sabibuy_order(self, organizer_phone, campaign_code, buyer_name, quantity, progress_percent):
        """Notify SabiBuy organizer when someone joins their campaign"""
        try:
            message = (f"SabiBuy order!\n"
                      f"Campaign: {campaign_code}\n"
                      f"Buyer: {buyer_name}\n"
                      f"Qty: {quantity}\n"
                      f"Progress: {progress_percent}%")
            return self.send_sms(organizer_phone, message)
        except Exception as e:
            current_app.logger.error(f"SabiBuy order notification error: {e}")
    
    def notify_sabibuy_complete(self, organizer_phone, campaign_code, total_orders, profit):
        """Notify organizer when SabiBuy campaign reaches minimum"""
        try:
            message = (f"SabiBuy complete!\n"
                      f"Campaign: {campaign_code}\n"
                      f"Orders: {total_orders}\n"
                      f"Your profit: N{profit:,.0f}\n"
                      f"Book transport now!")
            return self.send_sms(organizer_phone, message)
        except Exception as e:
            current_app.logger.error(f"SabiBuy complete notification error: {e}")
    
    def notify_delivery_started(self, buyer_phone, transporter_name, job_id, estimated_arrival=None):
        """Notify buyer when delivery is in transit"""
        try:
            message = (f"Delivery started!\n"
                      f"Job #{job_id}\n"
                      f"Driver: {transporter_name}")
            if estimated_arrival:
                message += f"\nETA: {estimated_arrival}"
            return self.send_sms(buyer_phone, message)
        except Exception as e:
            current_app.logger.error(f"Delivery notification error: {e}")
    
    def notify_delivery_complete(self, farmer_phone, job_id, amount):
        """Notify farmer when delivery is complete and payment will be released"""
        try:
            message = (f"Delivery complete!\n"
                      f"Job #{job_id}\n"
                      f"Payment: N{amount:,.0f} releasing\n"
                      f"Thank you for using Tradoja!")
            return self.send_sms(farmer_phone, message)
        except Exception as e:
            current_app.logger.error(f"Delivery complete notification error: {e}")
    
    def notify_agent_milestone(self, agent_phone, farmers_count, airtime_earned):
        """Notify agent when they reach a milestone"""
        try:
            message = (f"Agent milestone!\n"
                      f"Farmers registered: {farmers_count}\n"
                      f"Airtime earned: N{airtime_earned:,.0f}\n"
                      f"Keep up the great work!")
            return self.send_sms(agent_phone, message)
        except Exception as e:
            current_app.logger.error(f"Agent milestone notification error: {e}")
    
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
    
    def _handle_sabibuy_command(self, phone_number, command_parts):
        """Handle SabiBuy SMS commands
        
        Formats:
        - SABIBUY CODE - join a campaign
        - SABIBUY CODE QTY - join with quantity
        - SABIBUY START - create new campaign (prompts for details)
        """
        from models import SabiBuy, SabiBuyOrder
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "SabiBuy Commands:\n"
                "SABIBUY CODE - Join campaign\n"
                "SABIBUY CODE QTY - Join with quantity\n"
                "MYSABIBUY - Your campaigns\n"
                "Example: SABIBUY OBI-SABIBUY-48K 10")
        
        action = command_parts[1].upper()
        
        if action == 'START':
            return self.send_sms(phone_number,
                "To start SabiBuy, dial *712*55# > 10\n"
                "Or visit tradoja.com/sabibuy")
        
        if action == 'EARNINGS':
            campaigns = SabiBuy.query.filter_by(organizer_id=user.id).all()
            total_profit = sum(c.organizer_profit or 0 for c in campaigns if c.status == 'delivered')
            pending = sum(c.organizer_profit or 0 for c in campaigns if c.status in ['active', 'closed', 'booked', 'in_transit'])
            return self.send_sms(phone_number,
                f"SabiBuy Earnings:\n"
                f"Pending: ₦{pending:,.0f}\n"
                f"Total Paid: ₦{total_profit:,.0f}\n"
                f"Campaigns: {len(campaigns)}")
        
        campaign_code = action
        if '-SABIBUY-' not in campaign_code and not campaign_code.startswith('SB-'):
            if len(command_parts) >= 3 and '-SABIBUY-' in command_parts[2].upper():
                campaign_code = command_parts[2].upper()
        
        campaign = SabiBuy.query.filter_by(code=campaign_code).first()
        
        if not campaign:
            return self.send_sms(phone_number,
                f"Campaign code not found: {campaign_code}\n"
                "Check the code and try again.")
        
        if campaign.status != 'active':
            return self.send_sms(phone_number,
                f"Campaign {campaign_code} is {campaign.status}.\n"
                "It's no longer accepting orders.")
        
        quantity = 1
        if len(command_parts) >= 3:
            try:
                qty_str = command_parts[-1] if not command_parts[-1].upper().startswith('SB') else command_parts[2]
                quantity = int(re.sub(r'[^\d]', '', qty_str))
                if quantity < 1:
                    quantity = 1
            except ValueError:
                quantity = 1
        
        try:
            from services.sabibuy_service import sabibuy_service
            
            result = sabibuy_service.join_campaign(
                code=campaign_code,
                buyer_phone=phone_number,
                quantity=quantity,
                buyer_name=user.name,
                buyer_id=user.id,
                payment_method='pending',
                source_channel='sms',
                language=user.preferred_language or 'en'
            )
            
            if result.get('success'):
                total = result.get('total_amount', quantity * campaign.selling_price)
                produce = Produce.query.get(campaign.produce_id)
                produce_name = produce.crop_type if produce else 'Produce'
                
                return self.send_sms(phone_number,
                    f"Order placed!\n"
                    f"{quantity} {produce_name} @ ₦{campaign.selling_price:,.0f}\n"
                    f"Total: ₦{total:,.0f}\n"
                    f"Pay to complete your order.")
            else:
                return self.send_sms(phone_number, result.get('error', 'Order failed'))
                
        except Exception as e:
            current_app.logger.error(f"SabiBuy order error: {e}")
            return self.send_sms(phone_number, "Order failed. Please try again.")
    
    def _handle_my_sabibuy(self, phone_number):
        """Handle viewing user's SabiBuy campaigns"""
        from models import SabiBuy
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        campaigns = SabiBuy.query.filter_by(organizer_id=user.id).order_by(
            SabiBuy.created_at.desc()
        ).limit(5).all()
        
        if not campaigns:
            return self.send_sms(phone_number,
                "No SabiBuy campaigns yet.\n"
                "Dial *712*55# > 10 to start one!")
        
        campaign_list = []
        for c in campaigns:
            produce = Produce.query.get(c.produce_id)
            produce_name = produce.crop_type if produce else 'Produce'
            progress = int((c.current_quantity / c.minimum_quantity * 100)) if c.minimum_quantity > 0 else 0
            campaign_list.append(f"{c.campaign_code}: {produce_name} ({progress}%)")
        
        return self.send_sms(phone_number,
            f"Your SabiBuys:\n" + "\n".join(campaign_list))
    
    def _handle_sabibuy_join_code(self, phone_number, code, command_parts):
        """Handle direct SabiBuy code join (e.g., OBI-SABIBUY-48K 5)"""
        from models import SabiBuy
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first! Reply: JOIN [name] [location] [crop]")
        
        campaign_code = code.upper()
        campaign = SabiBuy.query.filter_by(code=campaign_code).first()
        
        if not campaign:
            return self.send_sms(phone_number,
                f"Campaign not found: {campaign_code}")
        
        if campaign.status != 'active':
            return self.send_sms(phone_number,
                f"Campaign {campaign_code} is no longer accepting orders.")
        
        quantity = 1
        if len(command_parts) >= 2:
            try:
                quantity = int(re.sub(r'[^\d]', '', command_parts[1]))
                if quantity < 1:
                    quantity = 1
            except ValueError:
                quantity = 1
        
        try:
            from services.sabibuy_service import sabibuy_service
            
            result = sabibuy_service.join_campaign(
                code=campaign_code,
                buyer_phone=phone_number,
                quantity=quantity,
                buyer_name=user.name,
                buyer_id=user.id,
                payment_method='pending',
                source_channel='sms',
                language=user.preferred_language or 'en'
            )
            
            if result.get('success'):
                total = result.get('total_amount', quantity * campaign.selling_price)
                produce = Produce.query.get(campaign.produce_id)
                produce_name = produce.crop_type if produce else 'Produce'
                
                return self.send_sms(phone_number,
                    f"Order placed for {campaign_code}!\n"
                    f"{quantity} {produce_name}\n"
                    f"Total: ₦{total:,.0f}")
            else:
                return self.send_sms(phone_number, result.get('error', 'Order failed'))
                
        except Exception as e:
            current_app.logger.error(f"SabiBuy join error: {e}")
            return self.send_sms(phone_number, "Order failed. Please try again.")


    def _handle_complaint(self, phone_number, command_parts):
        """Handle complaint/dispute filing via SMS
        
        Format: COMPLAINT [issue description]
        Examples:
        - COMPLAINT BAD QUALITY TOMATOES
        - REPORT FRAUD SELLER 08012345678
        - DISPUTE PAYMENT NOT RECEIVED
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "To file a complaint, send:\nCOMPLAINT [your issue]\n"
                "Example: COMPLAINT BAD QUALITY TOMATOES")
        
        issue_text = ' '.join(command_parts[1:])
        
        try:
            from services.dispute_service import dispute_service
            
            result = dispute_service.file_dispute_via_sms(
                phone=phone_number,
                message=issue_text,
                language=user.preferred_language or 'en'
            )
            
            if result.get('success'):
                return self.send_sms(phone_number, result.get('sms_response'))
            else:
                return self.send_sms(phone_number, 
                    result.get('sms_response', 'Could not process complaint. Please try again.'))
                
        except Exception as e:
            current_app.logger.error(f"Complaint error: {e}")
            return self.send_sms(phone_number,
                "Could not process complaint. Call support: 0800-AGROLINK")
    
    def _handle_order_tracking(self, phone_number, command_parts):
        """Handle order tracking via SMS
        
        Format: TRACK [code or order type]
        Examples:
        - TRACK NGOZI-SABIBUY-48K
        - TRACK MYORDERS
        - TRACK LOGISTICS
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "To track orders:\nTRACK [code]\n"
                "Or: TRACK MYORDERS for all orders")
        
        tracking_target = command_parts[1].upper()
        
        try:
            if tracking_target == 'MYORDERS':
                from models import SabiBuyOrder
                orders = SabiBuyOrder.query.filter_by(
                    buyer_phone=phone_number
                ).order_by(SabiBuyOrder.created_at.desc()).limit(3).all()
                
                if not orders:
                    return self.send_sms(phone_number, "No orders found.")
                
                order_lines = []
                for o in orders:
                    status = '✓' if o.delivered else ('💰' if o.payment_status == 'paid' else '⏳')
                    order_lines.append(f"{status} {o.campaign.code}: {o.quantity} units")
                
                return self.send_sms(phone_number,
                    "Your orders:\n" + "\n".join(order_lines))
            
            elif 'SABIBUY' in tracking_target or tracking_target.startswith('SB-'):
                from models import SabiBuy, SabiBuyOrder
                
                campaign = SabiBuy.query.filter_by(code=tracking_target).first()
                if not campaign:
                    return self.send_sms(phone_number,
                        f"Campaign not found: {tracking_target}")
                
                order = SabiBuyOrder.query.filter_by(
                    sabibuy_id=campaign.id,
                    buyer_phone=phone_number
                ).first()
                
                if not order:
                    return self.send_sms(phone_number,
                        f"You have no order in {tracking_target}")
                
                status_text = {
                    'pending': 'Awaiting payment',
                    'paid': 'Paid - In escrow',
                    'refunded': 'Refunded',
                    'released': 'Completed'
                }.get(order.payment_status, order.payment_status)
                
                delivery = "Delivered ✓" if order.delivered else "Pending delivery"
                
                return self.send_sms(phone_number,
                    f"Order: {tracking_target}\n"
                    f"Qty: {order.quantity}\n"
                    f"Status: {status_text}\n"
                    f"Delivery: {delivery}")
            
            elif tracking_target == 'LOGISTICS':
                from models import LogisticsRequest
                requests = LogisticsRequest.query.filter_by(
                    requester_id=user.id
                ).order_by(LogisticsRequest.created_at.desc()).limit(3).all()
                
                if not requests:
                    return self.send_sms(phone_number, "No logistics requests found.")
                
                lines = []
                for r in requests:
                    lines.append(f"#{r.id}: {r.status}")
                
                return self.send_sms(phone_number,
                    "Logistics:\n" + "\n".join(lines))
            
            elif tracking_target.startswith('ORD-') or tracking_target.startswith('ORD'):
                # Track order by code
                from models import Order
                order = Order.query.filter_by(order_code=tracking_target).first()
                if not order:
                    return self.send_sms(phone_number,
                        f"Order {tracking_target} not found.")
                
                # Check user has access to this order
                if order.farmer_id != user.id and order.buyer_id != user.id and order.transporter_id != user.id:
                    return self.send_sms(phone_number,
                        "You don't have access to this order.")
                
                # Build status message
                status = order.get_status_display()
                msg = f"Order: {order.order_code}\n"
                msg += f"Status: {status}\n"
                msg += f"Amount: N{order.total_amount:,.0f}\n"
                
                if order.last_location:
                    msg += f"Location: {order.last_location}\n"
                
                # Add next action hint based on status and role
                if order.status == 'pending' and order.farmer_id == user.id:
                    msg += f"Action: ACCEPT {order.order_code}"
                elif order.status == 'accepted' and order.farmer_id == user.id:
                    msg += f"Action: PICKUP {order.order_code}"
                elif order.status in ['pickup_confirmed', 'in_transit'] and order.transporter_id == user.id:
                    msg += f"Action: DELIVER {order.order_code} [buyer-OTP]"
                
                return self.send_sms(phone_number, msg)
            
            else:
                return self.send_sms(phone_number,
                    f"Invalid tracking code: {tracking_target}\n"
                    "Use: TRACK ORD-xxxx or TRACK MYORDERS")
                
        except Exception as e:
            current_app.logger.error(f"Tracking error: {e}")
            return self.send_sms(phone_number,
                "Could not fetch tracking info. Please try again.")
    
    def _handle_pickup_confirmation(self, phone_number, command_parts):
        """Handle farmer confirming pickup by transporter
        
        Format: PICKUP [order-code]
        Example: PICKUP ORD-7842
        """
        from models import Order
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "Format: PICKUP [order-code]\nExample: PICKUP ORD-7842")
        
        order_code = command_parts[1].upper()
        
        try:
            order = Order.query.filter_by(order_code=order_code).first()
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            # Verify user is the farmer
            if order.farmer_id != user.id:
                return self.send_sms(phone_number,
                    "Only the seller can confirm pickup.")
            
            # Check order status
            if order.status != 'accepted':
                return self.send_sms(phone_number,
                    f"Order cannot be picked up. Status: {order.get_status_display()}")
            
            # Confirm pickup
            order.confirm_pickup()
            db.session.commit()
            
            # Record pickup in traceability chain
            try:
                from services.traceability_service import traceability_service
                traceability_service.record_order_events(
                    order_id=order.id,
                    event_type='pickup',
                    user_id=user.id,
                    role='farmer',
                    location=order.pickup_location or user.location,
                    source_channel='sms'
                )
            except Exception as te:
                current_app.logger.error(f"Trace pickup error: {te}")
            
            # Notify transporter if assigned
            if order.transporter:
                self.send_sms(order.transporter.phone_number,
                    f"Pickup confirmed for {order_code}. You may begin transit.\n"
                    f"Destination: {order.destination}\n"
                    f"Update location: LOCATION {order_code}")
            
            # Notify buyer
            if order.buyer.phone_number:
                self.send_sms(order.buyer.phone_number,
                    f"Your order {order_code} has been picked up.\n"
                    f"Track: TRACK {order_code}")
            
            return self.send_sms(phone_number,
                f"Pickup confirmed for {order_code}.\n"
                f"Goods handed to transporter. You'll be notified when delivered.")
            
        except Exception as e:
            current_app.logger.error(f"Pickup confirmation error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error confirming pickup. Please try again.")
    
    def _handle_location_update(self, phone_number, command_parts):
        """Handle transporter reporting location
        
        Format: LOCATION [order-code] [location-text]
        Example: LOCATION ORD-7842 Ibadan expressway
        """
        from models import Order
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: REG TRK [name] [vehicle] [capacity]")
        
        if len(command_parts) < 3:
            return self.send_sms(phone_number,
                "Format: LOCATION [order-code] [location]\n"
                "Example: LOCATION ORD-7842 Ibadan expressway")
        
        order_code = command_parts[1].upper()
        location = ' '.join(command_parts[2:])
        
        try:
            order = Order.query.filter_by(order_code=order_code).first()
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            # Verify user is the transporter
            if order.transporter_id != user.id:
                return self.send_sms(phone_number,
                    "Only the assigned transporter can update location.")
            
            # Update location and status
            order.update_location(location)
            if order.status == 'pickup_confirmed':
                order.start_transit()
            
            # Record location in traceability chain
            try:
                from services.traceability_service import traceability_service
                traceability_service.record_order_events(
                    order_id=order.id,
                    event_type='location_update',
                    user_id=user.id,
                    role='transporter',
                    location=location,
                    source_channel='sms'
                )
            except Exception as te:
                current_app.logger.error(f"Trace location error: {te}")
            
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"Location updated: {location}\n"
                f"When delivered, send: DELIVER {order_code} [buyer-OTP]")
            
        except Exception as e:
            current_app.logger.error(f"Location update error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error updating location. Please try again.")
    
    def _handle_delivery_confirmation(self, phone_number, command_parts):
        """Handle transporter confirming delivery with OTP
        
        Format: DELIVER [order-code] [otp]
        Example: DELIVER ORD-7842 4829
        """
        from models import Order, EscrowHold
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: REG TRK [name] [vehicle] [capacity]")
        
        if len(command_parts) < 3:
            return self.send_sms(phone_number,
                "Format: DELIVER [order-code] [buyer-OTP]\n"
                "Example: DELIVER ORD-7842 4829\n"
                "Get OTP from buyer at delivery.")
        
        order_code = command_parts[1].upper()
        otp_input = command_parts[2]
        
        try:
            order = Order.query.filter_by(order_code=order_code).first()
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            # Verify user is the transporter
            if order.transporter_id != user.id:
                return self.send_sms(phone_number,
                    "Only the assigned transporter can confirm delivery.")
            
            # Check order status
            if order.status not in ['pickup_confirmed', 'in_transit']:
                return self.send_sms(phone_number,
                    f"Order not ready for delivery. Status: {order.get_status_display()}")
            
            # Verify OTP
            success, message = order.verify_otp(otp_input)
            
            if success:
                # AI-powered auto-release verification
                try:
                    from services.ai_trading_service import ai_trading_service
                    release_check = ai_trading_service.evaluate_auto_release(order.id)
                    
                    if release_check.get('require_manual_review'):
                        # Persist review-required state
                        order.status = 'delivery_review'
                        if order.escrow:
                            order.escrow.status = 'review'
                            order.escrow.admin_notes = f"AI flagged: {release_check.get('reason', 'Manual review required')[:200]}"
                        db.session.commit()
                        return self.send_sms(phone_number,
                            f"Delivery noted for {order_code}.\n"
                            f"AI flagged for review: {release_check.get('reason', 'Additional verification')[:60]}\n"
                            f"Funds release pending approval.")
                except Exception as ai_err:
                    current_app.logger.warning(f"AI release check failed: {ai_err}")
                
                # Verify escrow is funded before releasing
                if order.escrow and order.escrow.status != 'held':
                    db.session.commit()
                    return self.send_sms(phone_number,
                        f"Delivery confirmed but payment issue.\n"
                        f"Escrow status: {order.escrow.status}. Contact support.")
                
                # Auto-release escrow
                order.complete_order()
                
                # Release escrow if exists and is held
                if order.escrow and order.escrow.status == 'held':
                    order.escrow.status = 'released'
                    order.escrow.release_date = datetime.utcnow()
                    order.escrow.released_to_id = order.farmer_id
                    order.escrow.ai_verified = True
                
                # Record delivery in traceability chain
                try:
                    from services.traceability_service import traceability_service
                    traceability_service.record_order_events(
                        order_id=order.id,
                        event_type='delivery',
                        user_id=user.id,
                        role='transporter',
                        location=order.destination,
                        source_channel='sms'
                    )
                except Exception as te:
                    current_app.logger.error(f"Trace delivery error: {te}")
                
                db.session.commit()
                
                # Notify farmer
                if order.farmer.phone_number:
                    farmer_amount = order.total_amount - order.platform_fee
                    self.send_sms(order.farmer.phone_number,
                        f"Delivery confirmed for {order_code}!\n"
                        f"Payment of N{farmer_amount:,.0f} released to your account.")
                
                # Notify buyer
                if order.buyer.phone_number:
                    self.send_sms(order.buyer.phone_number,
                        f"Delivery confirmed for {order_code}.\n"
                        f"Thank you! Rate: RATE {order_code} [1-5] [comment]")
                
                return self.send_sms(phone_number,
                    f"Delivery confirmed for {order_code}!\n"
                    f"OTP verified. Transaction complete.\n"
                    f"Your logistics fee will be paid shortly.")
            else:
                db.session.commit()
                return self.send_sms(phone_number, f"Delivery failed: {message}")
            
        except Exception as e:
            current_app.logger.error(f"Delivery confirmation error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error confirming delivery. Please try again.")
    
    def _handle_rating(self, phone_number, command_parts):
        """Handle rating submission via SMS
        
        Format: RATE [code/phone] [1-5 stars] [comment]
        Examples:
        - RATE NGOZI-SABIBUY-48K 5 GREAT SERVICE
        - RATE 08012345678 4 GOOD QUALITY
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 3:
            return self.send_sms(phone_number,
                "To rate:\nRATE [code] [1-5] [comment]\n"
                "Example: RATE NGOZI-SABIBUY-48K 5 GREAT")
        
        target = command_parts[1]
        
        try:
            rating = int(command_parts[2])
            if rating < 1 or rating > 5:
                raise ValueError()
        except ValueError:
            return self.send_sms(phone_number,
                "Rating must be 1-5 stars")
        
        comment = ' '.join(command_parts[3:]) if len(command_parts) > 3 else ''
        
        try:
            from services.rating_service import rating_service
            
            if 'SABIBUY' in target.upper() or target.upper().startswith('SB-'):
                from models import SabiBuy
                campaign = SabiBuy.query.filter_by(code=target.upper()).first()
                if campaign:
                    result = rating_service.submit_rating(
                        rater_id=user.id,
                        rated_id=campaign.organizer_id,
                        overall_rating=rating,
                        comment=comment,
                        transaction_type='purchase'
                    )
                    
                    if result.get('success'):
                        return self.send_sms(phone_number,
                            f"Thanks! Rated {rating}/5 stars")
                    else:
                        return self.send_sms(phone_number,
                            result.get('error', 'Rating failed'))
            
            rated_user = User.query.filter_by(phone_number=target).first()
            if rated_user:
                result = rating_service.submit_rating(
                    rater_id=user.id,
                    rated_id=rated_user.id,
                    overall_rating=rating,
                    comment=comment,
                    transaction_type='purchase'
                )
                
                if result.get('success'):
                    return self.send_sms(phone_number,
                        f"Thanks! Rated {rating}/5 stars")
                else:
                    return self.send_sms(phone_number,
                        result.get('error', 'Rating failed'))
            
            return self.send_sms(phone_number,
                f"Could not find: {target}")
                
        except Exception as e:
            current_app.logger.error(f"Rating error: {e}")
            return self.send_sms(phone_number,
                "Rating failed. Please try again.")
    
    def _handle_status_check(self, phone_number, command_parts):
        """Handle status check via SMS
        
        Format: STATUS [optional: dispute ticket]
        Examples:
        - STATUS
        - STATUS DISP-000123
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) > 1:
            ticket = command_parts[1].upper()
            
            if ticket.startswith('DISP-'):
                from models import Dispute
                try:
                    dispute_id = int(ticket.replace('DISP-', ''))
                    dispute = Dispute.query.get(dispute_id)
                    
                    if dispute and dispute.complainant_id == user.id:
                        badge_class, status_text = dispute.get_status_badge()
                        return self.send_sms(phone_number,
                            f"Ticket: {ticket}\n"
                            f"Status: {status_text}\n"
                            f"Type: {dispute.dispute_type}")
                    else:
                        return self.send_sms(phone_number,
                            f"Ticket {ticket} not found or not yours")
                except:
                    return self.send_sms(phone_number,
                        f"Invalid ticket: {ticket}")
        
        from models import SabiBuyOrder, Dispute
        
        open_orders = SabiBuyOrder.query.filter_by(
            buyer_phone=phone_number,
            delivered=False
        ).filter(SabiBuyOrder.payment_status.in_(['pending', 'paid'])).count()
        
        open_disputes = Dispute.query.filter_by(
            complainant_id=user.id
        ).filter(Dispute.status.in_(['open', 'investigating'])).count()
        
        rating_info = f"Rating: {user.average_rating:.1f}/5" if user.total_ratings else "No ratings yet"
        
        return self.send_sms(phone_number,
            f"Account: {user.name}\n"
            f"Open orders: {open_orders}\n"
            f"Open disputes: {open_disputes}\n"
            f"{rating_info}")
    
    def _handle_pay_command(self, phone_number, command_parts):
        """Handle PAY command for produce purchases or logistics payments
        
        Formats:
        - PAY [listing_id] [amount] - Pay for produce listing
        - PAY [listing_id] WALLET - Pay using T2 wallet
        - PAY [listing_id] BANK [bank_code] - Generate USSD code for bank payment
        - PAY SABIBUY [code] [amount] - Pay for SabiBuy order
        
        Examples:
        - PAY 123 50000
        - PAY 123 WALLET
        - PAY 123 BANK 058 (GTBank)
        - PAY SABIBUY SB-RICE-001 25000
        """
        from wallet_service import wallet_service
        from payment_service import payment_service
        from models import Produce, Transaction, EscrowHold
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "Payment format:\n"
                "PAY [listing_id] WALLET - use wallet\n"
                "PAY [listing_id] BANK [code] - bank USSD\n"
                "Reply BANKS for bank codes")
        
        target = command_parts[1]
        
        if target == 'BANKS':
            return self.send_sms(phone_number, payment_service.format_bank_list_sms())
        
        if target == 'SABIBUY' or target == 'SB':
            return self._handle_sabibuy_payment(phone_number, command_parts[2:], user)
        
        try:
            produce_id = int(target)
            produce = Produce.query.get(produce_id)
            
            if not produce:
                return self.send_sms(phone_number, f"Listing #{produce_id} not found")
            
            if not produce.is_available:
                return self.send_sms(phone_number, f"Listing #{produce_id} is no longer available")
            
            if produce.farmer_id == user.id:
                return self.send_sms(phone_number, "You cannot buy your own listing")
            
            amount = produce.price
            user_type = 'farmer' if user.role == 'farmer' else ('verified_trader' if user.trader_verified else 'buyer')
            fee_info = payment_service.calculate_tiered_fee(amount, user_type)
            total = fee_info['total_amount']
            
            if len(command_parts) >= 3:
                payment_method = command_parts[2].upper()
                
                if payment_method == 'WALLET':
                    wallet_balance = wallet_service.get_balance(user)
                    if wallet_balance < total:
                        return self.send_sms(phone_number,
                            f"Insufficient wallet balance.\n"
                            f"Balance: N{wallet_balance:,.0f}\n"
                            f"Required: N{total:,.0f}\n"
                            f"Top up: TOPUP [amount]")
                    
                    success, msg, ref = wallet_service.hold_escrow(
                        user, total,
                        f"Payment for {produce.name} (#{produce.id})",
                        produce_id=produce.id,
                        db_session=db.session
                    )
                    
                    if success:
                        db.session.commit()
                        self._notify_seller_payment(produce.farmer, produce, user, total)
                        return self.send_sms(phone_number,
                            f"Payment held in escrow!\n"
                            f"Item: {produce.name}\n"
                            f"Amount: N{total:,.0f}\n"
                            f"Ref: {ref}\n"
                            f"Seller notified. Await delivery.")
                    else:
                        return self.send_sms(phone_number, f"Payment failed: {msg}")
                
                elif payment_method == 'BANK':
                    if len(command_parts) < 4:
                        return self.send_sms(phone_number,
                            "Specify bank code.\n"
                            "Reply BANKS for codes.\n"
                            "Example: PAY 123 BANK 058")
                    
                    bank_code = command_parts[3]
                    ref = payment_service.generate_reference(f"SMS_{produce.id}")
                    
                    email = user.email if '@sms.' not in user.email else f"sms_{phone_number.replace('+', '')}@tradoja.com"
                    
                    result = payment_service.charge_ussd(email, total, ref, bank_code)
                    
                    if result.get('success'):
                        transaction = Transaction(
                            reference=ref,
                            user_id=user.id,
                            transaction_type='produce_sale',
                            base_amount=amount,
                            platform_fee=fee_info['platform_fee'],
                            total_amount=total,
                            payment_method='ussd',
                            status='pending',
                            produce_id=produce.id
                        )
                        db.session.add(transaction)
                        db.session.commit()
                        
                        return self.send_sms(phone_number,
                            f"Dial to pay:\n"
                            f"{result['ussd_code']}\n"
                            f"Amount: N{total:,.0f}\n"
                            f"Ref: {ref}\n"
                            f"Check: STATUS {ref}")
                    else:
                        return self.send_sms(phone_number,
                            f"USSD failed: {result.get('message')}\n"
                            f"Try: PAY {produce_id} WALLET")
            
            return self.send_sms(phone_number,
                f"Confirm payment:\n"
                f"Item: {produce.name}\n"
                f"Qty: {produce.quantity}\n"
                f"Price: N{amount:,.0f}\n"
                f"Fee: N{fee_info['platform_fee']:,.0f}\n"
                f"Total: N{total:,.0f}\n\n"
                f"Reply:\n"
                f"PAY {produce_id} WALLET - from balance\n"
                f"PAY {produce_id} BANK [code] - via bank")
            
        except ValueError:
            return self.send_sms(phone_number,
                f"Invalid listing ID: {target}\n"
                f"Use: PAY [listing_id] WALLET")
        except Exception as e:
            current_app.logger.error(f"Pay command error: {e}")
            return self.send_sms(phone_number, "Payment failed. Try again later.")
    
    def _handle_sabibuy_payment(self, phone_number, command_parts, user):
        """Handle SabiBuy order payment via SMS"""
        from wallet_service import wallet_service
        from models import SabiBuy, SabiBuyOrder
        
        if len(command_parts) < 1:
            return self.send_sms(phone_number,
                "Format: PAY SABIBUY [campaign_code]\n"
                "Example: PAY SABIBUY SB-RICE-001")
        
        campaign_code = command_parts[0].upper()
        
        campaign = SabiBuy.query.filter(
            db.func.upper(SabiBuy.campaign_code) == campaign_code
        ).first()
        
        if not campaign:
            return self.send_sms(phone_number, f"Campaign {campaign_code} not found")
        
        if campaign.status != 'active':
            return self.send_sms(phone_number,
                f"Campaign {campaign_code} is {campaign.status}")
        
        order = SabiBuyOrder.query.filter_by(
            campaign_id=campaign.id,
            buyer_phone=phone_number,
            payment_status='pending'
        ).first()
        
        if not order:
            return self.send_sms(phone_number,
                f"No pending order for {campaign_code}\n"
                f"First join: {campaign_code} [quantity]")
        
        wallet_balance = wallet_service.get_balance(user)
        if wallet_balance < order.total_amount:
            return self.send_sms(phone_number,
                f"Insufficient balance.\n"
                f"Balance: N{wallet_balance:,.0f}\n"
                f"Order: N{order.total_amount:,.0f}\n"
                f"Top up: TOPUP [amount]")
        
        success, msg, ref = wallet_service.debit_wallet(
            user, order.total_amount,
            f"SabiBuy order: {campaign.campaign_code}",
            db_session=db.session
        )
        
        if success:
            order.payment_status = 'paid'
            order.payment_reference = ref
            order.payment_date = datetime.utcnow()
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"SabiBuy payment confirmed!\n"
                f"Campaign: {campaign.campaign_code}\n"
                f"Amount: N{order.total_amount:,.0f}\n"
                f"Qty: {order.quantity}\n"
                f"Track: TRACK {campaign.campaign_code}")
        else:
            return self.send_sms(phone_number, f"Payment failed: {msg}")
    
    def _handle_wallet_command(self, phone_number, command_parts):
        """Handle WALLET command - view balance and recent transactions
        
        Formats:
        - WALLET - show balance and recent transactions
        - WALLET SEND [phone] [amount] - transfer to another user
        """
        from wallet_service import wallet_service
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) > 1 and command_parts[1] == 'SEND':
            if len(command_parts) < 4:
                return self.send_sms(phone_number,
                    "Format: WALLET SEND [phone] [amount]\n"
                    "Example: WALLET SEND 08012345678 5000")
            
            to_phone = self._normalize_phone_number(command_parts[2])
            try:
                amount = float(command_parts[3].replace(',', ''))
            except ValueError:
                return self.send_sms(phone_number, "Invalid amount")
            
            to_user = User.query.filter_by(phone_number=to_phone).first()
            if not to_user:
                return self.send_sms(phone_number,
                    f"User {command_parts[2]} not found on Tradoja")
            
            if to_user.id == user.id:
                return self.send_sms(phone_number, "Cannot transfer to yourself")
            
            success, msg, ref = wallet_service.transfer(
                user, to_user, amount,
                "SMS wallet transfer",
                db_session=db.session
            )
            
            if success:
                db.session.commit()
                self.send_sms(to_phone,
                    f"Received N{amount:,.0f} from {user.name}\n"
                    f"New balance: N{wallet_service.get_balance(to_user):,.0f}")
                return self.send_sms(phone_number,
                    f"Sent N{amount:,.0f} to {to_user.name}\n"
                    f"Ref: {ref}\n"
                    f"Balance: N{wallet_service.get_balance(user):,.0f}")
            else:
                return self.send_sms(phone_number, msg)
        
        balance = wallet_service.get_balance(user)
        history = wallet_service.format_history_sms(user, 3)
        
        return self.send_sms(phone_number,
            f"T2 Wallet Balance: N{balance:,.0f}\n\n"
            f"{history}\n\n"
            f"WALLET SEND [phone] [amt] - transfer\n"
            f"TOPUP [amount] - add funds")
    
    def _handle_topup_command(self, phone_number, command_parts):
        """Handle TOPUP command - add funds to wallet via Paystack USSD
        
        Formats:
        - TOPUP [amount] - show bank options
        - TOPUP [amount] [bank_code] - generate USSD code
        """
        from payment_service import payment_service
        from models import Transaction
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "Format: TOPUP [amount] [bank_code]\n"
                "Example: TOPUP 10000 058\n"
                "Reply BANKS for bank codes")
        
        try:
            amount = float(command_parts[1].replace(',', '').replace('N', ''))
        except ValueError:
            return self.send_sms(phone_number, "Invalid amount")
        
        if amount < 100:
            return self.send_sms(phone_number, "Minimum top-up is N100")
        
        if amount > 500000:
            return self.send_sms(phone_number, "Maximum top-up is N500,000")
        
        if len(command_parts) < 3:
            banks = payment_service.get_bank_ussd_codes()
            bank_list = "\n".join([f"{info['name']}: {code}" for code, info in list(banks.items())[:6]])
            return self.send_sms(phone_number,
                f"Top-up N{amount:,.0f}\n"
                f"Select bank code:\n{bank_list}\n"
                f"Reply: TOPUP {int(amount)} [code]")
        
        bank_code = command_parts[2]
        ref = payment_service.generate_reference(f"TOPUP_{user.id}")
        
        email = user.email if '@sms.' not in user.email else f"sms_{phone_number.replace('+', '')}@tradoja.com"
        
        result = payment_service.charge_ussd(email, amount, ref, bank_code)
        
        if result.get('success'):
            transaction = Transaction(
                reference=ref,
                user_id=user.id,
                transaction_type='wallet_topup',
                base_amount=amount,
                platform_fee=0,
                total_amount=amount,
                payment_method='ussd',
                status='pending',
                transaction_metadata=f'{{"phone":"{phone_number}","bank":"{bank_code}"}}'
            )
            db.session.add(transaction)
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"Dial to top up:\n"
                f"{result['ussd_code']}\n"
                f"Amount: N{amount:,.0f}\n"
                f"Ref: {ref}")
        else:
            return self.send_sms(phone_number,
                f"Failed: {result.get('message')}\n"
                f"Try a different bank")
    
    def _handle_bond_command(self, phone_number, command_parts):
        """Handle BOND command for SabiBuy Captain bond management
        
        Formats:
        - BOND - check bond status
        - BOND PAY - pay Captain bond from wallet
        - BOND REFUND - request bond refund (if eligible)
        """
        from wallet_service import wallet_service
        from models import CaptainBond
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        active_bond = CaptainBond.query.filter_by(
            user_id=user.id, status='active'
        ).first()
        
        if len(command_parts) < 2:
            if active_bond:
                return self.send_sms(phone_number,
                    f"Captain Bond: ACTIVE\n"
                    f"Amount: N{active_bond.amount:,.0f}\n"
                    f"Campaigns: {active_bond.campaigns_run}\n"
                    f"Ref: {active_bond.reference}\n\n"
                    f"To refund: BOND REFUND")
            else:
                return self.send_sms(phone_number,
                    f"No active Captain bond.\n"
                    f"Captain bond = N10,000 (refundable)\n"
                    f"Required to start SabiBuy campaigns.\n\n"
                    f"To pay: BOND PAY")
        
        action = command_parts[1].upper()
        
        if action == 'PAY':
            if active_bond:
                return self.send_sms(phone_number,
                    f"You already have an active bond (N{active_bond.amount:,.0f})")
            
            balance = wallet_service.get_balance(user)
            bond_amount = wallet_service.CAPTAIN_BOND_AMOUNT
            
            if balance < bond_amount:
                return self.send_sms(phone_number,
                    f"Insufficient balance.\n"
                    f"Balance: N{balance:,.0f}\n"
                    f"Bond required: N{bond_amount:,.0f}\n"
                    f"Top up: TOPUP {int(bond_amount - balance)}")
            
            success, msg, ref = wallet_service.collect_captain_bond(user, db_session=db.session)
            
            if success:
                db.session.commit()
                return self.send_sms(phone_number,
                    f"Captain bond paid!\n"
                    f"Amount: N{bond_amount:,.0f}\n"
                    f"Ref: {ref}\n"
                    f"You can now start SabiBuy campaigns!")
            else:
                return self.send_sms(phone_number, f"Bond payment failed: {msg}")
        
        elif action == 'REFUND':
            if not active_bond:
                return self.send_sms(phone_number, "No active bond to refund")
            
            from models import SabiBuy
            active_campaigns = SabiBuy.query.filter_by(
                organizer_id=user.id
            ).filter(SabiBuy.status.in_(['active', 'closed', 'booked', 'in_transit'])).count()
            
            if active_campaigns > 0:
                return self.send_sms(phone_number,
                    f"Cannot refund: {active_campaigns} active campaign(s).\n"
                    f"Complete all campaigns first.")
            
            success, msg = wallet_service.refund_captain_bond(user, db_session=db.session)
            
            if success:
                db.session.commit()
                return self.send_sms(phone_number,
                    f"Bond refunded!\n"
                    f"{msg}\n"
                    f"Balance: N{wallet_service.get_balance(user):,.0f}")
            else:
                return self.send_sms(phone_number, f"Refund failed: {msg}")
        
        return self.send_sms(phone_number,
            "Bond commands:\n"
            "BOND - check status\n"
            "BOND PAY - pay bond\n"
            "BOND REFUND - request refund")
    
    def _handle_transaction_history(self, phone_number):
        """Handle HISTORY/TXN command - show recent transactions"""
        from wallet_service import wallet_service
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        history = wallet_service.format_history_sms(user, 5)
        balance = wallet_service.get_balance(user)
        
        return self.send_sms(phone_number,
            f"Balance: N{balance:,.0f}\n\n{history}")
    
    def _notify_seller_payment(self, seller, produce, buyer, amount):
        """Notify seller when payment is received"""
        try:
            if seller.phone_number:
                self.send_sms(seller.phone_number,
                    f"Payment received!\n"
                    f"Item: {produce.name}\n"
                    f"Amount: N{amount:,.0f}\n"
                    f"Buyer: {buyer.name}\n"
                    f"Phone: {buyer.phone_number}\n"
                    f"Funds held in escrow until delivery confirmed.")
        except Exception as e:
            current_app.logger.error(f"Seller notification error: {e}")
    
    def _handle_delivery_confirmation(self, phone_number, command_parts):
        """Handle CONFIRM command to release escrow after delivery
        
        Format: CONFIRM [escrow_ref or produce_id]
        Examples:
        - CONFIRM ESC_20231201_ABC123
        - CONFIRM 456 (produce ID)
        """
        from wallet_service import wallet_service
        from models import EscrowHold, Produce
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            escrows = EscrowHold.query.filter_by(
                user_id=user.id,
                status='held'
            ).all()
            
            if not escrows:
                return self.send_sms(phone_number, "No pending deliveries to confirm.")
            
            lines = ["Pending deliveries:"]
            for e in escrows[:5]:
                produce = Produce.query.get(e.produce_id) if e.produce_id else None
                name = produce.name if produce else "Item"
                lines.append(f"- {name}: CONFIRM {e.reference}")
            
            return self.send_sms(phone_number, "\n".join(lines))
        
        identifier = command_parts[1]
        
        escrow = EscrowHold.query.filter(
            (EscrowHold.reference == identifier) | 
            (EscrowHold.produce_id == int(identifier) if identifier.isdigit() else False)
        ).filter_by(user_id=user.id, status='held').first()
        
        if not escrow:
            return self.send_sms(phone_number,
                f"Order {identifier} not found or already confirmed.")
        
        produce = Produce.query.get(escrow.produce_id) if escrow.produce_id else None
        seller = produce.farmer if produce else None
        
        if not seller:
            return self.send_sms(phone_number, "Seller not found.")
        
        success, msg = wallet_service.release_escrow(
            escrow.reference,
            seller,
            db_session=db.session
        )
        
        if success:
            if produce:
                produce.is_available = False
                produce.buyer_id = user.id
            db.session.commit()
            
            if seller.phone_number:
                try:
                    self.send_sms(seller.phone_number,
                        f"Payment released!\n"
                        f"Item: {produce.name if produce else 'Item'}\n"
                        f"Amount: N{escrow.amount:,.0f}\n"
                        f"Buyer: {user.name}\n"
                        f"Balance: N{wallet_service.get_balance(seller):,.0f}")
                except:
                    pass
            
            return self.send_sms(phone_number,
                f"Delivery confirmed!\n"
                f"Released: N{escrow.amount:,.0f}\n"
                f"To: {seller.name}\n"
                f"Thank you!")
        else:
            return self.send_sms(phone_number, f"Confirmation failed: {msg}")
    
    def _handle_subscribe_command(self, phone_number, command_parts):
        """Handle subscription enrollment via SMS
        
        Format: SUBSCRIBE [plan]
        Plans:
        - FREE - Basic access (default)
        - CAPTAIN - SabiBuy organizer (₦2,500/month)
        - PREMIUM - Full features (₦5,000/month)
        """
        from wallet_service import wallet_service
        from payment_service import payment_service
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            current_plan = user.subscription_plan_code or 'free'
            is_active = user.is_premium and user.subscription_end_date and user.subscription_end_date > datetime.utcnow()
            
            return self.send_sms(phone_number,
                f"Current: {current_plan.upper()}\n"
                f"Status: {'Active' if is_active else 'Inactive'}\n\n"
                f"Plans:\n"
                f"SUBSCRIBE CAPTAIN - N2,500/mo\n"
                f"SUBSCRIBE PREMIUM - N5,000/mo\n"
                f"SUBSCRIBE FREE - Cancel")
        
        plan = command_parts[1].upper()
        
        plan_prices = {
            'CAPTAIN': 2500,
            'PREMIUM': 5000,
            'FREE': 0
        }
        
        if plan not in plan_prices:
            return self.send_sms(phone_number,
                f"Invalid plan: {plan}\n"
                f"Options: CAPTAIN, PREMIUM, FREE")
        
        if plan == 'FREE':
            user.is_premium = False
            user.subscription_plan_code = 'free'
            db.session.commit()
            return self.send_sms(phone_number, "Subscription cancelled. You're now on FREE plan.")
        
        amount = plan_prices[plan]
        balance = wallet_service.get_balance(user)
        
        if balance >= amount:
            success, msg, ref = wallet_service.debit_wallet(
                user, amount,
                f"Subscription: {plan} plan",
                f"SUB_{plan}_{datetime.utcnow().strftime('%Y%m%d')}",
                db_session=db.session
            )
            
            if success:
                user.is_premium = True
                user.subscription_plan_code = plan.lower()
                user.subscription_start_date = datetime.utcnow()
                user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                db.session.commit()
                
                return self.send_sms(phone_number,
                    f"Subscribed to {plan}!\n"
                    f"Amount: N{amount:,.0f}\n"
                    f"Valid: 30 days\n"
                    f"Balance: N{wallet_service.get_balance(user):,.0f}")
            else:
                return self.send_sms(phone_number, f"Subscription failed: {msg}")
        else:
            shortfall = amount - balance
            
            email = user.email if '@sms.' not in user.email else f"sms_{phone_number.replace('+', '')}@tradoja.com"
            ref = payment_service.generate_reference(f"SUB_{plan}")
            
            result = payment_service.charge_ussd(email, amount, ref, '737')
            
            if result.get('success'):
                from models import Transaction
                transaction = Transaction(
                    reference=ref,
                    user_id=user.id,
                    transaction_type='subscription',
                    base_amount=amount,
                    total_amount=amount,
                    payment_method='ussd',
                    status='pending'
                )
                db.session.add(transaction)
                db.session.commit()
                
                return self.send_sms(phone_number,
                    f"Dial to subscribe:\n{result['ussd_code']}\n"
                    f"Amount: N{amount:,.0f}\n"
                    f"Plan: {plan}")
            else:
                return self.send_sms(phone_number,
                    f"Low balance: N{balance:,.0f}\n"
                    f"Need: N{amount:,.0f}\n"
                    f"Top up: TOPUP {shortfall}")
    
    def _handle_transport_settlement(self, phone_number, command_parts):
        """Handle transport trip settlement via SMS
        
        Format: SETTLE [trip_id]
        Examples:
        - SETTLE - View pending settlements
        - SETTLE 123 - Settle specific trip
        """
        from wallet_service import wallet_service
        from models import LogisticsRequest, TransportProfile
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        transport = TransportProfile.query.filter_by(user_id=user.id).first()
        if not transport:
            return self.send_sms(phone_number,
                "Register as transporter first. Dial *712*55# > 6 > 2")
        
        completed_trips = LogisticsRequest.query.filter_by(
            assigned_transport_id=transport.id,
            status='delivered'
        ).filter(LogisticsRequest.payment_status != 'settled').all()
        
        if len(command_parts) < 2:
            if not completed_trips:
                return self.send_sms(phone_number, "No pending settlements.")
            
            lines = ["Pending settlements:"]
            total = 0
            for trip in completed_trips[:5]:
                amount = trip.agreed_price or trip.estimated_cost or 0
                total += amount
                lines.append(f"#{trip.id}: N{amount:,.0f}")
            
            lines.append(f"\nTotal: N{total:,.0f}")
            lines.append(f"SETTLE [id] to claim")
            
            return self.send_sms(phone_number, "\n".join(lines))
        
        try:
            trip_id = int(command_parts[1])
        except ValueError:
            return self.send_sms(phone_number, "Invalid trip ID. Use: SETTLE [number]")
        
        trip = LogisticsRequest.query.filter_by(
            id=trip_id,
            assigned_transport_id=transport.id,
            status='delivered'
        ).first()
        
        if not trip:
            return self.send_sms(phone_number,
                f"Trip #{trip_id} not found or not eligible for settlement.")
        
        if trip.payment_status == 'settled':
            return self.send_sms(phone_number,
                f"Trip #{trip_id} already settled.")
        
        amount = trip.agreed_price or trip.estimated_cost or 0
        platform_fee = amount * 0.05
        net_amount = amount - platform_fee
        
        success, msg, ref = wallet_service.credit_wallet(
            user, net_amount,
            f"Trip #{trip_id} settlement",
            f"SETTLE_{trip_id}_{datetime.utcnow().strftime('%Y%m%d')}",
            db_session=db.session
        )
        
        if success:
            trip.payment_status = 'settled'
            trip.settlement_date = datetime.utcnow()
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"Trip #{trip_id} settled!\n"
                f"Amount: N{amount:,.0f}\n"
                f"Fee: N{platform_fee:,.0f}\n"
                f"Net: N{net_amount:,.0f}\n"
                f"Balance: N{wallet_service.get_balance(user):,.0f}")
        else:
            return self.send_sms(phone_number, f"Settlement failed: {msg}")
    
    def _handle_sabibuy_create(self, phone_number, command_parts):
        """Handle SabiBuy campaign creation via SMS
        
        Format: CREATE SABIBUY [crop] [price] [min_qty]
        Examples:
        - CREATE SABIBUY RICE 48000 50
        - CREATE SABIBUY TOMATO 25000 100
        """
        from wallet_service import wallet_service
        from models import CaptainBond, SabiBuy
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "CREATE SABIBUY [crop] [price] [min_qty]\n"
                "Example: CREATE SABIBUY RICE 48000 50\n"
                "Note: Requires N10,000 Captain bond")
        
        if command_parts[1].upper() != 'SABIBUY':
            return self.send_sms(phone_number,
                "Use: CREATE SABIBUY [crop] [price] [min_qty]")
        
        bond = CaptainBond.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
        
        if not bond:
            return self.send_sms(phone_number,
                "Captain bond required (N10,000).\n"
                "Send: BOND PAY\n"
                "Or dial *712*55# > 15")
        
        if len(command_parts) < 5:
            return self.send_sms(phone_number,
                "Format: CREATE SABIBUY [crop] [price] [min_qty]\n"
                "Example: CREATE SABIBUY RICE 48000 50")
        
        try:
            crop = command_parts[2].upper()
            price = float(command_parts[3])
            min_qty = int(command_parts[4])
        except (ValueError, IndexError):
            return self.send_sms(phone_number,
                "Invalid format.\n"
                "Use: CREATE SABIBUY RICE 48000 50")
        
        if price < 1000 or price > 10000000:
            return self.send_sms(phone_number, "Price must be N1,000 - N10,000,000")
        
        if min_qty < 5 or min_qty > 10000:
            return self.send_sms(phone_number, "Minimum quantity must be 5 - 10,000")
        
        name_part = user.name.split()[0].upper()[:4]
        code = f"{name_part}-SABIBUY-{int(price/1000)}K"
        
        existing = SabiBuy.query.filter_by(campaign_code=code).first()
        counter = 1
        while existing:
            code = f"{name_part}-SABIBUY-{int(price/1000)}K-{counter}"
            existing = SabiBuy.query.filter_by(campaign_code=code).first()
            counter += 1
        
        try:
            campaign = SabiBuy(
                campaign_code=code,
                organizer_id=user.id,
                produce_name=crop,
                unit_price=price,
                minimum_quantity=min_qty,
                current_quantity=0,
                status='active',
                source_channel='sms'
            )
            db.session.add(campaign)
            db.session.commit()
            
            return self.send_sms(phone_number,
                f"SabiBuy created!\n"
                f"Code: {code}\n"
                f"Crop: {crop}\n"
                f"Price: N{price:,.0f}\n"
                f"Min: {min_qty} units\n\n"
                f"Share code with buyers!")
                
        except Exception as e:
            current_app.logger.error(f"SabiBuy create error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number, "Failed to create campaign. Try again.")

    def _handle_order_cancel(self, phone_number, command_parts):
        """Handle order cancellation with refund logic
        
        Format: CANCEL [order_code] [reason]
        Examples:
        - CANCEL ORD-ABC123 changed mind
        - CANCEL ORD-ABC123 buyer not responding
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "To cancel order:\nCANCEL [order-code] [reason]\n"
                "Example: CANCEL ORD-ABC123 buyer unavailable")
        
        order_code = command_parts[1].upper()
        reason = ' '.join(command_parts[2:]) if len(command_parts) > 2 else 'No reason given'
        
        try:
            from models import Order
            
            order = Order.query.filter_by(order_code=order_code).first()
            
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.\n"
                    f"Check code and try again.")
            
            # Check if user is authorized to cancel
            if user.id not in [order.farmer_id, order.buyer_id]:
                return self.send_sms(phone_number,
                    "You can only cancel your own orders.")
            
            # Check if order can be cancelled
            non_cancellable = ['in_transit', 'delivered', 'completed', 'cancelled']
            if order.status in non_cancellable:
                return self.send_sms(phone_number,
                    f"Cannot cancel order in '{order.status}' status.\n"
                    f"Contact support if needed.")
            
            # Cancel the order
            order.status = 'cancelled'
            order.cancelled_at = datetime.utcnow()
            order.cancelled_by_id = user.id
            order.cancellation_reason = reason
            
            # Refund escrow if exists
            refund_msg = ""
            if order.escrow and order.escrow.status == 'held':
                order.escrow.status = 'refunded'
                order.escrow.refund_date = datetime.utcnow()
                refund_msg = "\nPayment will be refunded."
            
            db.session.commit()
            
            # Notify the other party
            other_party = order.buyer if user.id == order.farmer_id else order.farmer
            if other_party and other_party.phone_number:
                self.send_sms(other_party.phone_number,
                    f"Order {order_code} cancelled.\n"
                    f"Reason: {reason[:50]}\n"
                    f"Contact seller for questions.")
            
            return self.send_sms(phone_number,
                f"Order {order_code} cancelled.\n"
                f"Reason: {reason[:30]}...{refund_msg}")
            
        except Exception as e:
            current_app.logger.error(f"Cancel order error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error cancelling order. Try again.")

    def _handle_transporter_jobs(self, phone_number):
        """Show available delivery jobs for transporters
        
        Format: JOBS
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        # Check if user is a transporter
        transport = TransportProfile.query.filter_by(user_id=user.id).first()
        if not transport:
            return self.send_sms(phone_number,
                "You need a transport profile to see jobs.\n"
                "Register at tradoja.com or contact agent.")
        
        try:
            # Find orders needing transport in user's area
            available_orders = Order.query.filter(
                Order.status.in_(['accepted', 'pending']),
                Order.transporter_id.is_(None)
            ).limit(5).all()
            
            if not available_orders:
                return self.send_sms(phone_number,
                    "No delivery jobs available now.\n"
                    "Check back later or send JOBS again.")
            
            jobs_text = "Available jobs:\n\n"
            for order in available_orders:
                produce_name = order.produce.crop_type if order.produce else "Goods"
                jobs_text += (
                    f"{order.order_code}\n"
                    f"{produce_name} - {order.quantity}kg\n"
                    f"To claim: CLAIM {order.order_code}\n\n"
                )
            
            return self.send_sms(phone_number, jobs_text.strip())
            
        except Exception as e:
            current_app.logger.error(f"Jobs listing error: {e}")
            return self.send_sms(phone_number,
                "Error loading jobs. Try again.")

    def _handle_claim_job(self, phone_number, command_parts):
        """Transporter claims a delivery job
        
        Format: CLAIM [order_code]
        Example: CLAIM ORD-ABC123
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        transport = TransportProfile.query.filter_by(user_id=user.id).first()
        if not transport:
            return self.send_sms(phone_number,
                "You need a transport profile to claim jobs.\n"
                "Register at tradoja.com or contact agent.")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "To claim job:\nCLAIM [order-code]\n"
                "Example: CLAIM ORD-ABC123\n"
                "Send JOBS to see available jobs.")
        
        order_code = command_parts[1].upper()
        
        try:
            order = Order.query.filter_by(order_code=order_code).first()
            
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            if order.transporter_id:
                return self.send_sms(phone_number,
                    f"Order {order_code} already claimed.\n"
                    f"Send JOBS for other available jobs.")
            
            if order.status not in ['accepted', 'pending']:
                return self.send_sms(phone_number,
                    f"Cannot claim order in '{order.status}' status.")
            
            # Assign transporter
            order.transporter_id = user.id
            order.transport_claimed_at = datetime.utcnow()
            db.session.commit()
            
            # Get pickup details
            farmer = order.farmer
            pickup_location = farmer.location if farmer else "Contact farmer"
            farmer_phone = farmer.phone_number if farmer else "N/A"
            
            # Notify farmer
            if farmer and farmer.phone_number:
                self.send_sms(farmer.phone_number,
                    f"Transporter assigned for {order_code}!\n"
                    f"Name: {user.farm_name or user.username}\n"
                    f"Phone: {phone_number}\n"
                    f"Prepare goods for pickup.")
            
            return self.send_sms(phone_number,
                f"Job claimed: {order_code}\n\n"
                f"Pickup from: {pickup_location}\n"
                f"Farmer: {farmer_phone}\n\n"
                f"After pickup send:\n"
                f"LOCATION {order_code} [area]")
            
        except Exception as e:
            current_app.logger.error(f"Claim job error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error claiming job. Try again.")

    def _handle_vouch_farmer(self, phone_number, command_parts):
        """Community vouching - established farmers vouch for new farmers
        
        Format: VOUCH [phone_number]
        Example: VOUCH 08012345678
        
        Requires 3 vouches from verified farmers for new farmer to become trusted.
        """
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return self.send_sms(phone_number,
                "Register first. Send: JOIN [name] [location] [crop]")
        
        # Check if voucher is a verified farmer
        if user.role != 'farmer' or user.verification_level != 'verified':
            return self.send_sms(phone_number,
                "Only verified farmers can vouch.\n"
                "Complete verification at tradoja.com first.")
        
        if len(command_parts) < 2:
            return self.send_sms(phone_number,
                "To vouch for a farmer:\nVOUCH [phone]\n"
                "Example: VOUCH 08012345678")
        
        target_phone = command_parts[1]
        # Normalize phone number
        if target_phone.startswith('0'):
            target_phone = '+234' + target_phone[1:]
        elif not target_phone.startswith('+'):
            target_phone = '+234' + target_phone
        
        try:
            from models import FarmerVouch
            
            target_user = User.query.filter_by(phone_number=target_phone).first()
            
            if not target_user:
                return self.send_sms(phone_number,
                    f"Farmer with {target_phone} not found.\n"
                    f"They must register first.")
            
            if target_user.id == user.id:
                return self.send_sms(phone_number,
                    "You cannot vouch for yourself.")
            
            if target_user.verification_level == 'verified':
                return self.send_sms(phone_number,
                    f"{target_user.farm_name or target_user.username} is already verified.")
            
            # Check if already vouched
            existing_vouch = FarmerVouch.query.filter_by(
                voucher_id=user.id,
                farmer_id=target_user.id
            ).first()
            
            if existing_vouch:
                return self.send_sms(phone_number,
                    f"You already vouched for this farmer.")
            
            # Add vouch
            vouch = FarmerVouch(
                voucher_id=user.id,
                farmer_id=target_user.id,
                vouched_at=datetime.utcnow()
            )
            db.session.add(vouch)
            
            # Count vouches
            vouch_count = FarmerVouch.query.filter_by(farmer_id=target_user.id).count() + 1
            
            # Auto-verify if 3 vouches received
            if vouch_count >= 3:
                target_user.verification_level = 'verified'
                target_user.verified_at = datetime.utcnow()
                target_user.verification_method = 'community_vouch'
                
                db.session.commit()
                
                # Notify the verified farmer
                if target_user.phone_number:
                    self.send_sms(target_user.phone_number,
                        f"Congratulations! You are now VERIFIED.\n"
                        f"3 farmers vouched for you.\n"
                        f"You can now access premium features.")
                
                return self.send_sms(phone_number,
                    f"Vouch recorded! {target_user.farm_name or target_user.username} "
                    f"is now VERIFIED (3/3 vouches).")
            else:
                db.session.commit()
                remaining = 3 - vouch_count
                
                return self.send_sms(phone_number,
                    f"Vouch recorded for {target_user.farm_name or target_user.username}.\n"
                    f"{vouch_count}/3 vouches. {remaining} more needed.")
            
        except Exception as e:
            current_app.logger.error(f"Vouch error: {e}")
            db.session.rollback()
            return self.send_sms(phone_number,
                "Error recording vouch. Try again.")

    def _try_ai_parse(self, phone_number, original_message, command_parts):
        """Try AI natural language parsing when command not recognized"""
        try:
            from services.ai_trading_service import ai_trading_service
            
            result = ai_trading_service.parse_natural_language(original_message, phone_number)
            
            # Validate command is in whitelist
            valid_commands = {'SELL', 'PRICE', 'TRACK', 'ACCEPT', 'CANCEL', 'BAL', 'BALANCE', 'STATUS', 'HELP', 'JOBS', 'VOUCH', 'TRACE', 'QUALITY'}
            
            if result.get('confidence', 0) >= 0.7 and result.get('command'):
                command = result['command'].upper()
                
                # Reject if not in whitelist
                if command not in valid_commands:
                    return self._send_invalid_command_message(phone_number)
                
                params = result.get('params', [])
                
                new_parts = [command] + [str(p).upper() for p in params]
                
                if command == 'SELL':
                    return self._handle_produce_listing(phone_number, new_parts)
                elif command == 'PRICE':
                    return self._handle_price_check(phone_number, new_parts)
                elif command == 'TRACK':
                    return self._handle_order_tracking(phone_number, new_parts)
                elif command == 'BAL' or command == 'BALANCE':
                    return self._handle_balance_check(phone_number)
                elif command == 'STATUS':
                    return self._handle_status_check(phone_number, new_parts)
                elif command == 'HELP':
                    return self._send_help_message(phone_number)
                elif command == 'ACCEPT':
                    return self._handle_order_acceptance(phone_number, new_parts)
                elif command == 'CANCEL':
                    return self._handle_order_cancel(phone_number, new_parts)
                elif command == 'JOBS':
                    return self._handle_view_jobs(phone_number)
                else:
                    return self.send_sms(phone_number,
                        f"I understood: {result.get('original_intent', 'your request')}\n"
                        f"Try: {command} {' '.join(str(p) for p in params)}")
            else:
                return self._send_invalid_command_message(phone_number)
                
        except Exception as e:
            current_app.logger.error(f"AI parse fallback error: {e}")
            return self._send_invalid_command_message(phone_number)
    
    def _handle_ai_command(self, phone_number, command_parts, original_message):
        """Handle explicit AI command - parse natural language"""
        try:
            from services.ai_trading_service import ai_trading_service
            
            if len(command_parts) < 2:
                return self.send_sms(phone_number,
                    "AI can help! Just type what you want.\n"
                    "Example: AI I want to sell 50kg tomatoes")
            
            user_message = ' '.join(command_parts[1:])
            result = ai_trading_service.parse_natural_language(user_message, phone_number)
            
            if result.get('confidence', 0) >= 0.5 and result.get('command'):
                cmd = result['command']
                params = ' '.join(str(p) for p in result.get('params', []))
                intent = result.get('original_intent', '')[:40]
                
                return self.send_sms(phone_number,
                    f"AI understood: {intent}\n"
                    f"Command: {cmd} {params}\n"
                    f"Send this command to proceed.")
            else:
                return self.send_sms(phone_number,
                    "I couldn't understand that.\n"
                    "Try: AI sell 50kg tomatoes for 15000\n"
                    "Or send HELP for commands.")
                
        except Exception as e:
            current_app.logger.error(f"AI command error: {e}")
            return self.send_sms(phone_number,
                "AI service temporarily unavailable.\nSend HELP for commands.")
    
    def _handle_price_advice(self, phone_number, command_parts):
        """Get AI-powered price advice for a crop"""
        try:
            from services.ai_trading_service import ai_trading_service
            
            user = User.query.filter_by(phone_number=phone_number).first()
            if not user:
                return self.send_sms(phone_number,
                    "Register first. Send: JOIN [name] [location] [crop]")
            
            if len(command_parts) < 2:
                return self.send_sms(phone_number,
                    "Get AI price advice:\nADVICE [crop] [quantity]\n"
                    "Example: ADVICE tomatoes 100")
            
            crop = command_parts[1]
            quantity = float(command_parts[2]) if len(command_parts) > 2 else 50
            location = user.location if hasattr(user, 'location') else None
            
            result = ai_trading_service.get_price_advice(crop, quantity, location)
            response = ai_trading_service.format_sms_response(result, 'price_advice')
            
            return self.send_sms(phone_number, response)
            
        except Exception as e:
            current_app.logger.error(f"Price advice error: {e}")
            return self.send_sms(phone_number,
                "Price advice unavailable. Try: PRICE [crop]")
    
    def _handle_risk_check(self, phone_number, command_parts):
        """Check AI risk score for an order"""
        try:
            from services.ai_trading_service import ai_trading_service
            from models import Order
            
            user = User.query.filter_by(phone_number=phone_number).first()
            if not user:
                return self.send_sms(phone_number,
                    "Register first. Send: JOIN [name] [location] [crop]")
            
            if len(command_parts) < 2:
                return self.send_sms(phone_number,
                    "Check order risk:\nRISK [order-code]\n"
                    "Example: RISK ORD-ABC123")
            
            order_code = command_parts[1].upper()
            order = Order.query.filter_by(order_code=order_code).first()
            
            if not order:
                return self.send_sms(phone_number,
                    f"Order {order_code} not found.")
            
            if user.id not in [order.farmer_id, order.buyer_id]:
                return self.send_sms(phone_number,
                    "You can only check risk for your orders.")
            
            result = ai_trading_service.score_escrow_risk(order.id)
            response = ai_trading_service.format_sms_response(result, 'risk_score')
            
            return self.send_sms(phone_number, response)
            
        except Exception as e:
            current_app.logger.error(f"Risk check error: {e}")
            return self.send_sms(phone_number,
                "Risk check unavailable. Contact support.")

    def _handle_trace_command(self, phone_number, command_parts):
        """View blockchain traceability history for produce
        
        Format: TRACE [chain-code or order-code]
        Examples:
        - TRACE CHN-ABC123
        - TRACE ORD-XYZ789
        """
        try:
            from services.traceability_service import traceability_service
            from models import Order, TraceChain
            
            user = User.query.filter_by(phone_number=phone_number).first()
            if not user:
                return self.send_sms(phone_number,
                    "Register first. Send: JOIN [name] [location] [crop]")
            
            if len(command_parts) < 2:
                return self.send_sms(phone_number,
                    "View produce journey:\nTRACE [code]\n"
                    "Example: TRACE CHN-ABC123\n"
                    "Or: TRACE ORD-XYZ789")
            
            code = command_parts[1].upper()
            
            if code.startswith('ORD-'):
                order = Order.query.filter_by(order_code=code).first()
                if not order:
                    return self.send_sms(phone_number, f"Order {code} not found.")
                
                chain = TraceChain.query.filter_by(produce_id=order.produce_id).first()
                if not chain:
                    return self.send_sms(phone_number,
                        f"No trace chain for {code}.\n"
                        f"Traceability starts when order is accepted.")
                code = chain.chain_code
            
            history = traceability_service.format_sms_history(code)
            return self.send_sms(phone_number, history)
            
        except Exception as e:
            current_app.logger.error(f"Trace command error: {e}")
            return self.send_sms(phone_number,
                "Trace lookup failed. Try again.")

    def _handle_quality_check(self, phone_number, command_parts):
        """Record quality check event in traceability chain
        
        Format: QUALITY [order-code] [grade] [notes]
        Examples:
        - QUALITY ORD-ABC123 A Fresh and ripe
        - QUALITY ORD-ABC123 B Minor bruising
        """
        try:
            from services.traceability_service import traceability_service
            from models import Order, TraceChain
            
            user = User.query.filter_by(phone_number=phone_number).first()
            if not user:
                return self.send_sms(phone_number,
                    "Register first. Send: JOIN [name] [location] [crop]")
            
            if len(command_parts) < 3:
                return self.send_sms(phone_number,
                    "Record quality check:\nQUALITY [order] [A/B/C] [notes]\n"
                    "Example: QUALITY ORD-123 A Fresh produce")
            
            order_code = command_parts[1].upper()
            grade = command_parts[2].upper()
            notes = ' '.join(command_parts[3:]) if len(command_parts) > 3 else ''
            
            if grade not in ['A', 'B', 'C', 'PREMIUM', 'STANDARD', 'ECONOMY']:
                return self.send_sms(phone_number,
                    "Grade must be A, B, or C\n"
                    "(or PREMIUM, STANDARD, ECONOMY)")
            
            order = Order.query.filter_by(order_code=order_code).first()
            if not order:
                return self.send_sms(phone_number, f"Order {order_code} not found.")
            
            if user.id not in [order.farmer_id, order.buyer_id, order.transporter_id]:
                return self.send_sms(phone_number,
                    "You can only record quality for your orders.")
            
            role = 'farmer' if user.id == order.farmer_id else (
                'buyer' if user.id == order.buyer_id else 'transporter')
            
            location = user.location if hasattr(user, 'location') else 'Unknown'
            
            result = traceability_service.record_order_events(
                order_id=order.id,
                event_type='quality_check',
                user_id=user.id,
                role=role,
                location=location,
                source_channel='sms'
            )
            
            if hasattr(result, '__getitem__') and result.get('success'):
                chain_code = result.get('chain_code', '')
                return self.send_sms(phone_number,
                    f"Quality recorded for {order_code}!\n"
                    f"Grade: {grade}\n"
                    f"Chain: {chain_code}\n"
                    f"View: TRACE {chain_code}")
            else:
                return self.send_sms(phone_number,
                    f"Quality check recorded.\n"
                    f"Grade: {grade}")
            
        except Exception as e:
            current_app.logger.error(f"Quality check error: {e}")
            return self.send_sms(phone_number,
                "Quality recording failed. Try again.")


# SMS Templates for future multilingual support
SMS_TEMPLATES = {
    'en': {
        'welcome': "Welcome to Tradoja! 🌾 Reply with: JOIN [name] [location] [crop]",
        'registration_success': "Welcome {name}! You're registered for {crop} in {location}.",
        'invalid_format': "Invalid format. Send HELP for commands.",
        'help': "Commands: JOIN, LIST, PRICE, TRACK, RATE, COMPLAINT, STATUS, HELP, STOP",
    },
    # Future: Yoruba, Hausa, Pidgin templates
}

# Create singleton instance
import os
sms_service = SMSService(
    username=os.environ.get('AFRICASTALKING_USERNAME', 'sandbox'),
    api_key=os.environ.get('AFRICASTALKING_API_KEY', '')
)