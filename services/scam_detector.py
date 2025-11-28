"""
AgroLink Scam Detector Service - Layer 5
Rules-based fraud detection for Nigerian agricultural marketplace
Targets 95-98% scam detection with <2% false positives
"""

import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


class ScamDetector:
    """
    Rules-based scam detection engine for AgroLink
    
    All rules are designed for Nigerian agricultural marketplace context:
    - Registration fraud (multi-account, IP abuse, location hopping)
    - Price manipulation (underpricing for false listings)
    - Payout fraud (escrow abuse, new account high-value requests)
    - Transporter abuse (low-score high-volume bidding)
    """
    
    BLOCK_THRESHOLD = 70
    HOLD_THRESHOLD = 50
    
    ACTION_TYPES = [
        'registration',
        'produce_listing',
        'logistics_bid',
        'payout_request',
        'sabibuy_campaign',
        'sabibuy_order'
    ]
    
    def __init__(self):
        self.db = None
        self.User = None
        self.Produce = None
        self.LogisticsBid = None
        self.LogisticsRequest = None
        self.TransportProfile = None
        self.ScamFlag = None
    
    def _lazy_load_models(self):
        """Lazy load database models to avoid circular imports"""
        if self.db is None:
            from app import db
            from models import (User, Produce, LogisticsBid, LogisticsRequest, 
                              TransportProfile, ScamFlag)
            self.db = db
            self.User = User
            self.Produce = Produce
            self.LogisticsBid = LogisticsBid
            self.LogisticsRequest = LogisticsRequest
            self.TransportProfile = TransportProfile
            self.ScamFlag = ScamFlag
    
    def is_scam_likely(
        self, 
        user, 
        action_type: str, 
        data: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """
        Main scam detection function
        
        Args:
            user: User model instance or None (for new registrations)
            action_type: One of 'registration', 'produce_listing', 'logistics_bid', 'payout_request'
            data: Additional context data for specific action types
            ip_address: Client IP address for registration checks
        
        Returns:
            Tuple of (is_scam: bool, reason: str, score: int)
            score >= 70: block/hold + admin SMS alert
            score 50-69: hold listing + agent phone call
            score < 50: allow
        """
        self._lazy_load_models()
        
        if data is None:
            data = {}
        
        total_score = 0
        reasons = []
        
        if action_type == 'registration':
            score, reason = self._check_registration_fraud(user, data, ip_address)
            total_score += score
            if reason:
                reasons.append(reason)
        
        elif action_type == 'produce_listing':
            if user:
                score, reason = self._check_listing_fraud(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
                
                score, reason = self._check_location_hopping(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
        
        elif action_type == 'logistics_bid':
            if user:
                score, reason = self._check_transporter_abuse(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
        
        elif action_type == 'payout_request':
            if user:
                score, reason = self._check_payout_fraud(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
                
                score, reason = self._check_escrow_abuse(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
        
        elif action_type == 'sabibuy_campaign':
            if user:
                score, reason = self._check_sabibuy_campaign_fraud(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
        
        elif action_type == 'sabibuy_order':
            if user:
                score, reason = self._check_sabibuy_order_fraud(user, data)
                total_score += score
                if reason:
                    reasons.append(reason)
        
        if user:
            score, reason = self._check_multi_name_phone(user)
            total_score += score
            if reason:
                reasons.append(reason)
        
        is_scam = total_score >= self.HOLD_THRESHOLD
        combined_reason = "; ".join(reasons) if reasons else "No issues detected"
        
        if is_scam and user:
            self._log_scam_flag(user, action_type, total_score, combined_reason)
        
        return is_scam, combined_reason, total_score
    
    def _check_registration_fraud(
        self, 
        user, 
        data: Dict, 
        ip_address: Optional[str]
    ) -> Tuple[int, str]:
        """
        Rule 1: >8 new registrations from same IP in 1 hour → block
        """
        if not ip_address:
            return 0, ""
        
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        same_ip_count = self.User.query.filter(
            self.User.last_ip == ip_address,
            self.User.registration_date >= one_hour_ago
        ).count()
        
        if same_ip_count > 8:
            return 80, f"BLOCK: {same_ip_count} registrations from same IP in 1 hour"
        elif same_ip_count > 5:
            return 40, f"WARNING: {same_ip_count} registrations from same IP in 1 hour"
        
        return 0, ""
    
    def _check_multi_name_phone(self, user) -> Tuple[int, str]:
        """
        Rule 2 & 3: Same name on >4 phones OR same phone by >2 different names → block
        """
        if not user:
            return 0, ""
        
        if user.name:
            same_name_count = self.User.query.filter(
                self.User.name == user.name,
                self.User.id != user.id
            ).count()
            
            if same_name_count >= 4:
                return 75, f"BLOCK: Same name '{user.name}' on {same_name_count + 1} accounts"
        
        if user.phone_number:
            different_names = self.User.query.filter(
                self.User.phone_number == user.phone_number,
                self.User.name != user.name
            ).distinct(self.User.name).count()
            
            if different_names >= 2:
                return 80, f"BLOCK: Phone {user.phone_number} used by {different_names + 1} different names"
        
        return 0, ""
    
    def _check_location_hopping(self, user, data: Dict) -> Tuple[int, str]:
        """
        Rule 4: New user in >4 states in 24 hrs (location hops) → freeze
        """
        if not user:
            return 0, ""
        
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        locations = []
        
        if user.location:
            locations.append(self._extract_state(user.location))
        
        recent_listings = self.Produce.query.filter(
            self.Produce.farmer_id == user.id,
            self.Produce.date_listed >= twenty_four_hours_ago
        ).all()
        
        for listing in recent_listings:
            if listing.listing_location:
                state = self._extract_state(listing.listing_location)
                if state:
                    locations.append(state)
        
        if data.get('location'):
            state = self._extract_state(data['location'])
            if state:
                locations.append(state)
        
        unique_states = set(locations)
        
        if len(unique_states) > 4:
            return 70, f"FREEZE: User active in {len(unique_states)} states in 24 hours: {', '.join(unique_states)}"
        elif len(unique_states) > 3:
            return 35, f"WARNING: User in {len(unique_states)} states in 24 hours"
        
        return 0, ""
    
    def _check_listing_fraud(self, user, data: Dict) -> Tuple[int, str]:
        """
        Rule 5: Listing price <60% of 7-day average for crop + location → hold for agent
        """
        crop = data.get('crop') or data.get('name')
        location = data.get('location') or user.location if user else None
        price = data.get('price', 0)
        
        if not crop or not price:
            return 0, ""
        
        avg_price = self.get_7day_avg_price(crop, location)
        
        if avg_price and avg_price > 0:
            price_ratio = price / avg_price
            
            if price_ratio < 0.60:
                return 60, f"HOLD: Price ₦{price:,.0f} is {price_ratio*100:.0f}% of 7-day avg ₦{avg_price:,.0f} for {crop}"
            elif price_ratio < 0.70:
                return 30, f"WARNING: Price ₦{price:,.0f} is {price_ratio*100:.0f}% below average for {crop}"
        
        return 0, ""
    
    def _check_escrow_abuse(self, user, data: Dict) -> Tuple[int, str]:
        """
        Rule 6: Buyer paid >₦2M in escrow but zero deliveries → freeze payout
        """
        if not user or user.role != 'buyer':
            return 0, ""
        
        total_escrow = self.db.session.query(
            self.db.func.sum(self.LogisticsRequest.escrow_amount)
        ).join(
            self.Produce, self.LogisticsRequest.produce_id == self.Produce.id
        ).filter(
            self.Produce.buyer_id == user.id
        ).scalar() or 0
        
        completed_deliveries = self.LogisticsRequest.query.join(
            self.Produce, self.LogisticsRequest.produce_id == self.Produce.id
        ).filter(
            self.Produce.buyer_id == user.id,
            self.LogisticsRequest.status == 'delivered'
        ).count()
        
        if total_escrow > 2000000 and completed_deliveries == 0:
            return 75, f"FREEZE: Buyer has ₦{total_escrow:,.0f} in escrow but {completed_deliveries} deliveries"
        elif total_escrow > 1000000 and completed_deliveries == 0:
            return 45, f"WARNING: High escrow (₦{total_escrow:,.0f}) with no completed deliveries"
        
        return 0, ""
    
    def _check_transporter_abuse(self, user, data: Dict) -> Tuple[int, str]:
        """
        Rule 7: Transporter score <30 but >10 bids today → hide
        """
        if not user:
            return 0, ""
        
        transport_profile = self.TransportProfile.query.filter_by(user_id=user.id).first()
        
        if not transport_profile:
            return 0, ""
        
        rating = transport_profile.rating or 5.0
        score_out_of_100 = (rating / 5.0) * 100
        
        if score_out_of_100 < 30:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_bids = self.LogisticsBid.query.filter(
                self.LogisticsBid.transporter_id == transport_profile.id,
                self.LogisticsBid.created_at >= today_start
            ).count()
            
            if today_bids > 10:
                return 70, f"HIDE: Low-rated transporter ({rating:.1f}/5) with {today_bids} bids today"
            elif today_bids > 5:
                return 35, f"WARNING: Low-rated transporter with {today_bids} bids today"
        
        return 0, ""
    
    def _check_payout_fraud(self, user, data: Dict) -> Tuple[int, str]:
        """
        Rule 8: New user (<30 days) requesting >₦500K daily payout → block
        """
        if not user:
            return 0, ""
        
        account_age_days = (datetime.utcnow() - user.registration_date).days if user.registration_date else 0
        
        if account_age_days < 30:
            payout_amount = data.get('amount', 0)
            
            if payout_amount > 500000:
                return 80, f"BLOCK: New user ({account_age_days} days old) requesting ₦{payout_amount:,.0f} payout"
            elif payout_amount > 200000:
                return 50, f"HOLD: New user requesting ₦{payout_amount:,.0f} payout"
        
        return 0, ""
    
    def get_7day_avg_price(self, crop: str, location: Optional[str] = None) -> float:
        """
        Calculate 7-day average price for a crop, optionally filtered by location
        
        Args:
            crop: Crop name to search (case-insensitive)
            location: Optional location to filter by state
        
        Returns:
            Average price or 0 if no data found
        """
        self._lazy_load_models()
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        query = self.Produce.query.filter(
            self.db.func.lower(self.Produce.name).like(f"%{crop.lower()}%"),
            self.Produce.date_listed >= seven_days_ago,
            self.Produce.price > 0
        )
        
        if location:
            state = self._extract_state(location)
            if state:
                query = query.filter(
                    self.db.func.lower(self.Produce.listing_location).like(f"%{state.lower()}%")
                )
        
        prices = [p.price for p in query.all()]
        
        if not prices:
            all_prices = self.Produce.query.filter(
                self.db.func.lower(self.Produce.name).like(f"%{crop.lower()}%"),
                self.Produce.date_listed >= seven_days_ago,
                self.Produce.price > 0
            ).with_entities(self.Produce.price).all()
            prices = [p[0] for p in all_prices]
        
        if prices:
            return sum(prices) / len(prices)
        
        return 0.0
    
    def _extract_state(self, location: str) -> str:
        """Extract Nigerian state from location string"""
        if not location:
            return ""
        
        nigerian_states = [
            'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 
            'Benue', 'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 
            'Ekiti', 'Enugu', 'FCT', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 
            'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 
            'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 
            'Sokoto', 'Taraba', 'Yobe', 'Zamfara'
        ]
        
        location_lower = location.lower()
        for state in nigerian_states:
            if state.lower() in location_lower:
                return state
        
        return location.split(',')[0].strip() if ',' in location else location.strip()
    
    def _log_scam_flag(
        self, 
        user, 
        action_type: str, 
        score: int, 
        reason: str
    ):
        """Log scam detection to database for admin review"""
        if not user:
            return
        
        try:
            flag = self.ScamFlag(
                user_id=user.id,
                action_type=action_type,
                scam_score=score,
                reason=reason,
                status='pending',
                detected_at=datetime.utcnow()
            )
            self.db.session.add(flag)
            
            if user.scam_score is None:
                user.scam_score = 0
            user.scam_score = max(user.scam_score, score)
            
            self.db.session.commit()
            
            if score >= self.BLOCK_THRESHOLD:
                self._send_admin_alert(user, action_type, score, reason)
            
        except Exception as e:
            logger.error(f"Error logging scam flag: {e}")
            self.db.session.rollback()
    
    def flag_new_user(
        self, 
        user,
        reason: str,
        score: int,
        ip_address: Optional[str] = None
    ):
        """
        Create ScamFlag record for newly registered user (post-registration hook)
        
        Call this immediately after user creation if is_scam_likely returned 
        a positive score during registration
        
        Args:
            user: Newly created User model instance
            reason: Scam detection reason
            score: Scam score from registration check
            ip_address: IP address used during registration
        """
        self._lazy_load_models()
        
        if not user or score < self.HOLD_THRESHOLD:
            return
        
        try:
            if ip_address:
                user.last_ip = ip_address
            
            flag = self.ScamFlag(
                user_id=user.id,
                action_type='registration',
                scam_score=score,
                reason=reason,
                status='pending',
                detected_at=datetime.utcnow()
            )
            self.db.session.add(flag)
            
            user.scam_score = score
            
            self.db.session.commit()
            
            if score >= self.BLOCK_THRESHOLD:
                self._send_admin_alert(user, 'registration', score, reason)
                
        except Exception as e:
            logger.error(f"Error flagging new user: {e}")
            self.db.session.rollback()
    
    def _send_admin_alert(
        self, 
        user, 
        action_type: str, 
        score: int, 
        reason: str
    ):
        """Send SMS alert to admin for high-score scam detection"""
        try:
            from sms_service import SMSService
            
            admin_phones = self._get_admin_phones()
            
            if admin_phones:
                sms = SMSService()
                message = (
                    f"SCAM ALERT [{score}]: {user.name} ({user.phone_number})\n"
                    f"Action: {action_type}\n"
                    f"Reason: {reason[:100]}"
                )
                
                for phone in admin_phones[:2]:
                    sms.send_sms(phone, message)
        except Exception as e:
            logger.error(f"Failed to send admin scam alert: {e}")
    
    def _get_admin_phones(self) -> list:
        """Get list of admin phone numbers for alerts"""
        admins = self.User.query.filter_by(role='admin').filter(
            self.User.phone_number.isnot(None)
        ).limit(3).all()
        
        return [admin.phone_number for admin in admins if admin.phone_number]
    
    def get_flagged_users(self, limit: int = 50) -> list:
        """Get top flagged users for admin dashboard"""
        self._lazy_load_models()
        
        return self.ScamFlag.query.filter(
            self.ScamFlag.status == 'pending'
        ).order_by(
            self.ScamFlag.scam_score.desc(),
            self.ScamFlag.detected_at.desc()
        ).limit(limit).all()
    
    def approve_user(self, flag_id: int, admin_id: int) -> bool:
        """Approve a flagged user (false positive)"""
        self._lazy_load_models()
        
        flag = self.ScamFlag.query.get(flag_id)
        if not flag:
            return False
        
        flag.status = 'approved'
        flag.reviewed_by = admin_id
        flag.reviewed_at = datetime.utcnow()
        
        if flag.user and flag.user.scam_score:
            flag.user.scam_score = max(0, flag.user.scam_score - 30)
        
        self.db.session.commit()
        return True
    
    def ban_user(self, flag_id: int, admin_id: int) -> bool:
        """Ban a flagged user (confirmed scammer)"""
        self._lazy_load_models()
        
        flag = self.ScamFlag.query.get(flag_id)
        if not flag:
            return False
        
        flag.status = 'banned'
        flag.reviewed_by = admin_id
        flag.reviewed_at = datetime.utcnow()
        
        if flag.user:
            flag.user.scam_score = 100
            flag.user.role = 'banned'
        
        self.db.session.commit()
        return True
    
    def request_agent_call(self, flag_id: int, admin_id: int) -> bool:
        """Request agent to call user for verification"""
        self._lazy_load_models()
        
        flag = self.ScamFlag.query.get(flag_id)
        if not flag:
            return False
        
        flag.status = 'agent_call_pending'
        flag.reviewed_by = admin_id
        flag.reviewed_at = datetime.utcnow()
        
        self.db.session.commit()
        
        self._notify_nearest_agent(flag.user)
        
        return True
    
    def _notify_nearest_agent(self, user):
        """Notify nearest agent to call user"""
        try:
            from models import AgentProfile
            from sms_service import SMSService
            
            location = user.location or ""
            state = self._extract_state(location)
            
            agent_profile = AgentProfile.query.filter(
                AgentProfile.is_approved == True,
                AgentProfile.lga.ilike(f"%{state}%") if state else True
            ).first()
            
            if not agent_profile:
                agent_profile = AgentProfile.query.filter_by(is_approved=True).first()
            
            if agent_profile and agent_profile.user:
                sms = SMSService()
                message = (
                    f"VERIFICATION NEEDED:\n"
                    f"Call {user.name} at {user.phone_number}\n"
                    f"Location: {location}\n"
                    f"Reply after verification"
                )
                sms.send_sms(agent_profile.user.phone_number, message)
        except Exception as e:
            logger.error(f"Failed to notify agent: {e}")
    
    def _check_sabibuy_campaign_fraud(self, user, data: Dict) -> Tuple[int, str]:
        """
        SabiBuy Campaign Fraud Detection Rules:
        - New account (<7 days) creating high-value campaigns → suspicious
        - Multiple failed campaigns from same organizer → warning
        - Excessive profit margins (>300%) → suspicious pricing
        - Rapid campaign creation (>5 in 24h) → possible flood attack
        """
        try:
            from models import SabiBuy, SabiBuyerProfile
            
            score = 0
            reasons = []
            
            account_age = (datetime.utcnow() - user.registration_date).days if user.registration_date else 0
            selling_price = data.get('selling_price', 0)
            farm_price = data.get('farm_price', 0)
            
            if account_age < 7 and selling_price > 100000:
                score += 40
                reasons.append(f"New account ({account_age} days) creating high-value campaign (₦{selling_price:,.0f})")
            
            if farm_price > 0 and selling_price > 0:
                margin_pct = ((selling_price - farm_price) / farm_price) * 100
                if margin_pct > 300:
                    score += 35
                    reasons.append(f"Excessive profit margin ({margin_pct:.0f}%)")
            
            failed_campaigns = SabiBuy.query.filter(
                SabiBuy.organizer_id == user.id,
                SabiBuy.status.in_(['cancelled', 'expired'])
            ).count()
            
            if failed_campaigns >= 3:
                score += 25
                reasons.append(f"{failed_campaigns} failed/cancelled campaigns")
            
            recent_campaigns = SabiBuy.query.filter(
                SabiBuy.organizer_id == user.id,
                SabiBuy.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            if recent_campaigns >= 5:
                score += 40
                reasons.append(f"{recent_campaigns} campaigns created in last 24 hours")
            
            return score, "; ".join(reasons)
            
        except Exception as e:
            logger.error(f"SabiBuy campaign fraud check error: {e}")
            return 0, ""
    
    def _check_sabibuy_order_fraud(self, user, data: Dict) -> Tuple[int, str]:
        """
        SabiBuy Order Fraud Detection Rules:
        - Unusually large orders from new accounts → suspicious
        - Multiple failed payments from same buyer → possible card testing
        - Ordering from multiple campaigns simultaneously → unusual pattern
        """
        try:
            from models import SabiBuyOrder
            
            score = 0
            reasons = []
            
            account_age = (datetime.utcnow() - user.registration_date).days if user.registration_date else 0
            order_amount = data.get('order_amount', 0)
            
            if account_age < 3 and order_amount > 200000:
                score += 35
                reasons.append(f"New account ({account_age} days) with large order (₦{order_amount:,.0f})")
            
            failed_payments = SabiBuyOrder.query.filter(
                SabiBuyOrder.buyer_id == user.id,
                SabiBuyOrder.payment_status == 'failed',
                SabiBuyOrder.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            if failed_payments >= 3:
                score += 40
                reasons.append(f"{failed_payments} failed payment attempts in 24h")
            
            active_orders = SabiBuyOrder.query.filter(
                SabiBuyOrder.buyer_id == user.id,
                SabiBuyOrder.payment_status == 'pending',
                SabiBuyOrder.created_at >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if active_orders >= 5:
                score += 30
                reasons.append(f"{active_orders} pending orders in last hour")
            
            return score, "; ".join(reasons)
            
        except Exception as e:
            logger.error(f"SabiBuy order fraud check error: {e}")
            return 0, ""


scam_detector = ScamDetector()
