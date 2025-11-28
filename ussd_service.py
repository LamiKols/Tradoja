"""
USSD Service for AgroLink
Supports Africa's Talking and T2 (9mobile) USSD channels
Enables feature phone users to access the platform without internet
"""

import re
import logging
import json
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from flask import current_app
from multilingual_service import get_message, detect_language

logger = logging.getLogger(__name__)


class USSDService:
    """USSD service for Africa's Talking and T2 platforms"""
    
    SERVICE_CODE = '*712*55#'
    
    # Menu structure definitions
    MENUS = {
        'main': {
            'options': {
                '1': 'list_produce',
                '2': 'check_prices',
                '3': 'my_listings',
                '4': 'balance',
                '5': 'register',
                '6': 'transport_jobs'
            }
        },
        'list_produce': {
            'steps': ['crop_name', 'quantity', 'price', 'confirm'],
            'next': 'main'
        },
        'check_prices': {
            'steps': ['crop_name'],
            'next': 'main'
        },
        'my_listings': {
            'steps': [],
            'next': 'main'
        },
        'balance': {
            'steps': [],
            'next': 'main'
        },
        'register': {
            'steps': ['name', 'location', 'crop'],
            'next': 'main'
        },
        'transport_jobs': {
            'options': {
                '1': 'new_jobs',
                '2': 'register_transporter',
                '3': 'my_bids',
                '4': 'active_trips',
                '5': 'transport_balance'
            },
            'next': 'main'
        },
        'register_transporter': {
            'steps': ['company_name', 'location', 'vehicle_type'],
            'next': 'transport_jobs'
        },
        'new_jobs': {
            'steps': ['view_job', 'bid_amount', 'confirm_bid'],
            'next': 'transport_jobs'
        },
        'my_bids': {
            'steps': [],
            'next': 'transport_jobs'
        },
        'active_trips': {
            'steps': ['view_trip', 'start_trip'],
            'next': 'transport_jobs'
        },
        'transport_balance': {
            'steps': [],
            'next': 'transport_jobs'
        }
    }
    
    def __init__(self):
        """Initialize USSD service"""
        self.db = None
        self.User = None
        self.USSDSession = None
        self.Produce = None
    
    def _lazy_load_models(self):
        """Lazy load database models to avoid circular imports"""
        if self.db is None:
            from app import db
            from models import User, USSDSession, Produce, TransportProfile, LogisticsRequest, LogisticsBid
            self.db = db
            self.User = User
            self.USSDSession = USSDSession
            self.Produce = Produce
            self.TransportProfile = TransportProfile
            self.LogisticsRequest = LogisticsRequest
            self.LogisticsBid = LogisticsBid
    
    def process_request(
        self, 
        session_id: str, 
        phone_number: str, 
        text: str,
        service_code: str = None,
        provider: str = 'africastalking'
    ) -> Tuple[str, bool]:
        """
        Process a USSD request and return response
        
        Args:
            session_id: Unique session identifier
            phone_number: User's phone number
            text: User input (empty for initial request, or cumulative input)
            service_code: USSD service code dialed
            provider: 'africastalking' or 't2'
            
        Returns:
            Tuple of (response_text, should_continue)
            should_continue: True = CON (continue), False = END (end session)
        """
        self._lazy_load_models()
        
        try:
            # Normalize phone number
            phone_number = self._normalize_phone(phone_number)
            
            # Get or create session
            session = self._get_or_create_session(
                session_id, phone_number, service_code, provider
            )
            
            # Get user if exists
            user = self.User.query.filter_by(phone_number=phone_number).first()
            if user:
                session.user_id = user.id
                session.is_authenticated = True
            
            # Parse the USSD input chain
            inputs = text.split('*') if text else []
            
            # Determine current state and process
            response, should_continue = self._handle_menu_navigation(
                session, inputs, user
            )
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            self.db.session.commit()
            
            return response, should_continue
            
        except Exception as e:
            logger.error(f"USSD processing error: {e}")
            return get_message('error', 'en'), False
    
    def _get_or_create_session(
        self, 
        session_id: str, 
        phone_number: str,
        service_code: str,
        provider: str
    ):
        """Get existing session or create new one"""
        session = self.USSDSession.query.filter_by(session_id=session_id).first()
        
        if not session:
            session = self.USSDSession(
                session_id=session_id,
                phone_number=phone_number,
                service_code=service_code or self.SERVICE_CODE,
                provider=provider,
                current_menu='main',
                current_step=0
            )
            self.db.session.add(session)
            self.db.session.commit()
        
        return session
    
    def _handle_menu_navigation(
        self, 
        session, 
        inputs: list, 
        user
    ) -> Tuple[str, bool]:
        """Handle menu navigation based on user inputs"""
        
        # Get user's preferred language or detect from session
        lang = user.preferred_language if user else 'en'
        
        # Initial request (no input yet)
        if not inputs or (len(inputs) == 1 and inputs[0] == ''):
            return self._show_main_menu(lang, user), True
        
        current_input = inputs[-1] if inputs else ''
        
        # Handle based on current menu state
        if session.current_menu == 'main':
            return self._handle_main_menu_selection(session, current_input, user, lang)
        
        elif session.current_menu == 'list_produce':
            return self._handle_list_produce(session, current_input, user, lang)
        
        elif session.current_menu == 'check_prices':
            return self._handle_check_prices(session, current_input, user, lang)
        
        elif session.current_menu == 'my_listings':
            return self._show_my_listings(session, user, lang)
        
        elif session.current_menu == 'balance':
            return self._show_balance(session, user, lang)
        
        elif session.current_menu == 'register':
            return self._handle_registration(session, current_input, user, lang)
        
        elif session.current_menu == 'transport_jobs':
            return self._handle_transport_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'new_jobs':
            return self._handle_new_jobs(session, current_input, user, lang)
        
        elif session.current_menu == 'my_bids':
            return self._show_my_bids(session, user, lang)
        
        elif session.current_menu == 'active_trips':
            return self._handle_active_trips(session, current_input, user, lang)
        
        elif session.current_menu == 'register_transporter':
            return self._handle_register_transporter(session, current_input, user, lang)
        
        elif session.current_menu == 'transport_balance':
            return self._show_transport_balance(session, user, lang)
        
        else:
            return self._show_main_menu(lang, user), True
    
    def _show_main_menu(self, lang: str, user) -> str:
        """Show the main USSD menu"""
        if user:
            welcome = get_message('welcome_back', lang, name=user.name.split()[0])
        else:
            welcome = get_message('ussd_welcome', lang)
        
        menu = get_message('ussd_main_menu', lang)
        return f"{welcome}\n{menu}"
    
    def _handle_main_menu_selection(
        self, 
        session, 
        selection: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle selection from main menu"""
        
        menu_map = self.MENUS['main']['options']
        
        if selection in menu_map:
            target_menu = menu_map[selection]
            session.current_menu = target_menu
            session.current_step = 0
            session.set_session_data({})
            
            if target_menu == 'list_produce':
                if not user:
                    session.current_menu = 'register'
                    return get_message('register_prompt', lang), True
                return get_message('list_prompt', lang), True
            
            elif target_menu == 'check_prices':
                return get_message('price_prompt', lang), True
            
            elif target_menu == 'my_listings':
                return self._show_my_listings(session, user, lang)
            
            elif target_menu == 'balance':
                return self._show_balance(session, user, lang)
            
            elif target_menu == 'register':
                if user:
                    return get_message('already_registered', lang), False
                return "Enter your name:", True
            
            elif target_menu == 'transport_jobs':
                return self._show_transport_menu(session, user, lang)
        
        return get_message('invalid_command', lang), True
    
    def _handle_list_produce(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle produce listing flow (3-step)"""
        
        if not user:
            session.current_menu = 'register'
            return get_message('register_prompt', lang), True
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            # Step 1: Crop name
            data['crop_name'] = user_input.strip().title()
            session.update_session_data('crop_name', data['crop_name'])
            session.current_step = 1
            return "Enter quantity (e.g., 50BAGS, 100KG, 5TONS):", True
        
        elif step == 1:
            # Step 2: Quantity
            quantity = self._parse_quantity(user_input)
            if not quantity:
                return "Invalid format. Use: 50BAGS, 100KG, or 5TONS:", True
            
            data['quantity'] = user_input.strip().upper()
            data['quantity_display'] = user_input.strip()
            session.update_session_data('quantity', data['quantity'])
            session.current_step = 2
            return "Enter price in Naira (e.g., 150000):", True
        
        elif step == 2:
            # Step 3: Price
            try:
                price = float(re.sub(r'[^\d.]', '', user_input))
                data['price'] = price
                session.update_session_data('price', price)
                session.current_step = 3
                
                # Confirmation
                crop = data.get('crop_name', 'Produce')
                qty = data.get('quantity', 'N/A')
                confirm_msg = f"Confirm listing:\n{qty} {crop}\nPrice: ₦{price:,.0f}\n\n1. Confirm\n2. Cancel"
                return confirm_msg, True
                
            except ValueError:
                return "Invalid price. Enter numbers only (e.g., 150000):", True
        
        elif step == 3:
            # Confirmation step
            if user_input == '1':
                # Create the listing
                return self._create_produce_listing(session, user, data, lang)
            else:
                session.current_menu = 'main'
                session.current_step = 0
                return "Listing cancelled.\n" + self._show_main_menu(lang, user), True
        
        return get_message('error', lang), False
    
    def _create_produce_listing(
        self, 
        session, 
        user, 
        data: dict, 
        lang: str
    ) -> Tuple[str, bool]:
        """Create a produce listing from USSD data"""
        try:
            from models import Produce
            
            produce = Produce(
                farmer_id=user.id,
                name=data.get('crop_name', 'Unknown'),
                quantity=data.get('quantity', '1'),
                price=data.get('price', 0),
                price_unit='NGN',
                description=f"Listed via USSD by {user.name}",
                contact_method='ussd',
                source_channel='ussd',
                listing_location=user.location or 'Unknown'
            )
            
            self.db.session.add(produce)
            self.db.session.commit()
            
            # Reset session
            session.current_menu = 'main'
            session.current_step = 0
            
            success_msg = get_message(
                'list_success', lang,
                quantity=data.get('quantity', ''),
                crop=data.get('crop_name', ''),
                price=f"{data.get('price', 0):,.0f}"
            )
            
            return success_msg, False
            
        except Exception as e:
            logger.error(f"Error creating USSD listing: {e}")
            return get_message('list_fail', lang), False
    
    def _handle_check_prices(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle price check flow"""
        from models import Produce
        from sqlalchemy import func
        
        crop_name = user_input.strip().title()
        
        # Query for produce with similar name
        produces = Produce.query.filter(
            Produce.name.ilike(f'%{crop_name}%'),
            Produce.is_available == True
        ).all()
        
        if not produces:
            session.current_menu = 'main'
            return get_message('no_price_data', lang, crop=crop_name), False
        
        # Calculate price statistics
        prices = [p.price for p in produces if p.price]
        if not prices:
            session.current_menu = 'main'
            return get_message('no_price_data', lang, crop=crop_name), False
        
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        session.current_menu = 'main'
        
        price_msg = get_message(
            'price_result', lang,
            crop=crop_name,
            avg=f"{avg_price:,.0f}",
            min=f"{min_price:,.0f}",
            max=f"{max_price:,.0f}"
        )
        
        return price_msg, False
    
    def _show_my_listings(
        self, 
        session, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Show user's active listings"""
        from models import Produce
        
        if not user:
            session.current_menu = 'register'
            return get_message('register_prompt', lang), True
        
        listings = Produce.query.filter_by(
            farmer_id=user.id,
            is_available=True
        ).limit(5).all()
        
        if not listings:
            session.current_menu = 'main'
            return get_message('no_listings', lang), False
        
        response = get_message('listings_header', lang) + "\n"
        for i, listing in enumerate(listings, 1):
            response += get_message(
                'listing_item', lang,
                num=i,
                crop=listing.name,
                quantity=listing.quantity,
                price=f"{listing.price:,.0f}"
            ) + "\n"
        
        session.current_menu = 'main'
        return response.strip(), False
    
    def _show_balance(
        self, 
        session, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Show user's balance information"""
        
        if not user:
            session.current_menu = 'register'
            return get_message('register_prompt', lang), True
        
        t2_balance = user.t2_wallet_balance or 0
        paystack_status = "Connected" if user.paystack_customer_code else "Not setup"
        
        balance_msg = get_message(
            'balance', lang,
            t2_balance=f"{t2_balance:,.2f}",
            paystack_status=paystack_status
        )
        
        session.current_menu = 'main'
        return balance_msg, False
    
    def _handle_registration(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle user registration flow (3-step)"""
        from werkzeug.security import generate_password_hash
        
        if user:
            session.current_menu = 'main'
            return get_message('already_registered', lang), False
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            # Step 1: Name
            data['name'] = user_input.strip().title()
            session.update_session_data('name', data['name'])
            session.current_step = 1
            return "Enter your location (town/city):", True
        
        elif step == 1:
            # Step 2: Location
            data['location'] = user_input.strip().title()
            session.update_session_data('location', data['location'])
            session.current_step = 2
            return "Enter your main crop (e.g., Rice, Yam, Tomatoes):", True
        
        elif step == 2:
            # Step 3: Main crop and complete registration
            data['main_crop'] = user_input.strip().title()
            
            try:
                # Create user account
                new_user = self.User(
                    name=data['name'],
                    phone_number=session.phone_number,
                    email=f"{session.phone_number.replace('+', '')}@ussd.agrolink.com",
                    role='farmer',
                    location=data['location'],
                    is_ussd_user=True,
                    preferred_language=lang,
                    sms_enabled=True,
                    sms_registration_date=datetime.utcnow()
                )
                new_user.password_hash = generate_password_hash('ussd_user_temp')
                
                self.db.session.add(new_user)
                self.db.session.commit()
                
                # Update session
                session.user_id = new_user.id
                session.is_authenticated = True
                session.current_menu = 'main'
                session.current_step = 0
                
                success_msg = get_message('registration_success', lang)
                return success_msg, False
                
            except Exception as e:
                logger.error(f"USSD registration error: {e}")
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _show_transport_menu(
        self,
        session,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Show transport jobs menu"""
        
        # Check if user is a transporter
        profile = None
        if user:
            profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        
        menu = get_message('transport_menu', lang)
        
        return menu, True
    
    def _handle_transport_menu(
        self,
        session,
        selection: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle transport menu selection"""
        
        if selection == '0':
            session.current_menu = 'main'
            session.current_step = 0
            return self._show_main_menu(lang, user), True
        
        menu_map = self.MENUS['transport_jobs'].get('options', {})
        
        if selection in menu_map:
            target = menu_map[selection]
            session.current_menu = target
            session.current_step = 0
            session.set_session_data({})
            
            if target == 'new_jobs':
                if not user or not self.TransportProfile.query.filter_by(user_id=user.id).first():
                    return get_message('register_transporter_first', lang), True
                return self._show_available_jobs(session, user, lang)
            elif target == 'register_transporter':
                if user:
                    profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
                    if profile:
                        return get_message('already_transporter', lang, transporter_id=profile.transporter_id or 'TRK-XXXXX'), False
                return get_message('register_transporter_name', lang), True
            elif target == 'my_bids':
                if not user or not self.TransportProfile.query.filter_by(user_id=user.id).first():
                    return get_message('register_transporter_first', lang), True
                return self._show_my_bids(session, user, lang)
            elif target == 'active_trips':
                if not user or not self.TransportProfile.query.filter_by(user_id=user.id).first():
                    return get_message('register_transporter_first', lang), True
                return self._show_active_trips(session, user, lang)
            elif target == 'transport_balance':
                if not user or not self.TransportProfile.query.filter_by(user_id=user.id).first():
                    return get_message('register_transporter_first', lang), True
                return self._show_transport_balance(session, user, lang)
        
        return get_message('invalid_command', lang), True
    
    def _show_transport_balance(
        self,
        session,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Show transporter wallet balance"""
        profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return get_message('register_transporter_first', lang), True
        
        balance = profile.wallet_balance or 0.0
        msg = get_message('transport_balance', lang, balance=f"{balance:,.0f}", transporter_id=profile.transporter_id or 'N/A')
        session.current_menu = 'transport_jobs'
        return msg, False
    
    def _handle_register_transporter(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle 3-step transporter LITE registration via USSD"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            data['company_name'] = user_input.strip().title()
            session.update_session_data('company_name', data['company_name'])
            session.current_step = 1
            return get_message('register_transporter_location', lang), True
        
        elif step == 1:
            data['location'] = user_input.strip().title()
            session.update_session_data('location', data['location'])
            session.current_step = 2
            return get_message('register_transporter_vehicle', lang), True
        
        elif step == 2:
            vehicle_map = {
                '1': ('pickup', 'Pickup/Motorcycle', False),
                '2': ('medium_truck', '5-10 Ton Truck', False),
                '3': ('large_truck', '15-30 Ton Truck', False),
                '4': ('refrigerated', 'Refrigerated/Cold Truck', True)
            }
            
            if user_input not in vehicle_map:
                return get_message('register_transporter_vehicle', lang), True
            
            vehicle_type, vehicle_display, is_cold_chain = vehicle_map[user_input]
            
            company_name = data.get('company_name')
            location = data.get('location')
            
            if not company_name or not location:
                session.current_menu = 'transport_jobs'
                session.current_step = 0
                return "Session expired. Please try again.\nDial *712*55# > 6 > 2", False
            
            try:
                from werkzeug.security import generate_password_hash
                
                phone = session.phone_number
                
                if user:
                    new_user = user
                    if new_user.role != 'transport_company':
                        new_user.role = 'transport_company'
                else:
                    new_user = self.User(
                        name=company_name,
                        phone_number=phone,
                        email=f"{phone.replace('+', '').replace('-', '')}@transport.agrolink.ng",
                        role='transport_company',
                        is_ussd_user=True,
                        source_channel='ussd',
                        preferred_language=lang,
                        location=location
                    )
                    new_user.password_hash = generate_password_hash('ussd_transporter_temp')
                    self.db.session.add(new_user)
                    self.db.session.flush()
                
                transporter_id = self.TransportProfile.generate_transporter_id()
                
                profile = self.TransportProfile(
                    user_id=new_user.id,
                    company_name=company_name,
                    main_location=location,
                    vehicle_types=json.dumps([vehicle_type]),
                    cold_chain_capable=is_cold_chain,
                    profile_complete=False,
                    registration_channel='ussd_lite',
                    transporter_id=transporter_id,
                    routes_covered=json.dumps([[location]])
                )
                
                self.db.session.add(profile)
                self.db.session.commit()
                
                session.current_menu = 'transport_jobs'
                session.current_step = 0
                session.set_session_data({})
                
                return get_message('register_transporter_success', lang, 
                                  transporter_id=transporter_id, 
                                  name=company_name), False
                
            except Exception as e:
                logger.error(f"USSD transport registration error: {e}")
                self.db.session.rollback()
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _show_available_jobs(
        self,
        session,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Show available transport jobs"""
        
        profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            session.current_menu = 'main'
            return "Not a registered transporter.", False
        
        # Get available jobs
        jobs = self.LogisticsRequest.query.filter(
            self.LogisticsRequest.status.in_(['pending', 'bidding'])
        ).order_by(self.LogisticsRequest.timestamp.desc()).limit(5).all()
        
        if not jobs:
            session.current_menu = 'transport_jobs'
            return "No jobs available now.\nCheck back later.", False
        
        response = "AVAILABLE JOBS:\n"
        job_ids = []
        for i, job in enumerate(jobs, 1):
            cc = "[CC]" if job.requires_cold_chain else ""
            route = f"{job.pickup_state or 'N/A'}->{job.destination_state or 'N/A'}"
            response += f"{i}. {route} {job.quantity_tons or 'N/A'}T {cc}\n"
            job_ids.append(job.id)
        
        response += "\nEnter job number to bid:"
        
        # Store job IDs in session for later reference
        session.update_session_data('job_ids', job_ids)
        session.current_step = 1
        
        return response, True
    
    def _handle_new_jobs(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle new jobs selection and bidding"""
        
        data = session.get_session_data()
        step = session.current_step
        
        profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            session.current_menu = 'main'
            return "Not a registered transporter.", False
        
        if step == 0:
            # Initial view - show jobs
            return self._show_available_jobs(session, user, lang)
        
        elif step == 1:
            # Job selection
            try:
                job_index = int(user_input) - 1
                job_ids = data.get('job_ids', [])
                
                if 0 <= job_index < len(job_ids):
                    job_id = job_ids[job_index]
                    job = self.LogisticsRequest.query.get(job_id)
                    
                    if job:
                        session.update_session_data('selected_job_id', job_id)
                        session.current_step = 2
                        
                        # Show job details
                        cc = "Yes" if job.requires_cold_chain else "No"
                        details = f"JOB #{job.id}\n"
                        details += f"From: {job.pickup_state or 'N/A'}\n"
                        details += f"To: {job.destination_state or 'N/A'}\n"
                        details += f"Weight: {job.quantity_tons or 'N/A'}T\n"
                        details += f"Cold Chain: {cc}\n\n"
                        details += "Enter bid amount (₦):"
                        
                        return details, True
                
                return "Invalid selection. Try again:", True
                
            except ValueError:
                return "Enter a number:", True
        
        elif step == 2:
            # Bid amount
            try:
                bid_amount = float(re.sub(r'[^\d.]', '', user_input))
                if bid_amount < 1000:
                    return "Minimum bid is ₦1,000:", True
                
                session.update_session_data('bid_amount', bid_amount)
                session.current_step = 3
                
                job_id = data.get('selected_job_id')
                confirm = f"Confirm bid of ₦{bid_amount:,.0f}\nfor Job #{job_id}?\n\n1. Confirm\n2. Cancel"
                return confirm, True
                
            except ValueError:
                return "Enter amount in numbers:", True
        
        elif step == 3:
            # Confirmation
            if user_input == '1':
                return self._create_ussd_bid(session, user, data, lang)
            else:
                session.current_menu = 'transport_jobs'
                session.current_step = 0
                return "Bid cancelled.\n" + self._show_transport_menu(session, user, lang)[0], True
        
        return get_message('error', lang), False
    
    def _create_ussd_bid(
        self,
        session,
        user,
        data: dict,
        lang: str
    ) -> Tuple[str, bool]:
        """Create a bid from USSD"""
        try:
            profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
            job_id = data.get('selected_job_id')
            bid_amount = data.get('bid_amount', 0)
            
            if not profile or not job_id:
                return "Error creating bid. Try again.", False
            
            # Check for existing bid
            existing = self.LogisticsBid.query.filter_by(
                logistics_request_id=job_id,
                transporter_id=profile.id
            ).first()
            
            if existing:
                existing.bid_amount = bid_amount
                existing.source_channel = 'ussd'
            else:
                bid = self.LogisticsBid(
                    logistics_request_id=job_id,
                    transporter_id=profile.id,
                    bid_amount=bid_amount,
                    eta_hours=24,
                    source_channel='ussd'
                )
                self.db.session.add(bid)
            
            # Update job status
            job = self.LogisticsRequest.query.get(job_id)
            if job and job.status == 'pending':
                job.status = 'bidding'
            
            self.db.session.commit()
            
            session.current_menu = 'transport_jobs'
            session.current_step = 0
            
            return f"Bid of ₦{bid_amount:,.0f} submitted!\nYou will be notified if accepted.", False
            
        except Exception as e:
            logger.error(f"USSD bid error: {e}")
            return "Error submitting bid. Try again.", False
    
    def _show_my_bids(
        self,
        session,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Show user's transport bids"""
        
        profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            session.current_menu = 'main'
            return "Not a registered transporter.", False
        
        bids = self.LogisticsBid.query.filter_by(
            transporter_id=profile.id
        ).order_by(self.LogisticsBid.created_at.desc()).limit(5).all()
        
        if not bids:
            session.current_menu = 'transport_jobs'
            return "No bids yet.\nGo to New Jobs to start bidding.", False
        
        response = "YOUR BIDS:\n"
        for bid in bids:
            job = bid.logistics_request
            route = f"{job.pickup_state or 'N/A'}->{job.destination_state or 'N/A'}" if job else "N/A"
            status = bid.status.upper()
            response += f"#{bid.logistics_request_id}: ₦{bid.bid_amount:,.0f} [{status}]\n"
        
        session.current_menu = 'transport_jobs'
        return response, False
    
    def _show_active_trips(
        self,
        session,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Show active trips for transporter"""
        
        profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            session.current_menu = 'main'
            return "Not a registered transporter.", False
        
        # Get trips where this transporter's bid was accepted
        accepted_bids = self.LogisticsBid.query.filter_by(
            transporter_id=profile.id,
            status='accepted'
        ).all()
        
        active_jobs = [b.logistics_request for b in accepted_bids 
                      if b.logistics_request and b.logistics_request.status in ['assigned', 'in_transit']]
        
        if not active_jobs:
            session.current_menu = 'transport_jobs'
            return "No active trips.\nBid on new jobs to get started!", False
        
        response = "ACTIVE TRIPS:\n"
        job_ids = []
        for i, job in enumerate(active_jobs[:5], 1):
            route = f"{job.pickup_state or 'N/A'}->{job.destination_state or 'N/A'}"
            status = job.status.replace('_', ' ').upper()
            response += f"{i}. {route} [{status}]\n"
            job_ids.append(job.id)
        
        if any(j.status == 'assigned' for j in active_jobs):
            response += "\nEnter number to start trip:"
            session.update_session_data('active_job_ids', job_ids)
            session.current_step = 1
            return response, True
        
        session.current_menu = 'transport_jobs'
        return response, False
    
    def _handle_active_trips(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle active trips menu"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            return self._show_active_trips(session, user, lang)
        
        elif step == 1:
            # Start a trip
            try:
                job_index = int(user_input) - 1
                job_ids = data.get('active_job_ids', [])
                
                if 0 <= job_index < len(job_ids):
                    job_id = job_ids[job_index]
                    job = self.LogisticsRequest.query.get(job_id)
                    
                    if job and job.status == 'assigned':
                        job.status = 'in_transit'
                        self.db.session.commit()
                        
                        session.current_menu = 'transport_jobs'
                        session.current_step = 0
                        
                        return f"Trip #{job.id} started!\nSafe travels. Deliver on time for best rating.", False
                    
                    return "Trip already in progress or delivered.", False
                
                return "Invalid selection.", False
                
            except ValueError:
                return "Enter a number:", True
        
        return get_message('error', lang), False

    def _parse_quantity(self, quantity_str: str) -> Optional[dict]:
        """Parse quantity string like '50BAGS', '100KG', '5TONS'"""
        pattern = r'^(\d+\.?\d*)\s*(BAGS?|KG|KILOS?|TONS?|T|TUBERS?|BUNCHES?)$'
        match = re.match(pattern, quantity_str.strip().upper())
        
        if match:
            return {
                'value': float(match.group(1)),
                'unit': match.group(2)
            }
        return None
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format"""
        phone = re.sub(r'[^\d+]', '', phone)
        if not phone.startswith('+'):
            if phone.startswith('0'):
                phone = '+234' + phone[1:]
            elif phone.startswith('234'):
                phone = '+' + phone
            else:
                phone = '+' + phone
        return phone
    
    def format_for_africastalking(self, response: str, should_continue: bool) -> str:
        """Format response for Africa's Talking USSD"""
        prefix = "CON " if should_continue else "END "
        return prefix + response
    
    def format_for_t2(self, response: str, should_continue: bool) -> str:
        """Format response for T2 (9mobile) USSD"""
        # T2 uses plain text, similar format
        prefix = "CON " if should_continue else "END "
        return prefix + response
    
    def end_session(self, session_id: str) -> None:
        """Mark a session as ended"""
        self._lazy_load_models()
        session = self.USSDSession.query.filter_by(session_id=session_id).first()
        if session:
            session.ended_at = datetime.utcnow()
            self.db.session.commit()
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get USSD session metrics for analytics"""
        self._lazy_load_models()
        
        try:
            total_sessions = self.USSDSession.query.count()
            active_sessions = self.USSDSession.query.filter(
                self.USSDSession.ended_at.is_(None)
            ).count()
            
            unique_users = self.USSDSession.query.with_entities(
                self.USSDSession.phone_number
            ).distinct().count()
            
            ussd_users = self.User.query.filter_by(is_ussd_user=True).count()
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'unique_phone_numbers': unique_users,
                'registered_ussd_users': ussd_users
            }
        except Exception as e:
            logger.error(f"Error getting USSD metrics: {e}")
            return {}


# Singleton instance
ussd_service = USSDService()
