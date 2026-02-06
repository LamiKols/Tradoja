"""
USSD Service for Tradoja
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
                '4': 'wallet',
                '5': 'register',
                '6': 'transport_jobs',
                '7': 'register_buyer',
                '8': 'register_agent',
                '9': 'agent_menu',
                '10': 'sabibuy_start',
                '11': 'sabibuy_join',
                '12': 'sabibuy_my_campaigns',
                '13': 'sabibuy_earnings',
                '14': 'pay_produce',
                '15': 'captain_bond',
                '16': 'trader_verify'
            }
        },
        'trader_verify': {
            'steps': ['select_services', 'confirm_application'],
            'next': 'main'
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
        'register_buyer': {
            'steps': ['name', 'location', 'buyer_type'],
            'next': 'main'
        },
        'register_agent': {
            'steps': ['name', 'location', 'referral_code'],
            'next': 'main'
        },
        'agent_menu': {
            'options': {
                '1': 'agent_register_farmer',
                '2': 'agent_register_buyer',
                '3': 'agent_my_farmers',
                '4': 'agent_earnings'
            },
            'next': 'main'
        },
        'agent_register_farmer': {
            'steps': ['farmer_name', 'farmer_location', 'farmer_crop'],
            'next': 'agent_menu'
        },
        'agent_register_buyer': {
            'steps': ['buyer_name', 'buyer_location'],
            'next': 'agent_menu'
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
        },
        'sabibuy_start': {
            'steps': ['select_produce', 'set_price', 'set_location', 'confirm'],
            'next': 'main'
        },
        'sabibuy_join': {
            'steps': ['enter_code', 'enter_quantity', 'confirm_payment'],
            'next': 'main'
        },
        'wallet': {
            'options': {
                '1': 'wallet_balance',
                '2': 'wallet_topup',
                '3': 'wallet_transfer',
                '4': 'wallet_history'
            },
            'next': 'main'
        },
        'wallet_topup': {
            'steps': ['enter_amount', 'select_bank', 'confirm'],
            'next': 'wallet'
        },
        'wallet_transfer': {
            'steps': ['enter_phone', 'enter_amount', 'confirm'],
            'next': 'wallet'
        },
        'pay_produce': {
            'steps': ['enter_listing_id', 'select_payment_method', 'confirm'],
            'next': 'main'
        },
        'captain_bond': {
            'options': {
                '1': 'bond_pay',
                '2': 'bond_status',
                '3': 'bond_refund'
            },
            'next': 'main'
        },
        'sabibuy_my_campaigns': {
            'steps': [],
            'next': 'main'
        },
        'sabibuy_earnings': {
            'steps': [],
            'next': 'main'
        }
    }
    
    @staticmethod
    def _verified_name(user, short=True):
        """Return user's name with * marker if verified (for USSD brevity)"""
        if user and hasattr(user, 'is_verified_account') and user.is_verified_account():
            return f"{user.name}*" if short else f"{user.name} [VERIFIED]"
        return user.name if user else "Unknown"

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
            from models import User, USSDSession, Produce, TransportProfile, LogisticsRequest, LogisticsBid, AgentProfile, SabiBuy, SabiBuyOrder
            self.db = db
            self.User = User
            self.USSDSession = USSDSession
            self.Produce = Produce
            self.TransportProfile = TransportProfile
            self.LogisticsRequest = LogisticsRequest
            self.LogisticsBid = LogisticsBid
            self.AgentProfile = AgentProfile
            self.SabiBuy = SabiBuy
            self.SabiBuyOrder = SabiBuyOrder
    
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
        
        elif session.current_menu == 'register_buyer':
            return self._handle_register_buyer(session, current_input, user, lang)
        
        elif session.current_menu == 'register_agent':
            return self._handle_register_agent(session, current_input, user, lang)
        
        elif session.current_menu == 'agent_menu':
            return self._handle_agent_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'agent_register_farmer':
            return self._handle_agent_register_farmer(session, current_input, user, lang)
        
        elif session.current_menu == 'agent_register_buyer':
            return self._handle_agent_register_buyer(session, current_input, user, lang)
        
        elif session.current_menu == 'agent_my_farmers':
            return self._show_agent_farmers(session, user, lang)
        
        elif session.current_menu == 'agent_earnings':
            return self._show_agent_earnings(session, user, lang)
        
        elif session.current_menu == 'transport_balance':
            return self._show_transport_balance(session, user, lang)
        
        elif session.current_menu == 'sabibuy_start':
            return self._handle_sabibuy_start(session, current_input, user, lang)
        
        elif session.current_menu == 'sabibuy_join':
            return self._handle_sabibuy_join(session, current_input, user, lang)
        
        elif session.current_menu == 'sabibuy_my_campaigns':
            return self._show_sabibuy_campaigns(session, user, lang)
        
        elif session.current_menu == 'sabibuy_earnings':
            return self._show_sabibuy_earnings(session, user, lang)
        
        elif session.current_menu == 'wallet':
            return self._handle_wallet_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'wallet_topup':
            return self._handle_wallet_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'wallet_transfer':
            return self._handle_wallet_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'pay_produce':
            return self._handle_pay_produce(session, current_input, user, lang)
        
        elif session.current_menu == 'captain_bond':
            return self._handle_captain_bond_menu(session, current_input, user, lang)
        
        elif session.current_menu == 'trader_verify':
            return self._handle_trader_verify(session, current_input, user, lang)
        
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
                    session.current_step = 0
                    return "Register first to list produce.\nEnter your name:", True
                if not user.can_create_listing():
                    return "Listing limit reached (max 3 for unverified).\nVisit tradoja.com/get-verified", False
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
            
            elif target_menu == 'register_buyer':
                if user and user.role == 'buyer':
                    return get_message('already_buyer', lang), False
                return get_message('register_buyer_name', lang), True
            
            elif target_menu == 'register_agent':
                if user:
                    profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
                    if profile:
                        return get_message('already_agent', lang, agent_id=profile.agent_id), False
                return get_message('register_agent_name', lang), True
            
            elif target_menu == 'agent_menu':
                if not user:
                    return get_message('register_agent_first', lang), False
                profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    return get_message('register_agent_first', lang), False
                return self._show_agent_menu(session, user, lang)
            
            elif target_menu == 'sabibuy_start':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to start SabiBuy.\nEnter your name:", True
                return self._show_sabibuy_produce_selection(session, user, lang)
            
            elif target_menu == 'sabibuy_join':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to join SabiBuy.\nEnter your name:", True
                return get_message('sabibuy_join_prompt', lang), True
            
            elif target_menu == 'sabibuy_my_campaigns':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to view campaigns.\nEnter your name:", True
                return self._show_sabibuy_campaigns(session, user, lang)
            
            elif target_menu == 'sabibuy_earnings':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to view earnings.\nEnter your name:", True
                return self._show_sabibuy_earnings(session, user, lang)
            
            elif target_menu == 'wallet':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to access wallet.\nEnter your name:", True
                return self._show_wallet_menu(session, user, lang)
            
            elif target_menu == 'pay_produce':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to make payments.\nEnter your name:", True
                return "Enter listing ID to pay for:", True
            
            elif target_menu == 'captain_bond':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first to manage bond.\nEnter your name:", True
                return self._show_captain_bond_menu(session, user, lang)
            
            elif target_menu == 'trader_verify':
                if not user:
                    session.current_menu = 'register'
                    session.current_step = 0
                    return "Register first for trader verification.\nEnter your name:", True
                if user.role != 'buyer' or not user.is_trader():
                    return "Trader verification is for bulk traders only.", False
                if user.trader_verified:
                    return f"Already verified trader!\nStatus: {user.trader_verification_status}", False
                return self._show_trader_verify_menu(session, user, lang)
        
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
            session.current_step = 0
            return "Register first to list produce.\nEnter your name:", True
        
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
            session.current_step = 0
            return "Register first to view listings.\nEnter your name:", True
        
        listings = Produce.query.filter_by(
            farmer_id=user.id,
            is_available=True,
            is_sold=False
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
            session.current_step = 0
            return "Register first to view balance.\nEnter your name:", True
        
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
        """Handle user registration flow (3-step) - Creates LITE account"""
        from werkzeug.security import generate_password_hash
        import secrets
        
        if user:
            session.current_menu = 'main'
            if user.is_lite_account():
                return "Already registered (LITE). Visit tradoja.com to get VERIFIED!", False
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
            # Step 3: Main crop and complete LITE registration
            data['main_crop'] = user_input.strip().title()
            
            try:
                # Create LITE user account (USSD registration)
                new_user = self.User(
                    name=data['name'],
                    phone_number=session.phone_number,
                    email=f"{session.phone_number.replace('+', '')}@ussd.tradoja.com",
                    role='farmer',
                    location=data['location'],
                    is_ussd_user=True,
                    preferred_language=lang,
                    sms_enabled=True,
                    sms_registration_date=datetime.utcnow(),
                    source_channel='ussd',
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                temp_password = secrets.token_hex(8)
                new_user.password_hash = generate_password_hash(temp_password)
                
                self.db.session.add(new_user)
                self.db.session.commit()
                
                # Update session
                session.user_id = new_user.id
                session.is_authenticated = True
                session.current_menu = 'main'
                session.current_step = 0
                
                success_msg = f"Welcome {data['name']}! You're registered (LITE). Visit tradoja.com for VERIFIED status!"
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
                        email=f"{phone.replace('+', '').replace('-', '')}@transport.tradoja.com",
                        role='transport_company',
                        is_ussd_user=True,
                        source_channel='ussd',
                        preferred_language=lang,
                        location=location,
                        registration_status='lite',
                        lite_registration_date=datetime.utcnow()
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
    
    def _handle_register_buyer(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle 3-step buyer LITE registration via USSD"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            data['name'] = user_input.strip().title()
            session.update_session_data('name', data['name'])
            session.current_step = 1
            return get_message('register_buyer_location', lang), True
        
        elif step == 1:
            data['location'] = user_input.strip().title()
            session.update_session_data('location', data['location'])
            session.current_step = 2
            return get_message('register_buyer_type', lang), True
        
        elif step == 2:
            buyer_type_map = {
                '1': 'retail_buyer',
                '2': 'bulk_trader',
                '3': 'institutional_buyer',
                '4': 'agro_processor'
            }
            
            if user_input not in buyer_type_map:
                return get_message('register_buyer_type', lang), True
            
            buyer_type = buyer_type_map[user_input]
            
            name = data.get('name')
            location = data.get('location')
            
            if not name or not location:
                session.current_menu = 'main'
                session.current_step = 0
                return "Session expired. Please try again.\nDial *712*55# > 7", False
            
            try:
                from werkzeug.security import generate_password_hash
                
                phone = session.phone_number
                
                if user:
                    user.role = 'buyer'
                    user.buyer_type = buyer_type
                    user.location = location
                    new_user = user
                else:
                    new_user = self.User(
                        name=name,
                        phone_number=phone,
                        email=f"{phone.replace('+', '').replace('-', '')}@buyer.tradoja.com",
                        role='buyer',
                        buyer_type=buyer_type,
                        is_ussd_user=True,
                        source_channel='ussd',
                        preferred_language=lang,
                        location=location,
                        registration_status='lite',
                        lite_registration_date=datetime.utcnow()
                    )
                    new_user.password_hash = generate_password_hash('ussd_buyer_temp')
                    self.db.session.add(new_user)
                
                self.db.session.commit()
                
                session.current_menu = 'main'
                session.current_step = 0
                session.set_session_data({})
                
                return get_message('register_buyer_success', lang, name=name), False
                
            except Exception as e:
                logger.error(f"USSD buyer registration error: {e}")
                self.db.session.rollback()
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _handle_register_agent(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle 3-step agent LITE registration via USSD"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            data['name'] = user_input.strip().title()
            session.update_session_data('name', data['name'])
            session.current_step = 1
            return get_message('register_agent_location', lang), True
        
        elif step == 1:
            data['lga'] = user_input.strip().title()
            session.update_session_data('lga', data['lga'])
            session.current_step = 2
            return get_message('register_agent_referral', lang), True
        
        elif step == 2:
            referral_code = user_input.strip() if user_input.strip() not in ('0', 'SKIP', 'skip', '') else None
            
            name = data.get('name')
            lga = data.get('lga')
            
            if not name or not lga:
                session.current_menu = 'main'
                session.current_step = 0
                return "Session expired. Please try again.\nDial *712*55# > 8", False
            
            try:
                from werkzeug.security import generate_password_hash
                
                phone = session.phone_number
                is_nysc = self.AgentProfile.is_valid_nysc_code(referral_code) if referral_code else False
                
                if user:
                    user.role = 'agent'
                    user.location = lga
                    new_user = user
                else:
                    new_user = self.User(
                        name=name,
                        phone_number=phone,
                        email=f"{phone.replace('+', '').replace('-', '')}@agent.tradoja.com",
                        role='agent',
                        is_ussd_user=True,
                        source_channel='ussd',
                        preferred_language=lang,
                        location=lga,
                        registration_status='lite',
                        lite_registration_date=datetime.utcnow()
                    )
                    new_user.password_hash = generate_password_hash('ussd_agent_temp')
                    self.db.session.add(new_user)
                    self.db.session.flush()
                
                agent_id = self.AgentProfile.generate_agent_id()
                
                profile = self.AgentProfile(
                    user_id=new_user.id,
                    agent_id=agent_id,
                    lga=lga,
                    referral_code_used=referral_code,
                    registration_channel='ussd_lite',
                    is_approved=is_nysc,
                    is_nysc=is_nysc
                )
                
                self.db.session.add(profile)
                self.db.session.commit()
                
                session.current_menu = 'main'
                session.current_step = 0
                session.set_session_data({})
                
                return get_message('register_agent_success', lang, 
                                  agent_id=agent_id, 
                                  name=name), False
                
            except Exception as e:
                logger.error(f"USSD agent registration error: {e}")
                self.db.session.rollback()
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _show_agent_menu(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show the agent menu"""
        profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return get_message('register_agent_first', lang), False
        
        status = "Approved" if profile.is_approved else "Pending"
        return get_message('agent_menu', lang, 
                          agent_id=profile.agent_id,
                          status=status), True
    
    def _handle_agent_menu(
        self, 
        session, 
        selection: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle selection from agent menu"""
        
        if selection == '0':
            session.current_menu = 'main'
            session.current_step = 0
            return self._show_main_menu(lang, user), True
        
        profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            return get_message('register_agent_first', lang), False
        
        menu_map = self.MENUS['agent_menu'].get('options', {})
        
        if selection in menu_map:
            target = menu_map[selection]
            session.current_menu = target
            session.current_step = 0
            session.set_session_data({})
            
            if target == 'agent_register_farmer':
                if not profile.is_approved:
                    return get_message('agent_pending_approval', lang), False
                return get_message('agent_farmer_name', lang), True
            elif target == 'agent_register_buyer':
                if not profile.is_approved:
                    return get_message('agent_pending_approval', lang), False
                return get_message('agent_buyer_name', lang), True
            elif target == 'agent_my_farmers':
                return self._show_agent_farmers(session, user, lang)
            elif target == 'agent_earnings':
                return self._show_agent_earnings(session, user, lang)
        
        return get_message('invalid_command', lang), True
    
    def _handle_agent_register_farmer(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle agent registering a farmer via USSD"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            data['farmer_name'] = user_input.strip().title()
            session.update_session_data('farmer_name', data['farmer_name'])
            session.current_step = 1
            return get_message('agent_farmer_location', lang), True
        
        elif step == 1:
            data['farmer_location'] = user_input.strip().title()
            session.update_session_data('farmer_location', data['farmer_location'])
            session.current_step = 2
            return get_message('agent_farmer_crop', lang), True
        
        elif step == 2:
            farmer_crop = user_input.strip().title()
            farmer_name = data.get('farmer_name')
            farmer_location = data.get('farmer_location')
            
            if not farmer_name or not farmer_location:
                session.current_menu = 'agent_menu'
                session.current_step = 0
                return "Session expired. Try again.", False
            
            try:
                from werkzeug.security import generate_password_hash
                import random
                
                phone_placeholder = f"+234{random.randint(7000000000, 9999999999)}"
                
                new_farmer = self.User(
                    name=farmer_name,
                    phone_number=phone_placeholder,
                    email=f"farmer{random.randint(10000, 99999)}@tradoja.com",
                    role='farmer',
                    is_ussd_user=True,
                    source_channel='agent',
                    preferred_language=lang,
                    location=farmer_location,
                    registered_by_agent_id=user.id,
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                new_farmer.password_hash = generate_password_hash('agent_farmer_temp')
                self.db.session.add(new_farmer)
                
                profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
                if profile:
                    profile.total_farmers_registered += 1
                    if profile.total_farmers_registered % 10 == 0:
                        profile.pending_earnings += 200.0
                
                self.db.session.commit()
                
                session.current_menu = 'agent_menu'
                session.current_step = 0
                session.set_session_data({})
                
                return get_message('agent_farmer_success', lang, 
                                  name=farmer_name,
                                  total=profile.total_farmers_registered if profile else 1), False
                
            except Exception as e:
                logger.error(f"Agent farmer registration error: {e}")
                self.db.session.rollback()
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _handle_agent_register_buyer(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle agent registering a buyer via USSD"""
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            data['buyer_name'] = user_input.strip().title()
            session.update_session_data('buyer_name', data['buyer_name'])
            session.current_step = 1
            return get_message('agent_buyer_location', lang), True
        
        elif step == 1:
            buyer_location = user_input.strip().title()
            buyer_name = data.get('buyer_name')
            
            if not buyer_name:
                session.current_menu = 'agent_menu'
                session.current_step = 0
                return "Session expired. Try again.", False
            
            try:
                from werkzeug.security import generate_password_hash
                import random
                
                phone_placeholder = f"+234{random.randint(7000000000, 9999999999)}"
                
                new_buyer = self.User(
                    name=buyer_name,
                    phone_number=phone_placeholder,
                    email=f"buyer{random.randint(10000, 99999)}@tradoja.com",
                    role='buyer',
                    buyer_type='retail_buyer',
                    is_ussd_user=True,
                    source_channel='agent',
                    preferred_language=lang,
                    location=buyer_location,
                    registered_by_agent_id=user.id,
                    registration_status='lite',
                    lite_registration_date=datetime.utcnow()
                )
                new_buyer.password_hash = generate_password_hash('agent_buyer_temp')
                self.db.session.add(new_buyer)
                
                profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
                if profile:
                    profile.total_buyers_registered += 1
                
                self.db.session.commit()
                
                session.current_menu = 'agent_menu'
                session.current_step = 0
                session.set_session_data({})
                
                return get_message('agent_buyer_success', lang, 
                                  name=buyer_name,
                                  total=profile.total_buyers_registered if profile else 1), False
                
            except Exception as e:
                logger.error(f"Agent buyer registration error: {e}")
                self.db.session.rollback()
                return get_message('error', lang), False
        
        return get_message('error', lang), False
    
    def _show_agent_farmers(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show farmers registered by this agent"""
        farmers = self.User.query.filter_by(
            registered_by_agent_id=user.id, 
            role='farmer'
        ).order_by(self.User.registration_date.desc()).limit(5).all()
        
        profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
        
        if not farmers:
            session.current_menu = 'agent_menu'
            return get_message('agent_no_farmers', lang), True
        
        farmer_list = "\n".join([f"{i+1}. {f.name} ({f.location})" for i, f in enumerate(farmers)])
        total = profile.total_farmers_registered if profile else len(farmers)
        
        session.current_menu = 'agent_menu'
        return get_message('agent_farmers_list', lang, 
                          farmers=farmer_list, 
                          total=total), True
    
    def _show_agent_earnings(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show agent earnings"""
        profile = self.AgentProfile.query.filter_by(user_id=user.id).first()
        
        if not profile:
            session.current_menu = 'main'
            return get_message('register_agent_first', lang), False
        
        session.current_menu = 'agent_menu'
        return get_message('agent_earnings', lang,
                          pending=profile.pending_earnings,
                          total=profile.total_earnings,
                          farmers=profile.total_farmers_registered,
                          buyers=profile.total_buyers_registered), True
    
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
    
    def _show_sabibuy_produce_selection(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show available produce for SabiBuy campaign"""
        produce_list = self.Produce.query.filter(
            self.Produce.is_available == True,
            self.Produce.is_sold == False
        ).limit(10).all()
        
        if not produce_list:
            return "No produce available for SabiBuy. Check back later.", False
        
        produce_options = []
        produce_ids = []
        for i, p in enumerate(produce_list, 1):
            farmer = self.User.query.get(p.farmer_id) if p.farmer_id else None
            farmer_tag = "*" if farmer and farmer.is_verified_account() else ""
            produce_options.append(f"{i}. {p.name}{farmer_tag} @ ₦{p.price:,.0f}/{p.quantity}")
            produce_ids.append(p.id)
        
        session.update_session_data('produce_ids', produce_ids)
        session.current_step = 0
        
        return get_message('sabibuy_select_produce', lang, produce_list="\n".join(produce_options)), True
    
    def _handle_sabibuy_start(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle SabiBuy campaign creation flow"""
        
        if not user:
            session.current_menu = 'register'
            session.current_step = 0
            return "Register first to start SabiBuy.\nEnter your name:", True
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            try:
                produce_index = int(user_input) - 1
                produce_ids = data.get('produce_ids', [])
                
                if 0 <= produce_index < len(produce_ids):
                    produce_id = produce_ids[produce_index]
                    produce = self.Produce.query.get(produce_id)
                    
                    if produce:
                        session.update_session_data('produce_id', produce_id)
                        session.update_session_data('produce_name', produce.name)
                        session.update_session_data('farm_price', produce.price)
                        session.update_session_data('unit', produce.quantity)
                        
                        suggested = int(produce.price * 1.15)
                        margin = suggested - produce.price
                        
                        session.current_step = 1
                        return get_message('sabibuy_set_price', lang, 
                                         farm_price=f"{produce.price:,.0f}",
                                         suggested=f"{suggested:,.0f}",
                                         margin=f"{margin:,.0f}"), True
                
                return "Invalid selection. Enter number:", True
                
            except ValueError:
                return "Enter a number:", True
        
        elif step == 1:
            try:
                price = float(re.sub(r'[^\d.]', '', user_input))
                farm_price = data.get('farm_price', 0)
                
                if price <= farm_price:
                    return f"Price must be higher than farm price ₦{farm_price:,.0f}:", True
                
                session.update_session_data('selling_price', price)
                session.current_step = 2
                return get_message('sabibuy_set_location', lang), True
                
            except ValueError:
                return "Enter valid price:", True
        
        elif step == 2:
            location = user_input.strip()
            if len(location) < 2:
                return "Enter valid location:", True
            
            session.update_session_data('delivery_location', location)
            session.current_step = 3
            
            produce_name = data.get('produce_name', 'Produce')
            price = data.get('selling_price', 0)
            unit = data.get('unit', 'unit')
            
            return get_message('sabibuy_confirm', lang,
                             produce=produce_name,
                             price=f"{price:,.0f}",
                             min_qty=50,
                             unit=unit,
                             location=location), True
        
        elif step == 3:
            if user_input == '1':
                try:
                    from services.sabibuy_service import sabibuy_service
                    
                    delivery_location = data.get('delivery_location', '')
                    
                    result = sabibuy_service.create_campaign(
                        organizer_id=user.id,
                        produce_id=data.get('produce_id'),
                        selling_price=data.get('selling_price'),
                        delivery_lga=delivery_location,
                        delivery_market=delivery_location,
                        delivery_state='Lagos',
                        minimum_quantity=50,
                        maximum_quantity=500,
                        source_channel='ussd'
                    )
                    
                    if result.get('success'):
                        code = result.get('code', 'N/A')
                        session.current_menu = 'main'
                        session.current_step = 0
                        return get_message('sabibuy_created', lang, code=code, quantity=50), False
                    else:
                        return result.get('error', 'Campaign creation failed'), False
                        
                except Exception as e:
                    logger.error(f"SabiBuy creation error: {e}")
                    return get_message('error', lang), False
            
            elif user_input == '2':
                session.current_menu = 'main'
                return self._show_main_menu(lang, user), True
        
        return get_message('error', lang), False
    
    def _handle_sabibuy_join(
        self,
        session,
        user_input: str,
        user,
        lang: str
    ) -> Tuple[str, bool]:
        """Handle joining a SabiBuy campaign"""
        
        if not user:
            session.current_menu = 'register'
            session.current_step = 0
            return "Register first to join SabiBuy.\nEnter your name:", True
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            code = user_input.strip().upper()
            campaign = self.SabiBuy.query.filter_by(code=code).first()
            
            if not campaign:
                return get_message('sabibuy_invalid_code', lang), True
            
            if campaign.status != 'active':
                return get_message('sabibuy_expired', lang), False
            
            session.update_session_data('campaign_id', campaign.id)
            session.update_session_data('campaign_code', code)
            session.current_step = 1
            
            produce = self.Produce.query.get(campaign.produce_id)
            produce_name = produce.name if produce else 'Produce'
            
            return get_message('sabibuy_join_quantity', lang,
                             code=code,
                             produce=produce_name,
                             price=f"{campaign.selling_price:,.0f}",
                             unit=produce.quantity if produce else 'unit'), True
        
        elif step == 1:
            try:
                quantity = int(user_input)
                if quantity < 1:
                    return "Enter quantity (minimum 1):", True
                
                campaign_id = data.get('campaign_id')
                campaign = self.SabiBuy.query.get(campaign_id)
                
                if not campaign:
                    return get_message('sabibuy_invalid_code', lang), False
                
                total = quantity * campaign.selling_price
                
                session.update_session_data('quantity', quantity)
                session.update_session_data('total', total)
                session.current_step = 2
                
                produce = self.Produce.query.get(campaign.produce_id)
                unit = produce.quantity if produce else 'unit'
                
                return get_message('sabibuy_join_confirm', lang,
                                 quantity=quantity,
                                 unit=unit,
                                 total=f"{total:,.0f}"), True
                
            except ValueError:
                return "Enter valid quantity:", True
        
        elif step == 2:
            if user_input == '1' or user_input == '2':
                try:
                    from services.sabibuy_service import sabibuy_service
                    
                    payment_method = 't2_wallet' if user_input == '1' else 'paystack'
                    campaign_code = data.get('campaign_code', '')
                    phone = getattr(user, 'phone_number', '')
                    
                    result = sabibuy_service.join_campaign(
                        code=campaign_code,
                        buyer_phone=phone,
                        quantity=data.get('quantity'),
                        buyer_name=user.name,
                        buyer_id=user.id,
                        payment_method=payment_method,
                        source_channel='ussd',
                        language=lang
                    )
                    
                    if result.get('success'):
                        session.current_menu = 'main'
                        session.current_step = 0
                        return get_message('sabibuy_order_placed', lang,
                                         quantity=data.get('quantity'),
                                         unit='units',
                                         total=f"{data.get('total'):,.0f}"), False
                    else:
                        return result.get('error', 'Order failed'), False
                        
                except Exception as e:
                    logger.error(f"SabiBuy order error: {e}")
                    return get_message('error', lang), False
            
            elif user_input == '3':
                session.current_menu = 'main'
                return self._show_main_menu(lang, user), True
        
        return get_message('error', lang), False
    
    def _show_sabibuy_campaigns(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show user's SabiBuy campaigns"""
        
        if not user:
            return "Register first to view campaigns.", False
        
        campaigns = self.SabiBuy.query.filter_by(organizer_id=user.id).order_by(
            self.SabiBuy.created_at.desc()
        ).limit(5).all()
        
        if not campaigns:
            return "You have no SabiBuy campaigns yet.\nDial 10 to start one!", False
        
        campaigns_list = []
        for c in campaigns:
            produce = self.Produce.query.get(c.produce_id)
            produce_name = produce.name if produce else 'Produce'
            progress = int((c.current_quantity / c.minimum_quantity * 100)) if c.minimum_quantity > 0 else 0
            campaigns_list.append(f"{c.code}: {produce_name} ({progress}%)")
        
        return get_message('sabibuy_my_campaigns', lang, campaigns_list="\n".join(campaigns_list)), False
    
    def _show_sabibuy_earnings(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show SabiBuy earnings summary"""
        
        if not user:
            return "Register first to view earnings.", False
        
        total_profit = 0
        pending_profit = 0
        campaign_count = 0
        
        campaigns = self.SabiBuy.query.filter_by(organizer_id=user.id).all()
        campaign_count = len(campaigns)
        
        for c in campaigns:
            if c.status == 'delivered':
                total_profit += c.organizer_profit or 0
            elif c.status in ['active', 'closed', 'booked', 'in_transit']:
                pending_profit += c.organizer_profit or 0
        
        return get_message('sabibuy_earnings', lang,
                         pending=f"{pending_profit:,.0f}",
                         total=f"{total_profit:,.0f}",
                         campaigns=campaign_count), False
    
    def _show_wallet_menu(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show wallet menu options"""
        from wallet_service import wallet_service
        
        balance = wallet_service.get_balance(user)
        
        menu = (f"Wallet Balance: N{balance:,.0f}\n\n"
                f"1. Check Balance\n"
                f"2. Top Up Wallet\n"
                f"3. Transfer Money\n"
                f"4. Transaction History\n"
                f"0. Back")
        
        return menu, True
    
    def _handle_wallet_menu(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle wallet menu selections"""
        from wallet_service import wallet_service
        from payment_service import payment_service
        
        data = session.get_session_data()
        step = session.current_step
        current_submenu = data.get('wallet_action')
        
        if step == 0:
            if user_input == '1':
                balance = wallet_service.get_balance(user)
                history = wallet_service.format_history_sms(user, 3)
                return f"Balance: N{balance:,.0f}\n\n{history}", False
            
            elif user_input == '2':
                session.current_step = 1
                data['wallet_action'] = 'topup'
                session.set_session_data(data)
                return "Enter amount to add (min N100):", True
            
            elif user_input == '3':
                session.current_step = 1
                data['wallet_action'] = 'transfer'
                session.set_session_data(data)
                return "Enter recipient phone number:", True
            
            elif user_input == '4':
                history = wallet_service.format_history_sms(user, 5)
                balance = wallet_service.get_balance(user)
                return f"Balance: N{balance:,.0f}\n\n{history}", False
            
            elif user_input == '0':
                session.current_menu = 'main'
                return self._show_main_menu(lang, user), True
        
        if current_submenu == 'topup':
            if step == 1:
                try:
                    amount = float(user_input.replace(',', '').replace('N', ''))
                    if amount < 100:
                        return "Minimum is N100. Enter amount:", True
                    if amount > 500000:
                        return "Maximum is N500,000. Enter amount:", True
                    
                    data['topup_amount'] = amount
                    session.update_session_data('topup_amount', amount)
                    session.current_step = 2
                    
                    banks = payment_service.get_bank_ussd_codes()
                    bank_list = "\n".join([f"{i+1}. {info['name']}" 
                                          for i, (code, info) in enumerate(list(banks.items())[:6])])
                    
                    return f"Amount: N{amount:,.0f}\nSelect bank:\n{bank_list}", True
                    
                except ValueError:
                    return "Invalid amount. Enter numbers only:", True
            
            elif step == 2:
                try:
                    bank_index = int(user_input) - 1
                    banks = list(payment_service.get_bank_ussd_codes().items())
                    
                    if 0 <= bank_index < len(banks):
                        bank_code, bank_info = banks[bank_index]
                        amount = data.get('topup_amount', 0)
                        
                        ref = payment_service.generate_reference(f"USSD_TOPUP_{user.id}")
                        email = user.email if '@sms.' not in user.email else f"ussd_{user.phone_number.replace('+', '')}@tradoja.com"
                        
                        result = payment_service.charge_ussd(email, amount, ref, bank_code)
                        
                        session.current_menu = 'main'
                        session.current_step = 0
                        
                        if result.get('success'):
                            from models import Transaction
                            from app import db
                            
                            transaction = Transaction(
                                reference=ref,
                                user_id=user.id,
                                transaction_type='wallet_topup',
                                base_amount=amount,
                                platform_fee=0,
                                total_amount=amount,
                                payment_method='ussd',
                                status='pending'
                            )
                            db.session.add(transaction)
                            db.session.commit()
                            
                            return (f"Dial to complete:\n{result['ussd_code']}\n"
                                   f"Amount: N{amount:,.0f}\n"
                                   f"Ref: {ref}"), False
                        else:
                            return f"Failed: {result.get('message')}", False
                    else:
                        return "Invalid selection. Try again:", True
                        
                except ValueError:
                    return "Enter bank number:", True
        
        elif current_submenu == 'transfer':
            if step == 1:
                to_phone = user_input.strip()
                if not to_phone.startswith('+'):
                    if to_phone.startswith('0'):
                        to_phone = '+234' + to_phone[1:]
                    else:
                        to_phone = '+234' + to_phone
                
                from models import User
                to_user = User.query.filter_by(phone_number=to_phone).first()
                
                if not to_user:
                    return "User not found. Enter phone:", True
                
                if to_user.id == user.id:
                    return "Cannot send to yourself. Enter phone:", True
                
                data['transfer_to_phone'] = to_phone
                data['transfer_to_name'] = to_user.name
                data['transfer_to_id'] = to_user.id
                session.set_session_data(data)
                session.current_step = 2
                
                return f"Send to: {self._verified_name(to_user)}\nEnter amount:", True
            
            elif step == 2:
                try:
                    amount = float(user_input.replace(',', '').replace('N', ''))
                    balance = wallet_service.get_balance(user)
                    
                    if amount <= 0:
                        return "Enter positive amount:", True
                    if amount > balance:
                        return f"Insufficient funds. Balance: N{balance:,.0f}", False
                    
                    data['transfer_amount'] = amount
                    session.set_session_data(data)
                    session.current_step = 3
                    
                    return (f"Confirm transfer:\n"
                           f"To: {data.get('transfer_to_name')}\n"
                           f"Amount: N{amount:,.0f}\n\n"
                           f"1. Confirm\n2. Cancel"), True
                    
                except ValueError:
                    return "Invalid amount:", True
            
            elif step == 3:
                if user_input == '1':
                    from models import User
                    from app import db
                    
                    to_user = User.query.get(data.get('transfer_to_id'))
                    amount = data.get('transfer_amount', 0)
                    
                    success, msg, ref = wallet_service.transfer(
                        user, to_user, amount,
                        "USSD transfer",
                        db_session=db.session
                    )
                    
                    session.current_menu = 'main'
                    session.current_step = 0
                    
                    if success:
                        db.session.commit()
                        return (f"Sent N{amount:,.0f} to {self._verified_name(to_user)}\n"
                               f"Ref: {ref}\n"
                               f"Balance: N{wallet_service.get_balance(user):,.0f}"), False
                    else:
                        return f"Transfer failed: {msg}", False
                else:
                    session.current_menu = 'main'
                    return "Transfer cancelled.\n" + self._show_main_menu(lang, user), True
        
        return get_message('error', lang), False
    
    def _show_captain_bond_menu(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show Captain bond status and options"""
        from models import CaptainBond
        from wallet_service import wallet_service
        
        active_bond = CaptainBond.query.filter_by(
            user_id=user.id, status='active'
        ).first()
        
        if active_bond:
            menu = (f"Captain Bond: ACTIVE\n"
                   f"Amount: N{active_bond.amount:,.0f}\n"
                   f"Campaigns: {active_bond.campaigns_run}\n\n"
                   f"1. View Status\n"
                   f"2. Request Refund\n"
                   f"0. Back")
        else:
            balance = wallet_service.get_balance(user)
            menu = (f"No active Captain bond.\n"
                   f"Bond Amount: N10,000 (refundable)\n"
                   f"Your Balance: N{balance:,.0f}\n\n"
                   f"1. Pay Captain Bond\n"
                   f"0. Back")
        
        return menu, True
    
    def _handle_captain_bond_menu(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle Captain bond menu selections"""
        from models import CaptainBond, SabiBuy
        from wallet_service import wallet_service
        from app import db
        
        active_bond = CaptainBond.query.filter_by(
            user_id=user.id, status='active'
        ).first()
        
        if user_input == '0':
            session.current_menu = 'main'
            return self._show_main_menu(lang, user), True
        
        if active_bond:
            if user_input == '1':
                return (f"Bond Status: ACTIVE\n"
                       f"Amount: N{active_bond.amount:,.0f}\n"
                       f"Paid: {active_bond.collected_date.strftime('%Y-%m-%d')}\n"
                       f"Campaigns: {active_bond.campaigns_run}\n"
                       f"Successful: {active_bond.successful_campaigns}"), False
            
            elif user_input == '2':
                active_campaigns = SabiBuy.query.filter_by(
                    organizer_id=user.id
                ).filter(SabiBuy.status.in_(['active', 'closed', 'booked', 'in_transit'])).count()
                
                if active_campaigns > 0:
                    return f"Cannot refund: {active_campaigns} active campaign(s).\nComplete all first.", False
                
                success, msg = wallet_service.refund_captain_bond(user, db_session=db.session)
                
                session.current_menu = 'main'
                session.current_step = 0
                
                if success:
                    db.session.commit()
                    return f"Bond refunded!\n{msg}\nBalance: N{wallet_service.get_balance(user):,.0f}", False
                else:
                    return f"Refund failed: {msg}", False
        else:
            if user_input == '1':
                balance = wallet_service.get_balance(user)
                bond_amount = wallet_service.CAPTAIN_BOND_AMOUNT
                
                if balance < bond_amount:
                    return (f"Insufficient balance.\n"
                           f"Need: N{bond_amount:,.0f}\n"
                           f"Have: N{balance:,.0f}\n"
                           f"Top up via 4 > 2"), False
                
                success, msg, ref = wallet_service.collect_captain_bond(user, db_session=db.session)
                
                session.current_menu = 'main'
                session.current_step = 0
                
                if success:
                    db.session.commit()
                    return f"Bond paid!\nRef: {ref}\nYou can now start SabiBuy campaigns!", False
                else:
                    return f"Bond failed: {msg}", False
        
        return get_message('invalid_command', lang), True
    
    def _handle_pay_produce(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle produce payment flow via USSD"""
        from wallet_service import wallet_service
        from payment_service import payment_service
        from models import Produce, Transaction, EscrowHold
        from app import db
        
        data = session.get_session_data()
        step = session.current_step
        
        if step == 0:
            try:
                produce_id = int(user_input)
                produce = Produce.query.get(produce_id)
                
                if not produce:
                    return f"Listing #{produce_id} not found. Enter ID:", True
                
                if not produce.is_available:
                    return f"#{produce_id} not available. Enter ID:", True
                
                if produce.farmer_id == user.id:
                    return "Cannot buy own listing. Enter ID:", True
                
                if not user.can_transact_amount(produce.price):
                    return "Unverified limit: N50,000/txn.\nVisit tradoja.com/get-verified", False
                
                user_type = 'farmer' if user.role == 'farmer' else ('verified_trader' if user.trader_verified else 'buyer')
                fee_info = payment_service.calculate_tiered_fee(produce.price, user_type)
                
                data['produce_id'] = produce_id
                data['amount'] = produce.price
                data['fee'] = fee_info['platform_fee']
                data['total'] = fee_info['total_amount']
                session.set_session_data(data)
                session.current_step = 1
                
                balance = wallet_service.get_balance(user)
                
                seller = self.User.query.get(produce.farmer_id) if produce.farmer_id else None
                seller_tag = "*" if seller and seller.is_verified_account() else ""
                
                return (f"Item: {produce.name}\n"
                       f"Seller: {seller.name if seller else 'N/A'}{seller_tag}\n"
                       f"Qty: {produce.quantity}\n"
                       f"Price: N{produce.price:,.0f}\n"
                       f"Fee: N{fee_info['platform_fee']:,.0f}\n"
                       f"Total: N{fee_info['total_amount']:,.0f}\n\n"
                       f"Your balance: N{balance:,.0f}\n\n"
                       f"1. Pay with Wallet\n"
                       f"2. Pay with Bank USSD\n"
                       f"0. Cancel"), True
                
            except ValueError:
                return "Enter valid listing ID:", True
        
        elif step == 1:
            produce_id = data.get('produce_id')
            produce = Produce.query.get(produce_id)
            total = data.get('total', 0)
            
            if user_input == '1':
                balance = wallet_service.get_balance(user)
                if balance < total:
                    return (f"Insufficient balance.\n"
                           f"Have: N{balance:,.0f}\n"
                           f"Need: N{total:,.0f}\n"
                           f"Top up via Menu 4 > 2"), False
                
                success, msg, ref = wallet_service.hold_escrow(
                    user, total,
                    f"Payment for {produce.name} (#{produce.id})",
                    produce_id=produce.id,
                    db_session=db.session
                )
                
                session.current_menu = 'main'
                session.current_step = 0
                
                if success:
                    from models import Order, Transaction
                    fee = data.get('fee', 0)
                    order = Order(
                        farmer_id=produce.farmer_id,
                        buyer_id=user.id,
                        produce_id=produce.id,
                        quantity=str(produce.quantity),
                        total_amount=total,
                        platform_fee=fee,
                        status='pending',
                        pickup_location=produce.listing_location or '',
                        source_channel='ussd'
                    )
                    order.generate_order_code()
                    db.session.add(order)
                    
                    transaction = Transaction(
                        reference=ref,
                        user_id=user.id,
                        transaction_type='produce_sale',
                        base_amount=data.get('amount', total),
                        platform_fee=fee,
                        total_amount=total,
                        payment_method='t2_wallet',
                        status='successful',
                        produce_id=produce.id,
                        payment_date=datetime.utcnow()
                    )
                    db.session.add(transaction)
                    
                    produce.is_available = False
                    produce.buyer_id = user.id
                    
                    db.session.commit()
                    return (f"Payment held in escrow!\n"
                           f"Item: {produce.name}\n"
                           f"Order: {order.order_code}\n"
                           f"Amount: N{total:,.0f}\n"
                           f"Ref: {ref}\n"
                           f"Seller notified."), False
                else:
                    return f"Payment failed: {msg}", False
            
            elif user_input == '2':
                session.current_step = 2
                banks = payment_service.get_bank_ussd_codes()
                bank_list = "\n".join([f"{i+1}. {info['name']}" 
                                      for i, (code, info) in enumerate(list(banks.items())[:6])])
                return f"Select bank:\n{bank_list}", True
            
            elif user_input == '0':
                session.current_menu = 'main'
                return "Cancelled.\n" + self._show_main_menu(lang, user), True
        
        elif step == 2:
            try:
                bank_index = int(user_input) - 1
                banks = list(payment_service.get_bank_ussd_codes().items())
                
                if 0 <= bank_index < len(banks):
                    bank_code, bank_info = banks[bank_index]
                    produce_id = data.get('produce_id')
                    total = data.get('total', 0)
                    
                    ref = payment_service.generate_reference(f"USSD_PAY_{produce_id}")
                    email = user.email if '@sms.' not in user.email else f"ussd_{user.phone_number.replace('+', '')}@tradoja.com"
                    
                    result = payment_service.charge_ussd(email, total, ref, bank_code)
                    
                    session.current_menu = 'main'
                    session.current_step = 0
                    
                    if result.get('success'):
                        from models import Order
                        produce = Produce.query.get(produce_id)
                        
                        transaction = Transaction(
                            reference=ref,
                            user_id=user.id,
                            transaction_type='produce_sale',
                            base_amount=data.get('amount', 0),
                            platform_fee=data.get('fee', 0),
                            total_amount=total,
                            payment_method='ussd',
                            status='pending',
                            produce_id=produce_id
                        )
                        db.session.add(transaction)
                        
                        order = Order(
                            farmer_id=produce.farmer_id if produce else user.id,
                            buyer_id=user.id,
                            produce_id=produce_id,
                            quantity=str(produce.quantity) if produce else '',
                            total_amount=total,
                            platform_fee=data.get('fee', 0),
                            status='pending',
                            pickup_location=produce.listing_location or '' if produce else '',
                            source_channel='ussd'
                        )
                        order.generate_order_code()
                        db.session.add(order)
                        
                        if produce:
                            produce.is_available = False
                            produce.buyer_id = user.id
                        
                        db.session.commit()
                        
                        return (f"Dial to pay:\n{result['ussd_code']}\n"
                               f"Amount: N{total:,.0f}\n"
                               f"Order: {order.order_code}\n"
                               f"Ref: {ref}"), False
                    else:
                        return f"Failed: {result.get('message')}", False
                else:
                    return "Invalid bank. Try again:", True
                    
            except ValueError:
                return "Enter bank number:", True
        
        return get_message('error', lang), False
    
    def _show_trader_verify_menu(self, session, user, lang: str) -> Tuple[str, bool]:
        """Show trader verification menu with value-add services"""
        session.current_step = 0
        
        status = user.trader_verification_status or 'not_applied'
        if status == 'pending':
            return (f"Application pending review.\n"
                   f"Submitted services will be verified within 24-48 hours.\n"
                   f"0. Back"), True
        
        return ("Trader Verification\n"
                "Select value-add services you provide:\n"
                "1. Transport (own/hire vehicles)\n"
                "2. Storage (warehouse/cold storage)\n"
                "3. Aggregation (collect from farmers)\n"
                "4. Processing (cleaning/grading)\n"
                "5. Working Capital (pay farmers upfront)\n"
                "6. Quality Grading (certification)\n"
                "\nEnter numbers separated by comma\n"
                "Example: 1,2,5\n"
                "0. Cancel"), True
    
    def _handle_trader_verify(
        self, 
        session, 
        user_input: str, 
        user, 
        lang: str
    ) -> Tuple[str, bool]:
        """Handle trader verification flow"""
        step = session.current_step
        data = session.get_session_data()
        
        if user_input == '0':
            session.current_menu = 'main'
            session.current_step = 0
            return "Cancelled.\n" + self._show_main_menu(lang, user), True
        
        if step == 0:
            service_map = {
                '1': 'transport',
                '2': 'storage',
                '3': 'aggregation',
                '4': 'processing',
                '5': 'working_capital',
                '6': 'quality_grading'
            }
            
            selections = [s.strip() for s in user_input.split(',')]
            selected_services = []
            
            for s in selections:
                if s in service_map:
                    selected_services.append(service_map[s])
            
            if not selected_services:
                return "Select at least one service (1-6):", True
            
            data['services'] = selected_services
            session.update_session_data('services', selected_services)
            session.current_step = 1
            
            service_names = {
                'transport': 'Transport',
                'storage': 'Storage',
                'aggregation': 'Aggregation',
                'processing': 'Processing',
                'working_capital': 'Working Capital',
                'quality_grading': 'Quality Grading'
            }
            
            names = [service_names.get(s, s) for s in selected_services]
            return (f"Confirm verification application:\n"
                   f"Services: {', '.join(names)}\n\n"
                   f"Note: You may need to upload proof documents via web or agent.\n\n"
                   f"1. Submit Application\n"
                   f"0. Cancel"), True
        
        elif step == 1:
            if user_input == '1':
                services = data.get('services', [])
                
                try:
                    user.set_value_services(services)
                    user.trader_verification_status = 'pending'
                    user.trader_verification_date = datetime.utcnow()
                    db.session.commit()
                    
                    session.current_menu = 'main'
                    session.current_step = 0
                    
                    return (f"Application submitted!\n"
                           f"Services: {len(services)} selected\n"
                           f"Review: 24-48 hours\n\n"
                           f"Upload proof docs via web or agent to speed up approval."), False
                           
                except Exception as e:
                    current_app.logger.error(f"Trader verify error: {e}")
                    return "Failed to submit. Try again later.", False
            else:
                session.current_menu = 'main'
                session.current_step = 0
                return "Cancelled.\n" + self._show_main_menu(lang, user), True
        
        return get_message('error', lang), False


# Singleton instance
ussd_service = USSDService()
