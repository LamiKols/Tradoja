"""
WhatsApp Service for Tradoja
Full trading channel via WhatsApp - registration, listing, buying, SabiBuy, tracking
Uses abstraction layer: works with simulator now, Twilio later
"""

import re
import os
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)


class WhatsAppService:
    
    COMMANDS_HELP = {
        'REG': 'Register: REG [name] [location] [role]',
        'SELL': 'List produce: SELL [crop] [qty] [price] [location]',
        'MARKET': 'Browse: MARKET [crop] or MARKET ALL',
        'BUY': 'Purchase: BUY [listing_id] [qty]',
        'SABIBUY': 'Group buy: SABIBUY LIST / SABIBUY JOIN [code] [qty]',
        'ORDERS': 'View your orders',
        'TRACK': 'Track order: TRACK [order_code]',
        'RATE': 'Rate: RATE [order_code] [1-5] [comment]',
        'BAL': 'Check wallet balance',
        'PRICE': 'Price check: PRICE [crop]',
        'VERIFY': 'Upgrade to verified account',
        'HELP': 'Show this help menu',
    }
    
    def __init__(self):
        self.twilio_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        self.twilio_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        self.twilio_wa_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')
        self._simulation_mode = True
        self._sessions = {}
        
        if self.twilio_sid and self.twilio_token and len(self.twilio_sid) > 10:
            try:
                from twilio.rest import Client
                self.client = Client(self.twilio_sid, self.twilio_token)
                self._simulation_mode = False
                logger.info("Twilio WhatsApp client initialized")
            except ImportError:
                logger.warning("Twilio package not installed, running in simulation mode")
                self.client = None
            except Exception as e:
                logger.warning(f"Twilio init failed: {e}, running in simulation mode")
                self.client = None
        else:
            self.client = None
            logger.info("WhatsApp service running in simulation mode (no Twilio credentials)")
    
    def send_message(self, to_number, message, media_url=None):
        """Send WhatsApp message (or simulate)"""
        try:
            to_number = self._normalize_phone(to_number)
            
            self._log_interaction(
                phone_number=to_number,
                message_type='outgoing',
                content=message,
                content_type='image' if media_url else 'text',
                status='simulated' if self._simulation_mode else 'sent'
            )
            
            if self._simulation_mode or not self.client:
                return message
            
            kwargs = {
                'body': message,
                'from_': f'whatsapp:{self.twilio_wa_number}',
                'to': f'whatsapp:{to_number}'
            }
            if media_url:
                kwargs['media_url'] = [media_url]
            
            msg = self.client.messages.create(**kwargs)
            return message
            
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return message
    
    def simulate_incoming(self, phone_number, message, media_url=None):
        """Simulate incoming WhatsApp message for demo"""
        self._simulation_mode = True
        try:
            return self.process_incoming(phone_number, message, media_url=media_url)
        finally:
            pass
    
    def process_incoming(self, phone_number, message, media_url=None):
        """Process incoming WhatsApp message and route to handler"""
        try:
            phone_number = self._normalize_phone(phone_number)
            original_message = message.strip()
            message_upper = message.strip().upper()
            
            self._log_interaction(
                phone_number=phone_number,
                message_type='incoming',
                content=original_message,
                content_type='image' if media_url else 'text',
                status='received'
            )
            
            if phone_number in self._sessions:
                session = self._sessions[phone_number]
                if session.get('expires_at', datetime.min) > datetime.utcnow():
                    return self._handle_session_input(phone_number, original_message, session, media_url)
                else:
                    del self._sessions[phone_number]
            
            parts = message_upper.split()
            if not parts:
                return self._send_welcome(phone_number)
            
            command = parts[0]
            
            if command in ('HI', 'HELLO', 'HEY', 'START', 'MENU'):
                return self._send_welcome(phone_number)
            elif command in ('REG', 'JOIN', 'REGISTER'):
                return self._handle_registration(phone_number, parts, original_message)
            elif command in ('SELL', 'LIST'):
                return self._handle_sell(phone_number, parts, original_message, media_url)
            elif command == 'MARKET':
                return self._handle_market(phone_number, parts)
            elif command == 'BUY':
                return self._handle_buy(phone_number, parts)
            elif command == 'SABIBUY':
                return self._handle_sabibuy(phone_number, parts, original_message)
            elif command == 'ORDERS':
                return self._handle_orders(phone_number)
            elif command == 'TRACK':
                return self._handle_track(phone_number, parts)
            elif command == 'RATE':
                return self._handle_rate(phone_number, parts, original_message)
            elif command in ('BAL', 'BALANCE', 'WALLET'):
                return self._handle_balance(phone_number)
            elif command == 'PRICE':
                return self._handle_price(phone_number, parts)
            elif command in ('VERIFY', 'UPGRADE'):
                return self._handle_verify(phone_number)
            elif command == 'HELP':
                return self._send_help(phone_number)
            elif command == 'MYLIST' or command == 'MYLISTINGS':
                return self._handle_my_listings(phone_number)
            elif command == 'STATUS':
                return self._handle_status(phone_number)
            elif command == 'ACCEPT':
                return self._handle_accept_order(phone_number, parts)
            elif command in ('COMPLAINT', 'DISPUTE', 'REPORT'):
                return self._handle_complaint(phone_number, parts, original_message)
            elif command == 'LOG':
                return self._handle_ledger_log(phone_number, parts, original_message)
            elif command == 'MYLOG':
                return self._handle_ledger_summary(phone_number)
            else:
                return self._handle_unknown(phone_number, original_message)
            
        except Exception as e:
            logger.error(f"WhatsApp processing error: {e}")
            return self.send_message(phone_number, 
                "Sorry, something went wrong. Please try again or send HELP for commands.")
    
    def _send_welcome(self, phone_number):
        """Send welcome menu"""
        from models import User
        user = User.query.filter_by(phone_number=phone_number).first()
        
        if user:
            from services.tradojaiq_service import tradojaiq
            trust = tradojaiq.calculate_trust_score(user)
            alerts = tradojaiq.get_farmer_alert(user)
            
            msg = f"Welcome back, {user.name}! {trust['emoji']} {trust['tier']}\n\n"
            
            if alerts:
                msg += "📢 *Market Alerts:*\n"
                for alert in alerts[:2]:
                    msg += f"• {alert}\n"
                msg += "\n"
            
            msg += "*What would you like to do?*\n\n"
            if user.is_farmer():
                msg += "🌾 SELL - List your produce\n"
                msg += "📦 ORDERS - View your orders\n"
                msg += "📊 PRICE [crop] - Check market prices\n"
                msg += "📋 MYLIST - View your listings\n"
            elif user.is_buyer():
                msg += "🛒 MARKET - Browse produce\n"
                msg += "📦 ORDERS - View your orders\n"
                msg += "🤝 SABIBUY - Group buying\n"
            msg += "💰 BAL - Wallet balance\n"
            msg += "❓ HELP - All commands\n"
        else:
            msg = ("🌿 *Welcome to Tradoja!*\n\n"
                   "Africa's farmer-first marketplace.\n\n"
                   "📱 *Get started:*\n"
                   "REG [name] [location] [crop]\n\n"
                   "*Example:*\n"
                   "REG Amina Kano Tomatoes\n\n"
                   "Or send HELP for all commands")
        
        return self.send_message(phone_number, msg)
    
    def _send_help(self, phone_number):
        """Send help message with all commands"""
        msg = "📋 *Tradoja WhatsApp Commands*\n\n"
        msg += "*🔑 Account:*\n"
        msg += "• REG [name] [location] [crop] - Register\n"
        msg += "• VERIFY - Upgrade account\n"
        msg += "• STATUS - Account info\n\n"
        msg += "*🌾 Selling:*\n"
        msg += "• SELL [crop] [qty] [price] - List produce\n"
        msg += "• MYLIST - Your listings\n"
        msg += "• PRICE [crop] - Market prices\n\n"
        msg += "*🛒 Buying:*\n"
        msg += "• MARKET [crop] - Browse produce\n"
        msg += "• MARKET ALL - See everything\n"
        msg += "• BUY [id] [qty] - Purchase\n\n"
        msg += "*🤝 SabiBuy Group-Buy:*\n"
        msg += "• SABIBUY LIST - Active campaigns\n"
        msg += "• SABIBUY JOIN [code] [qty] - Join\n\n"
        msg += "*📦 Orders:*\n"
        msg += "• ORDERS - Your orders\n"
        msg += "• TRACK [code] - Track order\n"
        msg += "• RATE [code] [1-5] [comment]\n"
        msg += "• ACCEPT [code] - Accept order\n\n"
        msg += "*💰 Payments:*\n"
        msg += "• BAL - Wallet balance\n\n"
        msg += "*📞 Support:*\n"
        msg += "• COMPLAINT [details] - File complaint\n"
        msg += "• HELP - This menu"
        
        return self.send_message(phone_number, msg)
    
    def _handle_registration(self, phone_number, parts, original):
        """Handle user registration"""
        from models import db, User
        from werkzeug.security import generate_password_hash
        
        existing = User.query.filter_by(phone_number=phone_number).first()
        if existing:
            status = "LITE" if existing.is_lite_account() else "Verified ✅"
            msg = (f"You're already registered, {existing.name}!\n"
                   f"Status: {status}\n"
                   f"Role: {existing.role.title()}\n\n"
                   f"Send HELP for commands.")
            return self.send_message(phone_number, msg)
        
        if len(parts) < 4:
            msg = ("📝 *Register on Tradoja*\n\n"
                   "Send: REG [name] [location] [main crop/role]\n\n"
                   "*Examples:*\n"
                   "• REG Amina Kano Tomatoes _(farmer)_\n"
                   "• REG Chidi Lagos BUYER _(buyer)_\n\n"
                   "Your LITE account lets you start trading immediately!")
            return self.send_message(phone_number, msg)
        
        name = parts[1].title()
        location = parts[2].title()
        role_or_crop = ' '.join(parts[3:])
        
        role = 'farmer'
        if role_or_crop.upper() in ('BUYER', 'BUY'):
            role = 'buyer'
        
        try:
            user = User(
                name=name,
                phone_number=phone_number,
                email=f"{phone_number.replace('+', '')}@wa.tradoja.com",
                role=role,
                sms_enabled=True,
                whatsapp_id=phone_number,
                source_channel='whatsapp',
                location=location,
                registration_status='lite',
                lite_registration_date=datetime.utcnow(),
                sms_registration_date=datetime.utcnow()
            )
            
            temp_password = secrets.token_hex(8)
            user.password_hash = generate_password_hash(temp_password)
            
            db.session.add(user)
            db.session.commit()
            
            from services.tradojaiq_service import tradojaiq
            trust = tradojaiq.calculate_trust_score(user)
            
            msg = (f"✅ *Welcome to Tradoja, {name}!*\n\n"
                   f"🏷 Status: LITE Account\n"
                   f"📍 Location: {location}\n"
                   f"👤 Role: {role.title()}\n"
                   f"{trust['emoji']} Trust: {trust['tier']}\n\n")
            
            if role == 'farmer':
                msg += ("*Start selling:*\n"
                       "SELL [crop] [qty] [price]\n"
                       "Example: SELL Tomatoes 100 5000\n\n")
            else:
                msg += ("*Start buying:*\n"
                       "MARKET ALL - Browse produce\n"
                       "SABIBUY LIST - Group buy campaigns\n\n")
            
            msg += ("💡 LITE accounts: max 3 listings, N50,000/transaction\n"
                   "Send VERIFY to upgrade for unlimited access!")
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"WhatsApp registration error: {e}")
            from models import db
            db.session.rollback()
            return self.send_message(phone_number,
                "Registration failed. Please try again or contact support.")
    
    def _handle_sell(self, phone_number, parts, original, media_url=None):
        """Handle produce listing"""
        from models import db, User, Produce
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if not user.can_create_listing():
            return self.send_message(phone_number,
                "⚠️ You've reached the maximum of 3 listings for LITE accounts.\n"
                "Send VERIFY to upgrade for unlimited listings!")
        
        if len(parts) < 4:
            msg = ("🌾 *List Your Produce*\n\n"
                   "Send: SELL [crop] [quantity] [price per unit]\n\n"
                   "*Examples:*\n"
                   "• SELL Tomatoes 100 5000\n"
                   "• SELL Rice 50 25000\n"
                   "• SELL Pepper 200 3000\n\n"
                   "📸 You can also send a photo with your listing!")
            return self.send_message(phone_number, msg)
        
        crop_name = parts[1].title()
        
        try:
            quantity_str = parts[2]
            quantity_num = float(re.sub(r'[^\d.]', '', quantity_str))
        except (ValueError, IndexError):
            return self.send_message(phone_number,
                "Please provide a valid quantity. Example: SELL Tomatoes 100 5000")
        
        try:
            price = float(re.sub(r'[^\d.]', '', parts[3]))
        except (ValueError, IndexError):
            return self.send_message(phone_number,
                "Please provide a valid price. Example: SELL Tomatoes 100 5000")
        
        if not user.can_transact_amount(price * quantity_num):
            return self.send_message(phone_number,
                f"⚠️ Total value exceeds N50,000 limit for LITE accounts.\n"
                f"Send VERIFY to upgrade for higher limits!")
        
        try:
            from services.tradojaiq_service import tradojaiq
            guidance = tradojaiq.get_price_guidance(crop_name, price, user.location)
            
            produce = Produce(
                name=crop_name,
                quantity=str(int(quantity_num)),
                price=price,
                price_unit='NGN',
                farmer_id=user.id,
                source_channel='whatsapp',
                listing_location=user.location or '',
                is_available=True,
                contact_method='whatsapp'
            )
            
            db.session.add(produce)
            db.session.commit()
            
            msg = (f"✅ *Produce Listed Successfully!*\n\n"
                   f"📋 Listing #{produce.id}\n"
                   f"🌾 {crop_name}\n"
                   f"📦 Quantity: {int(quantity_num)} units\n"
                   f"💰 Price: N{price:,.0f}/unit\n"
                   f"📍 Location: {user.location or 'Not set'}\n\n")
            
            if guidance['message']:
                msg += f"📊 *Price Intel:* {guidance['message']}\n"
            if guidance.get('regional_context'):
                msg += f"📍 {guidance['regional_context']}\n"
            
            msg += f"\nYour listing is now live on the marketplace!"
            
            if media_url:
                msg += "\n📸 Photo received and attached to listing."
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"WhatsApp sell error: {e}")
            db.session.rollback()
            return self.send_message(phone_number,
                "Failed to create listing. Please try again.")
    
    def _handle_market(self, phone_number, parts):
        """Handle marketplace browsing"""
        from models import Produce, User
        from services.tradojaiq_service import tradojaiq
        
        user = self._get_user(phone_number)
        
        query = Produce.query.filter_by(is_available=True, is_sold=False)
        
        crop_filter = None
        if len(parts) > 1 and parts[1] != 'ALL':
            crop_filter = ' '.join(parts[1:]).title()
            query = query.filter(Produce.name.ilike(f'%{crop_filter}%'))
        
        listings = query.order_by(Produce.date_listed.desc()).limit(10).all()
        
        if not listings:
            crop_text = f" for '{crop_filter}'" if crop_filter else ""
            return self.send_message(phone_number,
                f"No available produce{crop_text}.\n\n"
                f"Try: MARKET ALL to see everything\n"
                f"Or: MARKET [crop name]")
        
        msg = f"🛒 *Marketplace*"
        if crop_filter:
            msg += f" - {crop_filter}"
        msg += f"\n{'─' * 25}\n\n"
        
        for p in listings:
            farmer = User.query.get(p.farmer_id)
            trust = tradojaiq.calculate_trust_score(farmer) if farmer else {'emoji': '', 'tier': ''}
            
            msg += f"*#{p.id}* {p.name}\n"
            msg += f"  💰 N{p.price:,.0f} | 📦 {p.quantity}\n"
            msg += f"  📍 {p.listing_location or 'N/A'}"
            if farmer:
                msg += f" | {trust['emoji']} {farmer.name}\n"
            else:
                msg += "\n"
            msg += "\n"
        
        msg += f"{'─' * 25}\n"
        msg += f"To buy: BUY [id] [quantity]\n"
        msg += f"Example: BUY {listings[0].id} 10"
        
        return self.send_message(phone_number, msg)
    
    def _handle_buy(self, phone_number, parts):
        """Handle produce purchase"""
        from models import db, User, Produce, Order, Transaction
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 2:
            return self.send_message(phone_number,
                "To buy: BUY [listing_id] [quantity]\n"
                "Example: BUY 5 10\n\n"
                "Browse first: MARKET ALL")
        
        try:
            listing_id = int(parts[1])
        except ValueError:
            return self.send_message(phone_number, "Invalid listing ID. Use a number.")
        
        produce = Produce.query.get(listing_id)
        if not produce:
            return self.send_message(phone_number, f"Listing #{listing_id} not found.")
        
        if not produce.is_available or produce.is_sold:
            return self.send_message(phone_number, f"Listing #{listing_id} is no longer available.")
        
        if produce.farmer_id == user.id:
            return self.send_message(phone_number, "You can't buy your own listing!")
        
        quantity = produce.quantity
        if len(parts) > 2:
            try:
                quantity = str(int(parts[2]))
            except ValueError:
                quantity = produce.quantity
        
        try:
            qty_num = float(re.sub(r'[^\d.]', '', quantity))
        except ValueError:
            qty_num = 1
        
        total_amount = produce.price * qty_num
        platform_fee = total_amount * 0.02
        grand_total = total_amount + platform_fee
        
        if not user.can_transact_amount(grand_total):
            return self.send_message(phone_number,
                f"⚠️ Total N{grand_total:,.0f} exceeds N50,000 LITE limit.\n"
                f"Send VERIFY to upgrade!")
        
        try:
            import uuid
            order_ref = f"WA_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6].upper()}"
            
            order = Order(
                farmer_id=produce.farmer_id,
                buyer_id=user.id,
                produce_id=produce.id,
                quantity=quantity,
                total_amount=grand_total,
                platform_fee=platform_fee,
                status='pending',
                pickup_location=produce.listing_location or '',
                source_channel='whatsapp'
            )
            order.generate_order_code()
            
            transaction = Transaction(
                reference=order_ref,
                user_id=user.id,
                transaction_type='produce_sale',
                base_amount=total_amount,
                platform_fee=platform_fee,
                total_amount=grand_total,
                payment_method='whatsapp_pending',
                status='pending',
                produce_id=produce.id
            )
            
            produce.is_available = False
            produce.buyer_id = user.id
            produce.sale_date = datetime.utcnow()
            
            db.session.add(order)
            db.session.add(transaction)
            db.session.commit()
            
            farmer = User.query.get(produce.farmer_id)
            from services.tradojaiq_service import tradojaiq
            trust = tradojaiq.calculate_trust_score(farmer) if farmer else {'emoji': '', 'tier': ''}
            
            callback_url = os.environ.get('REPLIT_DEV_DOMAIN', '')
            if callback_url:
                callback_url = f"https://{callback_url}/payment/callback"
            
            msg = (f"🛒 *Order Created!*\n\n"
                   f"📋 Order: *{order.order_code}*\n"
                   f"🌾 {produce.name} - {quantity} units\n"
                   f"👨‍🌾 Farmer: {farmer.name if farmer else 'Unknown'} {trust['emoji']}\n"
                   f"📍 {produce.listing_location or 'N/A'}\n\n"
                   f"💰 *Payment Summary:*\n"
                   f"  Produce: N{total_amount:,.0f}\n"
                   f"  Platform fee: N{platform_fee:,.0f}\n"
                   f"  *Total: N{grand_total:,.0f}*\n\n")
            
            if callback_url:
                msg += (f"💳 *Pay via Paystack:*\n"
                       f"{callback_url}?ref={order_ref}\n\n")
            
            msg += (f"📦 Track: TRACK {order.order_code}\n"
                   f"❌ Cancel: CANCEL {order.order_code}")
            
            if farmer and farmer.phone_number:
                farmer_msg = (f"📦 *New Order!*\n\n"
                             f"Order: {order.order_code}\n"
                             f"🌾 {produce.name} - {quantity} units\n"
                             f"💰 N{total_amount:,.0f}\n"
                             f"👤 Buyer: {user.name}\n\n"
                             f"Reply ACCEPT {order.order_code} to confirm")
                self.send_message(farmer.phone_number, farmer_msg)
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"WhatsApp buy error: {e}")
            db.session.rollback()
            return self.send_message(phone_number,
                "Order creation failed. Please try again.")
    
    def _handle_sabibuy(self, phone_number, parts, original):
        """Handle SabiBuy commands"""
        from models import db, SabiBuy, SabiBuyOrder, User, Produce
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 2:
            msg = ("🤝 *SabiBuy Group-Buy*\n\n"
                   "Buy together, save together!\n\n"
                   "• SABIBUY LIST - Active campaigns\n"
                   "• SABIBUY JOIN [code] [qty] - Join a campaign\n"
                   "• SABIBUY CREATE [listing_id] [price] [min_qty] [location]\n")
            return self.send_message(phone_number, msg)
        
        sub_command = parts[1]
        
        if sub_command == 'LIST':
            campaigns = SabiBuy.query.filter_by(status='active').order_by(SabiBuy.created_at.desc()).limit(10).all()
            
            if not campaigns:
                return self.send_message(phone_number,
                    "No active SabiBuy campaigns right now.\n"
                    "Start one: SABIBUY CREATE [listing_id] [price] [min_qty] [location]")
            
            msg = "🤝 *Active SabiBuy Campaigns*\n"
            msg += f"{'─' * 25}\n\n"
            
            for c in campaigns:
                produce_name = c.produce.name if c.produce else 'Unknown'
                progress = c.calculate_progress_percentage()
                msg += f"*{c.code}*\n"
                msg += f"  🌾 {produce_name}\n"
                msg += f"  💰 N{c.selling_price:,.0f}/{c.price_unit}\n"
                msg += f"  📊 {c.current_quantity}/{c.minimum_quantity} ({progress}%)\n"
                msg += f"  📍 {c.delivery_lga or c.delivery_market or 'N/A'}\n\n"
            
            msg += f"Join: SABIBUY JOIN [code] [quantity]"
            return self.send_message(phone_number, msg)
        
        elif sub_command == 'JOIN':
            if len(parts) < 4:
                return self.send_message(phone_number,
                    "To join: SABIBUY JOIN [campaign_code] [quantity]\n"
                    "Example: SABIBUY JOIN AMINA-SABIBUY-5K89 10")
            
            code = parts[2].upper()
            try:
                qty = int(parts[3])
            except ValueError:
                return self.send_message(phone_number, "Invalid quantity.")
            
            campaign = SabiBuy.query.filter_by(code=code, status='active').first()
            if not campaign:
                return self.send_message(phone_number,
                    f"Campaign {code} not found or not active.\n"
                    f"Send SABIBUY LIST to see available campaigns.")
            
            total = campaign.selling_price * qty
            
            if not user.can_transact_amount(total):
                return self.send_message(phone_number,
                    f"⚠️ Total N{total:,.0f} exceeds LITE limit.\nSend VERIFY to upgrade!")
            
            try:
                sb_order = SabiBuyOrder(
                    sabibuy_id=campaign.id,
                    buyer_id=user.id,
                    buyer_phone=phone_number,
                    buyer_name=user.name,
                    quantity=qty,
                    unit_price=campaign.selling_price,
                    total_amount=total,
                    payment_status='pending',
                    source_channel='whatsapp'
                )
                
                campaign.current_quantity += qty
                campaign.total_escrow += total
                
                db.session.add(sb_order)
                db.session.commit()
                
                progress = campaign.calculate_progress_percentage()
                
                msg = (f"✅ *Joined SabiBuy Campaign!*\n\n"
                       f"📋 Campaign: {code}\n"
                       f"🌾 {campaign.produce.name if campaign.produce else 'Produce'}\n"
                       f"📦 Your quantity: {qty} {campaign.price_unit}\n"
                       f"💰 Total: N{total:,.0f}\n"
                       f"📊 Campaign progress: {progress}%\n\n")
                
                if campaign.is_ready_to_close():
                    msg += "🎉 Minimum quantity reached! Campaign ready to book!\n"
                else:
                    remaining = campaign.minimum_quantity - campaign.current_quantity
                    msg += f"📢 {remaining} more {campaign.price_unit} needed to close batch.\n"
                    msg += f"Share code *{code}* with friends!"
                
                return self.send_message(phone_number, msg)
                
            except Exception as e:
                logger.error(f"SabiBuy join error: {e}")
                db.session.rollback()
                return self.send_message(phone_number, "Failed to join campaign. Try again.")
        
        elif sub_command == 'CREATE':
            if len(parts) < 5:
                return self.send_message(phone_number,
                    "Create campaign:\n"
                    "SABIBUY CREATE [listing_id] [selling_price] [min_qty] [location]\n"
                    "Example: SABIBUY CREATE 5 6000 50 Lagos")
            
            try:
                listing_id = int(parts[2])
                selling_price = float(parts[3])
                min_qty = int(parts[4])
                location = ' '.join(parts[5:]).title() if len(parts) > 5 else user.location or ''
            except (ValueError, IndexError):
                return self.send_message(phone_number, "Invalid parameters. Check format and try again.")
            
            produce = Produce.query.get(listing_id)
            if not produce or not produce.is_available:
                return self.send_message(phone_number, f"Listing #{listing_id} not available.")
            
            if selling_price <= produce.price:
                return self.send_message(phone_number,
                    f"Selling price (N{selling_price:,.0f}) must be higher than farm price (N{produce.price:,.0f}).")
            
            try:
                code = SabiBuy.generate_code(user.name, selling_price)
                
                campaign = SabiBuy(
                    code=code,
                    organizer_id=user.id,
                    produce_id=produce.id,
                    farm_price=produce.price,
                    selling_price=selling_price,
                    minimum_quantity=min_qty,
                    delivery_lga=location,
                    delivery_state=location,
                    source_channel='whatsapp',
                    status='active',
                    expires_at=datetime.utcnow() + timedelta(days=7)
                )
                
                db.session.add(campaign)
                db.session.commit()
                
                profit_per_unit = selling_price - produce.price
                total_potential = profit_per_unit * min_qty
                
                msg = (f"✅ *SabiBuy Campaign Created!*\n\n"
                       f"📋 Code: *{code}*\n"
                       f"🌾 {produce.name}\n"
                       f"💰 Farm price: N{produce.price:,.0f}\n"
                       f"💰 Your price: N{selling_price:,.0f}\n"
                       f"📊 Min batch: {min_qty} units\n"
                       f"📍 Delivery: {location}\n"
                       f"💵 Profit potential: N{total_potential:,.0f}\n\n"
                       f"Share code *{code}* to attract buyers!\n"
                       f"Expires in 7 days.")
                
                return self.send_message(phone_number, msg)
                
            except Exception as e:
                logger.error(f"SabiBuy create error: {e}")
                db.session.rollback()
                return self.send_message(phone_number, "Failed to create campaign. Try again.")
        
        return self.send_message(phone_number, "Unknown SabiBuy command. Send SABIBUY for options.")
    
    def _handle_orders(self, phone_number):
        """Show user's orders"""
        from models import Order, User
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        orders_as_buyer = Order.query.filter_by(buyer_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
        orders_as_seller = Order.query.filter_by(farmer_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
        
        if not orders_as_buyer and not orders_as_seller:
            return self.send_message(phone_number,
                "📦 No orders yet.\n\n"
                "• MARKET ALL - Browse produce to buy\n"
                "• SELL [crop] [qty] [price] - List produce to sell")
        
        msg = "📦 *Your Orders*\n"
        msg += f"{'─' * 25}\n\n"
        
        if orders_as_seller:
            msg += "*📤 Orders Received (Seller):*\n"
            for o in orders_as_seller[:5]:
                buyer = User.query.get(o.buyer_id)
                channel_badge = f"[{o.source_channel}]" if o.source_channel else ""
                msg += (f"• *{o.order_code}* {channel_badge}\n"
                       f"  {o.produce.name if o.produce else 'N/A'} | N{o.total_amount:,.0f}\n"
                       f"  Buyer: {buyer.name if buyer else 'N/A'} | Status: {o.status.title()}\n\n")
        
        if orders_as_buyer:
            msg += "*📥 Orders Placed (Buyer):*\n"
            for o in orders_as_buyer[:5]:
                farmer = User.query.get(o.farmer_id)
                channel_badge = f"[{o.source_channel}]" if o.source_channel else ""
                msg += (f"• *{o.order_code}* {channel_badge}\n"
                       f"  {o.produce.name if o.produce else 'N/A'} | N{o.total_amount:,.0f}\n"
                       f"  Farmer: {farmer.name if farmer else 'N/A'} | Status: {o.status.title()}\n\n")
        
        msg += "Track: TRACK [order_code]"
        return self.send_message(phone_number, msg)
    
    def _handle_track(self, phone_number, parts):
        """Track a specific order"""
        from models import Order, User
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 2:
            return self.send_message(phone_number,
                "Track order: TRACK [order_code]\nExample: TRACK ORD-1234")
        
        code = parts[1].upper()
        if not code.startswith('ORD-'):
            code = f"ORD-{code}"
        
        order = Order.query.filter_by(order_code=code).first()
        if not order:
            return self.send_message(phone_number, f"Order {code} not found.")
        
        if order.buyer_id != user.id and order.farmer_id != user.id:
            return self.send_message(phone_number, "You don't have access to this order.")
        
        farmer = User.query.get(order.farmer_id)
        buyer = User.query.get(order.buyer_id)
        
        status_emojis = {
            'pending': '⏳', 'accepted': '✅', 'pickup_confirmed': '📦',
            'in_transit': '🚚', 'delivered': '📬', 'completed': '✅',
            'cancelled': '❌', 'disputed': '⚠️'
        }
        emoji = status_emojis.get(order.status, '📋')
        
        msg = (f"📦 *Order Tracking: {code}*\n"
               f"{'─' * 25}\n\n"
               f"{emoji} Status: *{order.get_status_display()}*\n\n"
               f"🌾 {order.produce.name if order.produce else 'N/A'}\n"
               f"📦 Qty: {order.quantity}\n"
               f"💰 Total: N{order.total_amount:,.0f}\n"
               f"👨‍🌾 Farmer: {farmer.name if farmer else 'N/A'}\n"
               f"👤 Buyer: {buyer.name if buyer else 'N/A'}\n"
               f"📍 Pickup: {order.pickup_location or 'N/A'}\n"
               f"🕐 Created: {order.created_at.strftime('%b %d, %Y %H:%M') if order.created_at else 'N/A'}\n"
               f"📱 Channel: {order.source_channel or 'web'}\n")
        
        if order.last_location:
            msg += f"📍 Last location: {order.last_location}\n"
        
        if order.delivery_otp and order.farmer_id == user.id:
            msg += f"\n🔑 Delivery OTP: {order.delivery_otp}\n"
        
        return self.send_message(phone_number, msg)
    
    def _handle_rate(self, phone_number, parts, original):
        """Handle order rating"""
        from models import db, Order, User
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 3:
            return self.send_message(phone_number,
                "Rate: RATE [order_code] [1-5] [comment]\n"
                "Example: RATE ORD-1234 5 Great tomatoes!")
        
        code = parts[1].upper()
        if not code.startswith('ORD-'):
            code = f"ORD-{code}"
        
        try:
            rating = int(parts[2])
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            return self.send_message(phone_number, "Rating must be 1-5 stars.")
        
        comment = ' '.join(parts[3:]) if len(parts) > 3 else ''
        
        order = Order.query.filter_by(order_code=code).first()
        if not order:
            return self.send_message(phone_number, f"Order {code} not found.")
        
        if order.buyer_id != user.id and order.farmer_id != user.id:
            return self.send_message(phone_number, "You don't have access to this order.")
        
        try:
            if order.buyer_id == user.id:
                target_user = User.query.get(order.farmer_id)
            else:
                target_user = User.query.get(order.buyer_id)
            
            if target_user:
                total = target_user.total_ratings or 0
                current_avg = target_user.average_rating or 0
                new_total = total + 1
                new_avg = ((current_avg * total) + rating) / new_total
                target_user.average_rating = round(new_avg, 2)
                target_user.total_ratings = new_total
                
                db.session.commit()
            
            stars = '⭐' * rating
            msg = (f"✅ *Rating Submitted!*\n\n"
                   f"📋 Order: {code}\n"
                   f"{stars} ({rating}/5)\n")
            if comment:
                msg += f"💬 \"{comment}\"\n"
            msg += f"\nThank you for your feedback!"
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"Rating error: {e}")
            db.session.rollback()
            return self.send_message(phone_number, "Failed to submit rating. Try again.")
    
    def _handle_balance(self, phone_number):
        """Check wallet balance"""
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        balance = user.t2_wallet_balance or 0
        
        from services.tradojaiq_service import tradojaiq
        trust = tradojaiq.calculate_trust_score(user)
        
        msg = (f"💰 *Wallet Balance*\n\n"
               f"Balance: *N{balance:,.2f}*\n"
               f"Account: {user.name}\n"
               f"Status: {'Verified ✅' if user.is_verified_account() else 'LITE'}\n"
               f"Trust: {trust['emoji']} {trust['tier']}\n")
        
        return self.send_message(phone_number, msg)
    
    def _handle_price(self, phone_number, parts):
        """Check market prices for a crop"""
        if len(parts) < 2:
            return self.send_message(phone_number,
                "Check prices: PRICE [crop]\nExample: PRICE Tomatoes")
        
        crop = ' '.join(parts[1:]).title()
        
        from services.tradojaiq_service import tradojaiq
        msg = tradojaiq.format_price_sms(crop)
        
        return self.send_message(phone_number, msg)
    
    def _handle_verify(self, phone_number):
        """Handle verification upgrade"""
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if user.is_verified_account():
            return self.send_message(phone_number, "✅ Your account is already verified!")
        
        domain = os.environ.get('REPLIT_DEV_DOMAIN', 'tradoja.com')
        verify_url = f"https://{domain}/get-verified" if domain else "tradoja.com/get-verified"
        
        msg = (f"🔓 *Upgrade to Verified*\n\n"
               f"Verified accounts get:\n"
               f"✅ Unlimited produce listings\n"
               f"✅ Transactions up to any amount\n"
               f"✅ Higher trust score\n"
               f"✅ Priority in search results\n\n"
               f"Verification fee: *N15,000*\n\n"
               f"Complete your verification:\n"
               f"{verify_url}")
        
        return self.send_message(phone_number, msg)
    
    def _handle_my_listings(self, phone_number):
        """Show user's produce listings"""
        from models import Produce
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        listings = Produce.query.filter_by(farmer_id=user.id).order_by(Produce.date_listed.desc()).limit(10).all()
        
        if not listings:
            return self.send_message(phone_number,
                "📋 No listings yet.\n\nSELL [crop] [qty] [price] to create one!")
        
        msg = "📋 *Your Listings*\n"
        msg += f"{'─' * 25}\n\n"
        
        for p in listings:
            status = "🟢 Active" if p.is_available and not p.is_sold else "🔴 Sold"
            msg += (f"*#{p.id}* {p.name} {status}\n"
                   f"  💰 N{p.price:,.0f} | 📦 {p.quantity}\n"
                   f"  📱 {p.source_channel or 'web'}\n\n")
        
        return self.send_message(phone_number, msg)
    
    def _handle_status(self, phone_number):
        """Show account status"""
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        from models import Produce, Order
        from services.tradojaiq_service import tradojaiq
        
        trust = tradojaiq.calculate_trust_score(user)
        active_listings = Produce.query.filter_by(farmer_id=user.id, is_available=True, is_sold=False).count()
        total_orders = Order.query.filter(
            (Order.farmer_id == user.id) | (Order.buyer_id == user.id)
        ).count()
        
        msg = (f"👤 *Account Status*\n"
               f"{'─' * 25}\n\n"
               f"Name: {user.name}\n"
               f"Role: {user.role.title()}\n"
               f"Status: {'Verified ✅' if user.is_verified_account() else 'LITE'}\n"
               f"Trust: {trust['emoji']} {trust['tier']} (Score: {trust['score']})\n"
               f"📍 Location: {user.location or 'Not set'}\n"
               f"📱 Channel: {user.source_channel or 'web'}\n"
               f"📋 Active Listings: {active_listings}\n"
               f"📦 Total Orders: {total_orders}\n"
               f"💰 Wallet: N{user.t2_wallet_balance or 0:,.2f}\n"
               f"⭐ Rating: {user.average_rating or 0:.1f}/5 ({user.total_ratings or 0} reviews)\n"
               f"📅 Joined: {user.registration_date.strftime('%b %d, %Y') if user.registration_date else 'N/A'}")
        
        return self.send_message(phone_number, msg)
    
    def _handle_accept_order(self, phone_number, parts):
        """Farmer accepts an order"""
        from models import db, Order
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 2:
            return self.send_message(phone_number, "ACCEPT [order_code]\nExample: ACCEPT ORD-1234")
        
        code = parts[1].upper()
        if not code.startswith('ORD-'):
            code = f"ORD-{code}"
        
        order = Order.query.filter_by(order_code=code, farmer_id=user.id).first()
        if not order:
            return self.send_message(phone_number, f"Order {code} not found or you're not the seller.")
        
        if order.status != 'pending':
            return self.send_message(phone_number, f"Order {code} is already {order.status}.")
        
        try:
            order.status = 'accepted'
            order.accepted_at = datetime.utcnow()
            order.generate_delivery_otp()
            
            db.session.commit()
            
            msg = (f"✅ *Order Accepted!*\n\n"
                   f"📋 {code}\n"
                   f"🔑 Delivery OTP: *{order.delivery_otp}*\n\n"
                   f"Share this OTP with buyer upon delivery.\n"
                   f"Payment will be released after OTP verification.")
            
            from models import User
            buyer = User.query.get(order.buyer_id)
            if buyer and buyer.phone_number:
                buyer_msg = (f"📦 *Order {code} Accepted!*\n\n"
                            f"👨‍🌾 {user.name} accepted your order.\n"
                            f"🌾 {order.produce.name if order.produce else 'Produce'}\n"
                            f"Awaiting delivery. You'll receive an OTP to confirm.")
                self.send_message(buyer.phone_number, buyer_msg)
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"Accept order error: {e}")
            db.session.rollback()
            return self.send_message(phone_number, "Failed to accept order. Try again.")
    
    def _handle_complaint(self, phone_number, parts, original):
        """Handle complaint/dispute filing"""
        from models import db, Dispute
        
        user = self._get_user(phone_number)
        if not user:
            return self._prompt_register(phone_number)
        
        if len(parts) < 2:
            return self.send_message(phone_number,
                "File complaint: COMPLAINT [details]\n"
                "Example: COMPLAINT Order ORD-1234 never delivered")
        
        details = ' '.join(parts[1:])
        
        try:
            dispute = Dispute(
                complainant_id=user.id,
                respondent_id=user.id,
                dispute_type='other',
                severity='medium',
                subject=f'WhatsApp complaint from {user.name}',
                description=details,
                source_channel='whatsapp'
            )
            dispute.set_sla_deadlines()
            
            db.session.add(dispute)
            db.session.commit()
            
            msg = (f"📝 *Complaint Filed*\n\n"
                   f"Ticket: #DIS-{dispute.id}\n"
                   f"Status: Open\n\n"
                   f"Our team will review within 24 hours.\n"
                   f"Check status: STATUS")
            
            return self.send_message(phone_number, msg)
            
        except Exception as e:
            logger.error(f"Complaint error: {e}")
            db.session.rollback()
            return self.send_message(phone_number, "Failed to file complaint. Try again.")
    
    def _handle_unknown(self, phone_number, original):
        """Handle unrecognized commands"""
        msg = (f"I didn't understand \"{original[:50]}\".\n\n"
               f"Try these commands:\n"
               f"• HELP - See all commands\n"
               f"• MARKET ALL - Browse produce\n"
               f"• SELL [crop] [qty] [price]\n"
               f"• ORDERS - Your orders")
        return self.send_message(phone_number, msg)
    
    def _handle_session_input(self, phone_number, message, session, media_url=None):
        """Handle multi-step session input"""
        del self._sessions[phone_number]
        return self.send_message(phone_number, "Session expired. Please start again.")
    
    def _get_user(self, phone_number):
        """Get user by phone number"""
        from models import User
        phone = self._normalize_phone(phone_number)
        user = User.query.filter_by(phone_number=phone).first()
        if not user:
            alt_phone = phone.replace('+', '')
            user = User.query.filter(
                (User.phone_number == alt_phone) | 
                (User.whatsapp_id == phone) |
                (User.whatsapp_id == alt_phone)
            ).first()
        return user
    
    def _prompt_register(self, phone_number):
        """Prompt unregistered user to register"""
        return self.send_message(phone_number,
            "👋 You're not registered yet!\n\n"
            "Register: REG [name] [location] [crop/role]\n"
            "Example: REG Amina Kano Tomatoes")
    
    def _normalize_phone(self, phone):
        """Normalize phone number"""
        phone = phone.strip()
        if not phone.startswith('+'):
            if phone.startswith('234'):
                phone = f'+{phone}'
            elif phone.startswith('0'):
                phone = f'+234{phone[1:]}'
            else:
                phone = f'+{phone}'
        return phone
    
    # ── Ledger rate-limit state (per-phone, in-memory) ─────────────────────
    _ledger_rate: dict = {}

    def _ledger_rate_ok(self, phone_number: str, max_per_minute: int = 10) -> bool:
        now = datetime.utcnow()
        bucket = self._ledger_rate.get(phone_number)
        if bucket is None or (now - bucket['ts']).total_seconds() >= 60:
            self._ledger_rate[phone_number] = {'ts': now, 'count': 1}
            return True
        if bucket['count'] >= max_per_minute:
            return False
        bucket['count'] += 1
        return True

    def _handle_ledger_log(self, phone_number, parts, original_message):
        """Handle LOG SALE / LOG BUY / LOG STOCK via WhatsApp"""
        try:
            import re
            from models import db, User, LedgerEntry
            from sqlalchemy import func as sqlfunc

            if not self._ledger_rate_ok(phone_number):
                return self.send_message(phone_number,
                    "Too many LOG commands. Please wait a minute and try again.")

            user = self._get_user(phone_number)
            if not user:
                return self._prompt_register(phone_number)

            if len(parts) < 4:
                return self.send_message(phone_number,
                    "Format:\nLOG SALE RICE 5BAGS 45000\n"
                    "LOG BUY FERTILIZER 2BAGS 20000\n"
                    "LOG STOCK MAIZE 18BAGS")

            sub_cmd = parts[1].upper()
            if sub_cmd == 'SALE':
                entry_type = 'sale'
            elif sub_cmd == 'BUY':
                entry_type = 'expense'
            elif sub_cmd == 'STOCK':
                entry_type = 'stock_adjustment'
            else:
                return self.send_message(phone_number,
                    "Unknown LOG type. Use: LOG SALE, LOG BUY, or LOG STOCK")

            item = parts[2].title()
            quantity = parts[3]
            amount = None
            if len(parts) >= 5 and entry_type != 'stock_adjustment':
                try:
                    amount = float(re.sub(r'[^\d.]', '', parts[4]))
                except (ValueError, IndexError):
                    pass

            entry = LedgerEntry(
                farmer_id=user.id,
                entry_type=entry_type,
                item=item,
                quantity=quantity,
                amount=amount,
                unit='NGN',
                source_channel='whatsapp',
                raw_message=original_message,
            )
            db.session.add(entry)
            db.session.commit()

            week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())
            weekly_sales = db.session.query(sqlfunc.sum(LedgerEntry.amount)).filter(
                LedgerEntry.farmer_id == user.id,
                LedgerEntry.entry_type == 'sale',
                LedgerEntry.created_at >= week_start
            ).scalar() or 0

            if entry_type == 'stock_adjustment':
                msg = f"✅ Logged. {item} stock: {quantity}. Week sales: ₦{weekly_sales:,.0f}."
            elif entry_type == 'sale':
                amt_str = f" ₦{amount:,.0f}" if amount else ""
                msg = f"✅ Logged. {item} sale: {quantity}{amt_str}. Today's sales: ₦{weekly_sales:,.0f}."
            else:
                amt_str = f" ₦{amount:,.0f}" if amount else ""
                msg = f"✅ Logged. {item} purchase: {quantity}{amt_str}."

            return self.send_message(phone_number, msg)

        except Exception as e:
            logger.error(f"WhatsApp ledger log error: {e}")
            try:
                from models import db
                db.session.rollback()
            except Exception:
                pass
            return self.send_message(phone_number,
                "Sorry, could not log entry. Please try again.")

    def _handle_ledger_summary(self, phone_number):
        """Handle MYLOG — last 5 entries + weekly totals via WhatsApp"""
        try:
            from models import db, User, LedgerEntry
            from sqlalchemy import func as sqlfunc

            if not self._ledger_rate_ok(phone_number):
                return self.send_message(phone_number,
                    "Too many requests. Please wait a minute and try again.")

            user = self._get_user(phone_number)
            if not user:
                return self._prompt_register(phone_number)

            recent = LedgerEntry.query.filter_by(farmer_id=user.id)\
                .order_by(LedgerEntry.created_at.desc()).limit(5).all()

            if not recent:
                return self.send_message(phone_number,
                    "No ledger entries yet.\nTry: LOG SALE RICE 5BAGS 45000")

            week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())

            weekly_sales = db.session.query(sqlfunc.sum(LedgerEntry.amount)).filter(
                LedgerEntry.farmer_id == user.id,
                LedgerEntry.entry_type == 'sale',
                LedgerEntry.created_at >= week_start
            ).scalar() or 0

            weekly_expenses = db.session.query(sqlfunc.sum(LedgerEntry.amount)).filter(
                LedgerEntry.farmer_id == user.id,
                LedgerEntry.entry_type == 'expense',
                LedgerEntry.created_at >= week_start
            ).scalar() or 0

            lines = ["📒 Your last entries:"]
            for e in recent:
                date_str = e.created_at.strftime('%d/%m')
                amt_str = f" ₦{e.amount:,.0f}" if e.amount else ""
                lines.append(f"{date_str} {e.entry_type.upper()} {e.item} {e.quantity or ''}{amt_str}")

            lines.append(f"\nWeek: Sales ₦{weekly_sales:,.0f} | Expenses ₦{weekly_expenses:,.0f}")
            return self.send_message(phone_number, '\n'.join(lines))

        except Exception as e:
            logger.error(f"WhatsApp ledger summary error: {e}")
            return self.send_message(phone_number,
                "Sorry, could not retrieve your log. Please try again.")

    def _log_interaction(self, phone_number, message_type, content, content_type='text', status='received'):
        """Log WhatsApp interaction"""
        try:
            from models import db, WhatsAppInteraction
            
            interaction = WhatsAppInteraction(
                phone_number=phone_number,
                message_type=message_type,
                content_type=content_type,
                content=content[:500] if content else '',
                status=status,
                timestamp=datetime.utcnow()
            )
            
            user = self._get_user(phone_number)
            if user:
                interaction.user_id = user.id
            
            db.session.add(interaction)
            db.session.commit()
        except Exception as e:
            logger.error(f"WhatsApp log error: {e}")
            try:
                from models import db
                db.session.rollback()
            except:
                pass


whatsapp_service = None

def get_whatsapp_service():
    """Get or create WhatsApp service instance"""
    global whatsapp_service
    if whatsapp_service is None:
        whatsapp_service = WhatsAppService()
    return whatsapp_service
