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
                '5': 'register'
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
            from models import User, USSDSession, Produce
            self.db = db
            self.User = User
            self.USSDSession = USSDSession
            self.Produce = Produce
    
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
