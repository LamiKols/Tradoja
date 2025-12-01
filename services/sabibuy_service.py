"""
SabiBuy Group-Buy Service for AgroLink
Zero-stock group-buying engine that turns anyone into a millionaire trader
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class SabiBuyService:
    """
    Core SabiBuy service handling campaign creation, order processing,
    batch management, logistics booking, and profit payouts.
    
    Includes:
    - Buyer escrow protection (payments held until delivery confirmed)
    - Captain bond system (deposit required, forfeit on abandonment)
    - Auto-cancellation with refunds for expired campaigns
    """
    
    CAPTAIN_FEE = 5000  # ₦5,000 one-time fee
    PREMIUM_MONTHLY_FEE = 10000  # ₦10,000/month
    FREE_TIER_MAX_CAMPAIGNS = 3
    
    SUGGESTED_MARGINS = {
        'min': 4000,  # ₦4,000 minimum suggested margin
        'max': 15000,  # ₦15,000 maximum suggested margin
        'default': 6000  # ₦6,000 default margin
    }
    
    # Captain bond tiers based on batch size
    BOND_TIERS = {
        'small': {'max_quantity': 100, 'bond': 2000},   # ₦2,000 for up to 100 units
        'medium': {'max_quantity': 300, 'bond': 5000},  # ₦5,000 for up to 300 units
        'large': {'max_quantity': 500, 'bond': 8000},   # ₦8,000 for up to 500 units
        'mega': {'max_quantity': 1000, 'bond': 10000}   # ₦10,000 for 500+ units
    }
    
    def __init__(self):
        self.db = None
        self.User = None
        self.Produce = None
        self.SabiBuy = None
        self.SabiBuyOrder = None
        self.SabiBuyerProfile = None
        self.LogisticsRequest = None
        self.TransportProfile = None
    
    def _lazy_load_models(self):
        """Lazy load database models to avoid circular imports"""
        if self.db is None:
            from app import db
            from models import (User, Produce, SabiBuy, SabiBuyOrder, 
                              SabiBuyerProfile, LogisticsRequest, TransportProfile)
            self.db = db
            self.User = User
            self.Produce = Produce
            self.SabiBuy = SabiBuy
            self.SabiBuyOrder = SabiBuyOrder
            self.SabiBuyerProfile = SabiBuyerProfile
            self.LogisticsRequest = LogisticsRequest
            self.TransportProfile = TransportProfile
    
    def get_or_create_profile(self, user_id: int) -> 'SabiBuyerProfile':
        """Get or create SabiBuyer profile for a user"""
        self._lazy_load_models()
        
        profile = self.SabiBuyerProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = self.SabiBuyerProfile(user_id=user_id)
            self.db.session.add(profile)
            self.db.session.commit()
        
        return profile
    
    def suggest_selling_price(self, farm_price: float) -> Dict[str, float]:
        """
        Suggest selling price with profit margin
        Returns min, max, and suggested prices
        """
        return {
            'farm_price': farm_price,
            'min_selling_price': farm_price + self.SUGGESTED_MARGINS['min'],
            'max_selling_price': farm_price + self.SUGGESTED_MARGINS['max'],
            'suggested_selling_price': farm_price + self.SUGGESTED_MARGINS['default'],
            'min_margin': self.SUGGESTED_MARGINS['min'],
            'max_margin': self.SUGGESTED_MARGINS['max'],
            'suggested_margin': self.SUGGESTED_MARGINS['default']
        }
    
    def create_campaign(
        self,
        organizer_id: int,
        produce_id: int,
        selling_price: float,
        delivery_lga: str,
        delivery_market: str,
        delivery_state: str,
        minimum_quantity: int = 50,
        maximum_quantity: int = 500,
        expires_in_days: int = 7,
        source_channel: str = 'web'
    ) -> Dict[str, Any]:
        """
        Create a new SabiBuy campaign
        
        Returns:
            dict with 'success', 'campaign', 'code', or 'error'
        """
        self._lazy_load_models()
        
        try:
            user = self.User.query.get(organizer_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            profile = self.get_or_create_profile(organizer_id)
            if not profile.can_create_campaign():
                return {
                    'success': False, 
                    'error': f'Maximum {profile.get_max_campaigns()} active campaigns reached. Upgrade to Captain for unlimited!'
                }
            
            produce = self.Produce.query.get(produce_id)
            if not produce or not produce.is_available:
                return {'success': False, 'error': 'Produce not available'}
            
            farm_price = produce.price
            if selling_price <= farm_price:
                return {'success': False, 'error': 'Selling price must be higher than farm price'}
            
            code = self.SabiBuy.generate_code(user.name, selling_price)
            
            campaign = self.SabiBuy(
                code=code,
                organizer_id=organizer_id,
                produce_id=produce_id,
                farm_price=farm_price,
                selling_price=selling_price,
                price_unit=produce.price_unit or 'bag',
                profit_margin=selling_price - farm_price,
                minimum_quantity=minimum_quantity,
                maximum_quantity=maximum_quantity,
                delivery_lga=delivery_lga,
                delivery_market=delivery_market,
                delivery_state=delivery_state,
                status='active',
                expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
                source_channel=source_channel
            )
            
            self.db.session.add(campaign)
            
            profile.total_campaigns += 1
            profile.active_campaigns_count += 1
            
            self.db.session.commit()
            
            logger.info(f"SabiBuy campaign created: {code} by {user.name}")
            
            return {
                'success': True,
                'campaign': campaign,
                'code': code,
                'message': f'SabiBuy created! Share code: {code}'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error creating SabiBuy campaign: {e}")
            return {'success': False, 'error': str(e)}
    
    def join_campaign(
        self,
        code: str,
        buyer_phone: str,
        quantity: int,
        buyer_name: Optional[str] = None,
        buyer_id: Optional[int] = None,
        payment_method: str = 'pending',
        source_channel: str = 'web',
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Join a SabiBuy campaign by placing an order
        
        Returns:
            dict with 'success', 'order', 'payment_link', or 'error'
        """
        self._lazy_load_models()
        
        try:
            code_upper = code.upper().strip()
            campaign = self.SabiBuy.query.filter_by(code=code_upper).first()
            
            if not campaign:
                return {'success': False, 'error': 'Invalid SabiBuy code'}
            
            if campaign.status != 'active':
                return {'success': False, 'error': f'This SabiBuy is {campaign.status}'}
            
            if campaign.expires_at and campaign.expires_at < datetime.utcnow():
                campaign.status = 'expired'
                self.db.session.commit()
                return {'success': False, 'error': 'This SabiBuy has expired'}
            
            remaining_capacity = campaign.maximum_quantity - campaign.current_quantity
            if quantity > remaining_capacity:
                return {
                    'success': False, 
                    'error': f'Only {remaining_capacity} {campaign.price_unit}s available'
                }
            
            total_amount = quantity * campaign.selling_price
            
            order = self.SabiBuyOrder(
                sabibuy_id=campaign.id,
                buyer_id=buyer_id,
                buyer_phone=buyer_phone,
                buyer_name=buyer_name,
                quantity=quantity,
                unit_price=campaign.selling_price,
                total_amount=total_amount,
                payment_status='pending',
                payment_method=payment_method,
                source_channel=source_channel,
                preferred_language=language
            )
            
            self.db.session.add(order)
            self.db.session.commit()
            
            payment_link = self._generate_payment_link(order.id, total_amount)
            
            logger.info(f"SabiBuy order placed: {quantity} units for {campaign.code}")
            
            return {
                'success': True,
                'order': order,
                'order_id': order.id,
                'total_amount': total_amount,
                'campaign_code': campaign.code,
                'payment_link': payment_link,
                'message': f'Order placed! Pay ₦{total_amount:,.0f} for {quantity} {campaign.price_unit}s'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error joining SabiBuy: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_payment(
        self,
        order_id: int,
        payment_reference: str,
        payment_method: str = 'paystack'
    ) -> Dict[str, Any]:
        """
        Process payment for a SabiBuy order and update campaign progress
        """
        self._lazy_load_models()
        
        try:
            order = self.SabiBuyOrder.query.get(order_id)
            if not order:
                return {'success': False, 'error': 'Order not found'}
            
            if order.payment_status == 'paid':
                return {'success': False, 'error': 'Order already paid'}
            
            order.payment_status = 'paid'
            order.payment_method = payment_method
            order.payment_reference = payment_reference
            order.paid_at = datetime.utcnow()
            order.in_escrow = True
            
            campaign = order.campaign
            campaign.current_quantity += order.quantity
            campaign.total_escrow += order.total_amount
            campaign.total_revenue += order.total_amount
            
            if campaign.is_ready_to_close():
                self._close_batch(campaign)
            
            self.db.session.commit()
            
            progress = campaign.calculate_progress_percentage()
            
            self._send_order_notification(order, 'payment_confirmed')
            self._send_organizer_notification(campaign, 'order_received', order)
            
            logger.info(f"Payment processed for order {order_id}, campaign at {progress}%")
            
            return {
                'success': True,
                'order': order,
                'campaign_progress': progress,
                'batch_closed': campaign.status == 'closed',
                'message': f'Payment confirmed! {campaign.code} is now {progress}% full'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error processing payment: {e}")
            return {'success': False, 'error': str(e)}
    
    def _close_batch(self, campaign: 'SabiBuy'):
        """Close a batch when minimum quantity is reached"""
        campaign.status = 'closed'
        campaign.closed_at = datetime.utcnow()
        campaign.organizer_profit = campaign.calculate_organizer_profit()
        
        profile = self.SabiBuyerProfile.query.filter_by(
            user_id=campaign.organizer_id
        ).first()
        
        if profile:
            profile.pending_earnings += campaign.organizer_profit
            profile.total_gmv += campaign.total_revenue
        
        self._send_organizer_notification(campaign, 'batch_closed')
        
        logger.info(f"Batch closed for {campaign.code} with {campaign.current_quantity} units")
    
    def book_logistics(self, campaign_id: int) -> Dict[str, Any]:
        """
        Auto-book farmer produce and logistics for a closed campaign
        """
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if campaign.status != 'closed':
                return {'success': False, 'error': 'Campaign not ready for booking'}
            
            logistics_request = self.LogisticsRequest(
                requester_id=campaign.organizer_id,
                produce_id=campaign.produce_id,
                pickup_location=campaign.produce.listing_location or campaign.produce.farmer.location,
                delivery_location=f"{campaign.delivery_market}, {campaign.delivery_lga}, {campaign.delivery_state}",
                quantity=campaign.current_quantity,
                weight_estimate=campaign.current_quantity * 50,
                status='pending',
                source_channel='sabibuy'
            )
            
            self.db.session.add(logistics_request)
            self.db.session.flush()
            
            campaign.logistics_request_id = logistics_request.id
            campaign.status = 'booked'
            
            self.db.session.commit()
            
            self._send_organizer_notification(campaign, 'logistics_booked')
            
            logger.info(f"Logistics booked for {campaign.code}")
            
            return {
                'success': True,
                'logistics_request_id': logistics_request.id,
                'message': 'Logistics booked! Awaiting transporter bids.'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error booking logistics: {e}")
            return {'success': False, 'error': str(e)}
    
    def confirm_delivery(self, campaign_id: int, confirmed_by: str = None) -> Dict[str, Any]:
        """
        Confirm delivery, release escrow, and pay organizer profit
        """
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if campaign.status not in ['booked', 'in_transit']:
                return {'success': False, 'error': 'Campaign not ready for delivery confirmation'}
            
            campaign.status = 'delivered'
            campaign.actual_delivery_date = datetime.utcnow()
            campaign.escrow_released = True
            
            for order in campaign.orders.filter_by(payment_status='paid'):
                order.delivered = True
                order.delivered_at = datetime.utcnow()
                order.delivery_confirmed_by = confirmed_by
                order.payment_status = 'released'
                order.in_escrow = False
                order.escrow_released_at = datetime.utcnow()
            
            farmer_payment = campaign.farm_price * campaign.current_quantity
            
            profile = self.SabiBuyerProfile.query.filter_by(
                user_id=campaign.organizer_id
            ).first()
            
            if profile:
                profile.pending_earnings -= campaign.organizer_profit
                profile.total_earnings += campaign.organizer_profit
                profile.successful_campaigns += 1
                profile.active_campaigns_count = max(0, profile.active_campaigns_count - 1)
                
                if profile.successful_campaigns >= 3 and profile.tier == 'free':
                    pass
            
            campaign.profit_paid = True
            campaign.profit_paid_at = datetime.utcnow()
            
            self.db.session.commit()
            
            self._send_organizer_notification(campaign, 'profit_paid')
            self._notify_all_buyers(campaign, 'delivery_complete')
            
            logger.info(f"Delivery confirmed for {campaign.code}, profit: ₦{campaign.organizer_profit:,.0f}")
            
            return {
                'success': True,
                'organizer_profit': campaign.organizer_profit,
                'farmer_payment': farmer_payment,
                'message': f'Delivery complete! ₦{campaign.organizer_profit:,.0f} profit paid!'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error confirming delivery: {e}")
            return {'success': False, 'error': str(e)}
    
    def upgrade_to_captain(self, user_id: int, payment_reference: str) -> Dict[str, Any]:
        """Upgrade user to SabiBuyer Captain after ₦5,000 payment"""
        self._lazy_load_models()
        
        try:
            profile = self.get_or_create_profile(user_id)
            
            if profile.tier == 'captain' or profile.tier == 'premium':
                return {'success': False, 'error': 'Already upgraded'}
            
            profile.tier = 'captain'
            profile.tier_upgraded_at = datetime.utcnow()
            profile.captain_fee_paid = True
            profile.captain_payment_ref = payment_reference
            profile.has_gold_badge = True
            
            self.db.session.commit()
            
            logger.info(f"User {user_id} upgraded to SabiBuyer Captain")
            
            return {
                'success': True,
                'tier': 'captain',
                'message': 'Congratulations! You are now a SabiBuyer Captain with unlimited campaigns!'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error upgrading to captain: {e}")
            return {'success': False, 'error': str(e)}
    
    def subscribe_premium(
        self, 
        user_id: int, 
        subscription_code: str
    ) -> Dict[str, Any]:
        """Subscribe user to Premium tier"""
        self._lazy_load_models()
        
        try:
            profile = self.get_or_create_profile(user_id)
            
            profile.tier = 'premium'
            profile.is_premium = True
            profile.premium_start_date = datetime.utcnow()
            profile.premium_end_date = datetime.utcnow() + timedelta(days=30)
            profile.premium_subscription_code = subscription_code
            profile.has_gold_badge = True
            
            self.db.session.commit()
            
            return {
                'success': True,
                'tier': 'premium',
                'message': 'Welcome to Premium! Enjoy priority features and higher limits!'
            }
            
        except Exception as e:
            self.db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_active_campaigns(
        self, 
        limit: int = 20, 
        state: Optional[str] = None
    ) -> List['SabiBuy']:
        """Get active SabiBuy campaigns for browsing"""
        self._lazy_load_models()
        
        query = self.SabiBuy.query.filter_by(status='active')
        
        if state:
            query = query.filter(self.SabiBuy.delivery_state.ilike(f'%{state}%'))
        
        return query.order_by(self.SabiBuy.created_at.desc()).limit(limit).all()
    
    def get_user_campaigns(self, user_id: int) -> Dict[str, List['SabiBuy']]:
        """Get all campaigns for a user (organized and participated)"""
        self._lazy_load_models()
        
        organized = self.SabiBuy.query.filter_by(organizer_id=user_id).all()
        
        order_campaign_ids = self.db.session.query(self.SabiBuyOrder.sabibuy_id).filter(
            self.SabiBuyOrder.buyer_id == user_id
        ).distinct().all()
        
        participated_ids = [c[0] for c in order_campaign_ids]
        participated = self.SabiBuy.query.filter(
            self.SabiBuy.id.in_(participated_ids)
        ).all() if participated_ids else []
        
        return {
            'organized': organized,
            'participated': participated
        }
    
    def get_leaderboard(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top SabiBuyers by earnings"""
        self._lazy_load_models()
        
        profiles = self.SabiBuyerProfile.query.order_by(
            self.SabiBuyerProfile.total_earnings.desc()
        ).limit(limit).all()
        
        return [
            {
                'rank': i + 1,
                'user_name': p.user.name if p.user else 'Unknown',
                'tier': p.tier,
                'total_earnings': p.total_earnings,
                'total_gmv': p.total_gmv,
                'successful_campaigns': p.successful_campaigns,
                'has_gold_badge': p.has_gold_badge
            }
            for i, p in enumerate(profiles)
        ]
    
    def get_weekly_stats(self) -> Dict[str, Any]:
        """Get weekly SabiBuy statistics for admin dashboard"""
        self._lazy_load_models()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        weekly_campaigns = self.SabiBuy.query.filter(
            self.SabiBuy.created_at >= week_ago
        ).all()
        
        weekly_gmv = sum(c.total_revenue for c in weekly_campaigns)
        weekly_profit = sum(c.organizer_profit for c in weekly_campaigns if c.profit_paid)
        
        delivered_campaigns = [c for c in weekly_campaigns if c.status == 'delivered']
        
        return {
            'total_campaigns': len(weekly_campaigns),
            'delivered_campaigns': len(delivered_campaigns),
            'total_gmv': weekly_gmv,
            'total_profit_paid': weekly_profit,
            'active_sabibuyers': self.SabiBuyerProfile.query.filter(
                self.SabiBuyerProfile.active_campaigns_count > 0
            ).count()
        }
    
    def _generate_payment_link(self, order_id: int, amount: float) -> str:
        """Generate Paystack payment link for order"""
        return f"/sabibuy/pay/{order_id}"
    
    def _send_order_notification(self, order: 'SabiBuyOrder', event: str):
        """Send notification to buyer about their order"""
        try:
            from sms_service import SMSService
            from multilingual_service import get_message
            
            sms = SMSService()
            lang = order.preferred_language or 'en'
            
            messages = {
                'payment_confirmed': get_message('sabibuy_payment_confirmed', lang).format(
                    code=order.campaign.code,
                    quantity=order.quantity,
                    amount=f"₦{order.total_amount:,.0f}"
                )
            }
            
            message = messages.get(event, f"SabiBuy update: {event}")
            sms.send_sms(order.buyer_phone, message)
            
        except Exception as e:
            logger.error(f"Failed to send order notification: {e}")
    
    def _send_organizer_notification(self, campaign: 'SabiBuy', event: str, order=None):
        """Send notification to campaign organizer"""
        try:
            from sms_service import SMSService
            from multilingual_service import get_message
            
            organizer = campaign.organizer
            if not organizer or not organizer.phone_number:
                return
            
            sms = SMSService()
            lang = organizer.preferred_language or 'en'
            
            progress = campaign.calculate_progress_percentage()
            
            messages = {
                'order_received': get_message('sabibuy_order_received', lang).format(
                    code=campaign.code,
                    progress=progress
                ),
                'batch_closed': get_message('sabibuy_batch_closed', lang).format(
                    code=campaign.code,
                    quantity=campaign.current_quantity
                ),
                'logistics_booked': get_message('sabibuy_logistics_booked', lang).format(
                    code=campaign.code
                ),
                'profit_paid': get_message('sabibuy_profit_paid', lang).format(
                    amount=f"₦{campaign.organizer_profit:,.0f}"
                )
            }
            
            message = messages.get(event, f"SabiBuy update: {event}")
            sms.send_sms(organizer.phone_number, message)
            
        except Exception as e:
            logger.error(f"Failed to send organizer notification: {e}")
    
    def _notify_all_buyers(self, campaign: 'SabiBuy', event: str):
        """Notify all buyers in a campaign"""
        try:
            from sms_service import SMSService
            from multilingual_service import get_message
            
            sms = SMSService()
            
            for order in campaign.orders.filter_by(payment_status='released'):
                lang = order.preferred_language or 'en'
                
                if event == 'delivery_complete':
                    message = get_message('sabibuy_delivery_complete', lang).format(
                        quantity=order.quantity,
                        location=campaign.delivery_market
                    )
                else:
                    message = f"SabiBuy {campaign.code}: {event}"
                
                sms.send_sms(order.buyer_phone, message)
                
        except Exception as e:
            logger.error(f"Failed to notify buyers: {e}")
    
    # ===== CAPTAIN BOND SYSTEM =====
    
    def calculate_bond_amount(self, maximum_quantity: int) -> int:
        """Calculate required bond based on batch size"""
        for tier_name, tier_config in self.BOND_TIERS.items():
            if maximum_quantity <= tier_config['max_quantity']:
                return tier_config['bond']
        return self.BOND_TIERS['mega']['bond']
    
    def require_bond_for_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """Mark a campaign as requiring bond (for Captains with large batches)"""
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            bond_amount = self.calculate_bond_amount(campaign.maximum_quantity)
            
            campaign.bond_required = True
            campaign.bond_amount = bond_amount
            campaign.bond_status = 'pending'
            campaign.status = 'awaiting_bond'
            
            self.db.session.commit()
            
            return {
                'success': True,
                'bond_amount': bond_amount,
                'message': f'Bond of ₦{bond_amount:,} required before campaign goes live'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error setting bond requirement: {e}")
            return {'success': False, 'error': str(e)}
    
    def pay_bond(self, campaign_id: int, payment_reference: str) -> Dict[str, Any]:
        """Process bond payment for a campaign"""
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if not campaign.bond_required:
                return {'success': False, 'error': 'No bond required for this campaign'}
            
            if campaign.bond_paid:
                return {'success': False, 'error': 'Bond already paid'}
            
            campaign.bond_paid = True
            campaign.bond_payment_ref = payment_reference
            campaign.bond_status = 'held'
            campaign.status = 'active'  # Activate campaign after bond paid
            
            self.db.session.commit()
            
            logger.info(f"Bond paid for campaign {campaign.code}")
            
            return {
                'success': True,
                'message': f'Bond of ₦{campaign.bond_amount:,} paid. Campaign is now active!'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error processing bond payment: {e}")
            return {'success': False, 'error': str(e)}
    
    def forfeit_bond(self, campaign_id: int, reason: str) -> Dict[str, Any]:
        """Forfeit captain's bond due to abandonment or fraud"""
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if not campaign.bond_paid or campaign.bond_status == 'forfeited':
                return {'success': False, 'error': 'No bond to forfeit'}
            
            campaign.bond_status = 'forfeited'
            campaign.bond_forfeited_at = datetime.utcnow()
            campaign.bond_forfeit_reason = reason
            campaign.status = 'cancelled'
            campaign.cancellation_reason = f'Bond forfeited: {reason}'
            
            # Refund all buyers
            refund_result = self.cancel_and_refund_campaign(campaign_id, reason)
            
            self.db.session.commit()
            
            logger.warning(f"Bond forfeited for campaign {campaign.code}: {reason}")
            
            return {
                'success': True,
                'forfeited_amount': campaign.bond_amount,
                'refunds': refund_result,
                'message': f'Bond of ₦{campaign.bond_amount:,} forfeited. Buyers refunded.'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error forfeiting bond: {e}")
            return {'success': False, 'error': str(e)}
    
    def release_bond(self, campaign_id: int) -> Dict[str, Any]:
        """Release captain's bond after successful delivery"""
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if campaign.status != 'delivered':
                return {'success': False, 'error': 'Campaign must be delivered before bond release'}
            
            if campaign.bond_status != 'held':
                return {'success': False, 'error': 'No bond held for this campaign'}
            
            campaign.bond_status = 'released'
            
            self.db.session.commit()
            
            logger.info(f"Bond released for campaign {campaign.code}")
            
            return {
                'success': True,
                'released_amount': campaign.bond_amount,
                'message': f'Bond of ₦{campaign.bond_amount:,} released to your account'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error releasing bond: {e}")
            return {'success': False, 'error': str(e)}
    
    # ===== AUTO-CANCELLATION & REFUNDS =====
    
    def check_expired_campaigns(self) -> Dict[str, Any]:
        """Batch job to check and auto-cancel expired campaigns
        Should be run daily by a scheduler
        """
        self._lazy_load_models()
        
        results = {
            'checked': 0,
            'expired': 0,
            'refunded_total': 0.0,
            'campaigns': []
        }
        
        try:
            expired = self.SabiBuy.query.filter(
                self.SabiBuy.status == 'active',
                self.SabiBuy.expires_at < datetime.utcnow()
            ).all()
            
            results['checked'] = len(expired)
            
            for campaign in expired:
                # Only auto-cancel if minimum not reached
                if campaign.current_quantity < campaign.minimum_quantity:
                    refund_result = self.cancel_and_refund_campaign(
                        campaign.id,
                        'Batch expired without reaching minimum quantity'
                    )
                    
                    if refund_result.get('success'):
                        results['expired'] += 1
                        results['refunded_total'] += refund_result.get('total_refunded', 0)
                        results['campaigns'].append({
                            'code': campaign.code,
                            'refunded': refund_result.get('total_refunded', 0)
                        })
                else:
                    # Close the batch instead
                    self._close_batch(campaign)
            
            self.db.session.commit()
            logger.info(f"Expired campaigns check: {results}")
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error checking expired campaigns: {e}")
            results['error'] = str(e)
        
        return results
    
    def cancel_and_refund_campaign(self, campaign_id: int, reason: str) -> Dict[str, Any]:
        """Cancel a campaign and refund all paid orders"""
        self._lazy_load_models()
        
        try:
            campaign = self.SabiBuy.query.get(campaign_id)
            if not campaign:
                return {'success': False, 'error': 'Campaign not found'}
            
            if campaign.status in ['delivered', 'cancelled']:
                return {'success': False, 'error': f'Campaign already {campaign.status}'}
            
            total_refunded = 0.0
            refunded_orders = []
            
            # Process refunds for all paid orders
            for order in campaign.orders.filter_by(payment_status='paid'):
                refund_result = self._process_order_refund(order, reason)
                if refund_result.get('success'):
                    total_refunded += order.total_amount
                    refunded_orders.append({
                        'order_id': order.id,
                        'phone': order.buyer_phone,
                        'amount': order.total_amount
                    })
            
            campaign.status = 'cancelled'
            campaign.cancellation_reason = reason
            campaign.auto_refunded = True
            campaign.refund_initiated_at = datetime.utcnow()
            campaign.total_refunded = total_refunded
            
            # Update organizer profile
            profile = self.SabiBuyerProfile.query.filter_by(
                user_id=campaign.organizer_id
            ).first()
            
            if profile:
                profile.active_campaigns_count = max(0, profile.active_campaigns_count - 1)
            
            self.db.session.commit()
            
            # Notify organizer and buyers
            self._send_organizer_notification(campaign, 'campaign_cancelled')
            self._notify_buyers_of_refund(campaign)
            
            logger.info(f"Campaign {campaign.code} cancelled and ₦{total_refunded:,.0f} refunded")
            
            return {
                'success': True,
                'total_refunded': total_refunded,
                'orders_refunded': len(refunded_orders),
                'message': f'Campaign cancelled. ₦{total_refunded:,.0f} refunded to {len(refunded_orders)} buyers.'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error cancelling campaign: {e}")
            return {'success': False, 'error': str(e)}
    
    def _process_order_refund(self, order: 'SabiBuyOrder', reason: str) -> Dict[str, Any]:
        """Process refund for a single order"""
        try:
            if order.payment_status != 'paid':
                return {'success': False, 'error': 'Order not paid'}
            
            order.payment_status = 'refunded'
            order.refund_amount = order.total_amount
            order.refund_reason = reason
            order.refunded_at = datetime.utcnow()
            order.in_escrow = False
            
            # TODO: Integrate with Paystack refund API
            # For now, mark as refunded and admin can process manually
            order.refund_reference = f"REF-{order.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            logger.info(f"Order {order.id} refunded: ₦{order.total_amount:,.0f}")
            
            return {'success': True, 'refund_reference': order.refund_reference}
            
        except Exception as e:
            logger.error(f"Error refunding order {order.id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _notify_buyers_of_refund(self, campaign: 'SabiBuy'):
        """Notify all buyers in a cancelled campaign about their refund"""
        try:
            from sms_service import SMSService
            from multilingual_service import get_message
            
            sms = SMSService()
            
            for order in campaign.orders.filter_by(payment_status='refunded'):
                lang = order.preferred_language or 'en'
                message = get_message('sabibuy_refund_notification', lang).format(
                    code=campaign.code,
                    amount=f"₦{order.total_amount:,.0f}",
                    reason=campaign.cancellation_reason or 'Campaign cancelled'
                )
                sms.send_sms(order.buyer_phone, message)
                
        except Exception as e:
            logger.error(f"Failed to notify buyers of refund: {e}")
    
    def get_escrow_summary(self) -> Dict[str, Any]:
        """Get summary of all escrow funds across active campaigns"""
        self._lazy_load_models()
        
        try:
            active = self.SabiBuy.query.filter(
                self.SabiBuy.status.in_(['active', 'closed', 'booked', 'in_transit']),
                self.SabiBuy.escrow_released == False
            ).all()
            
            total_escrow = sum(c.total_escrow for c in active)
            held_bonds = self.SabiBuy.query.filter_by(bond_status='held').all()
            total_bonds = sum(c.bond_amount for c in held_bonds)
            
            return {
                'active_campaigns': len(active),
                'total_escrow': total_escrow,
                'held_bonds': len(held_bonds),
                'total_bonds_held': total_bonds,
                'total_protected_funds': total_escrow + total_bonds
            }
            
        except Exception as e:
            logger.error(f"Error getting escrow summary: {e}")
            return {'error': str(e)}
    
    def get_pending_refunds(self) -> List[Dict[str, Any]]:
        """Get list of orders marked for refund that need processing"""
        self._lazy_load_models()
        
        orders = self.SabiBuyOrder.query.filter_by(
            payment_status='refunded',
            refund_reference=None
        ).all()
        
        return [
            {
                'order_id': o.id,
                'campaign_code': o.campaign.code,
                'buyer_phone': o.buyer_phone,
                'amount': o.total_amount,
                'reason': o.refund_reason,
                'marked_at': o.refunded_at.isoformat() if o.refunded_at else None
            }
            for o in orders
        ]


sabibuy_service = SabiBuyService()
