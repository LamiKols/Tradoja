"""
Reseller Detection Service
Prevents pure resellers (middlemen who just mark up without adding value) from flooding the platform.

Key Principles:
1. Traders MUST declare what value they add (transport, aggregation, processing, storage, capital, grading)
2. Traders MUST provide proof of their declared services
3. System automatically monitors behavior for pure reseller patterns
4. High-risk traders are flagged for admin review
5. CONTINUOUS VERIFICATION: Traders are monitored monthly for value-add activity
6. DEVICE FINGERPRINTING: Detect multiple accounts from same person/device
"""

from datetime import datetime, timedelta
from app import db
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class ResellerDetector:
    """Service for detecting and managing pure resellers"""
    
    VALUE_ADD_SERVICES = {
        'transport': {
            'name': 'Transport/Delivery',
            'description': 'You own or operate vehicles to transport produce from farms to markets',
            'proof_required': 'Vehicle registration, fleet photos, driver licenses',
            'weight': 25
        },
        'aggregation': {
            'name': 'Aggregation (Bulk Collection)',
            'description': 'You collect produce from multiple small farmers to create bulk lots',
            'proof_required': 'Photos of aggregation point, farmer contracts/agreements',
            'weight': 20
        },
        'processing': {
            'name': 'Processing/Packaging',
            'description': 'You process, clean, sort, or package produce for market',
            'proof_required': 'Processing facility photos, equipment, NAFDAC registration if applicable',
            'weight': 30
        },
        'storage': {
            'name': 'Storage/Warehousing',
            'description': 'You operate storage facilities (cold chain, dry storage, silos)',
            'proof_required': 'Warehouse photos, lease agreement, cold chain equipment',
            'weight': 25
        },
        'working_capital': {
            'name': 'Working Capital/Financing',
            'description': 'You provide upfront payment to farmers before resale',
            'proof_required': 'Bank statements showing farmer payments, credit facility letter',
            'weight': 20
        },
        'quality_grading': {
            'name': 'Quality Grading/Sorting',
            'description': 'You grade and sort produce by quality standards',
            'proof_required': 'Grading equipment photos, quality certificates, trained staff',
            'weight': 15
        },
        'market_access': {
            'name': 'Market Access/Export',
            'description': 'You have established relationships with institutional buyers or export channels',
            'proof_required': 'Buyer contracts, export license, institutional agreements',
            'weight': 20
        }
    }
    
    RESELLER_DETECTION_RULES = [
        {
            'id': 'no_value_declared',
            'name': 'No Value-Add Services Declared',
            'description': 'Trader has not declared any value-add services',
            'points': 30,
            'action': 'require_declaration'
        },
        {
            'id': 'no_logistics',
            'name': 'Never Uses Platform Logistics',
            'description': 'Trader has made multiple purchases but never booked transport',
            'points': 20,
            'action': 'flag_for_review'
        },
        {
            'id': 'high_markup',
            'name': 'High Markup Without Proof',
            'description': 'Average markup exceeds 30% without verified value-add services',
            'points': 25,
            'action': 'require_verification'
        },
        {
            'id': 'no_farmer_relationships',
            'name': 'No Repeat Farmer Relationships',
            'description': 'Many purchases but no recurring deals with same farmers',
            'points': 15,
            'action': 'flag_for_review'
        },
        {
            'id': 'pure_flip_pattern',
            'name': 'Buy-Sell Flip Pattern',
            'description': 'Buy and sell counts match closely (pure arbitrage)',
            'points': 10,
            'action': 'flag_for_review'
        },
        {
            'id': 'unverified_claims',
            'name': 'Unverified Service Claims',
            'description': 'Claims value-add services but no proof submitted',
            'points': 15,
            'action': 'require_proof'
        },
        # CONTINUOUS VERIFICATION RULES
        {
            'id': 'verification_expired',
            'name': 'Verification Expired',
            'description': 'Trader verification is more than 90 days old without renewal',
            'points': 25,
            'action': 'require_renewal'
        },
        {
            'id': 'inactive_value_add',
            'name': 'Inactive Value-Add Activity',
            'description': 'No logistics or farmer deals in last 30 days despite claiming services',
            'points': 20,
            'action': 'flag_for_review'
        },
        {
            'id': 'poor_farmer_ratings',
            'name': 'Poor Farmer Feedback',
            'description': 'Average rating from farmers below 3 stars',
            'points': 20,
            'action': 'flag_for_review'
        },
        {
            'id': 'device_collision',
            'name': 'Suspicious Device Match',
            'description': 'Account shares device fingerprint with another account',
            'points': 15,
            'action': 'investigate'
        },
        {
            'id': 'ip_farming',
            'name': 'IP Address Farming',
            'description': 'Multiple accounts registered from same IP',
            'points': 10,
            'action': 'investigate'
        }
    ]
    
    # Verification renewal period (90 days)
    VERIFICATION_VALIDITY_DAYS = 90
    
    def __init__(self):
        pass
    
    def get_available_services(self):
        """Get list of available value-add services for registration"""
        return self.VALUE_ADD_SERVICES
    
    def calculate_trader_score(self, user):
        """Calculate comprehensive reseller score for a user
        Returns tuple: (score, triggered_rules, recommendations)
        
        Enhanced with continuous verification and device fingerprinting rules.
        """
        if not user.is_trader():
            return (0, [], [])
        
        score = 0
        triggered_rules = []
        recommendations = []
        
        # Rule 1: No value-add services declared
        if not user.trader_value_services:
            score += 30
            triggered_rules.append({
                'rule': 'no_value_declared',
                'points': 30,
                'message': 'You have not declared any value-add services'
            })
            recommendations.append('Declare at least one value-add service you provide')
        
        # Rule 2: Never uses platform logistics (after 3+ purchases)
        if user.logistics_bookings == 0 and (user.total_purchases or 0) > 3:
            score += 20
            triggered_rules.append({
                'rule': 'no_logistics',
                'points': 20,
                'message': f'Made {user.total_purchases} purchases but never used platform logistics'
            })
            recommendations.append('Book transport through the platform to show you add delivery value')
        
        # Rule 3: High markup without verification
        if (user.avg_markup_percentage or 0) > 30 and not user.trader_verified:
            score += 25
            triggered_rules.append({
                'rule': 'high_markup',
                'points': 25,
                'message': f'Average markup of {user.avg_markup_percentage:.1f}% without verified services'
            })
            recommendations.append('Submit proof of your value-add services to justify pricing')
        
        # Rule 4: No repeat farmer relationships (after 5+ purchases)
        if (user.total_purchases or 0) > 5 and (user.direct_farmer_deals or 0) < 2:
            score += 15
            triggered_rules.append({
                'rule': 'no_farmer_relationships',
                'points': 15,
                'message': 'No recurring relationships with farmers'
            })
            recommendations.append('Build lasting relationships with farmers you work with')
        
        # Rule 5: Pure flip pattern (buy/sell nearly equal)
        purchases = user.total_purchases or 0
        sales = user.total_sales or 0
        if purchases > 0 and sales > 0 and abs(purchases - sales) < 2:
            score += 10
            triggered_rules.append({
                'rule': 'pure_flip_pattern',
                'points': 10,
                'message': 'Buy-sell pattern suggests pure arbitrage'
            })
        
        # Rule 6: Claims services but no proof
        if user.trader_value_services and not user.trader_verified:
            has_any_proof = any([
                user.trader_transport_proof,
                user.trader_storage_proof,
                user.trader_processing_proof,
                user.trader_capital_proof
            ])
            if not has_any_proof:
                score += 15
                triggered_rules.append({
                    'rule': 'unverified_claims',
                    'points': 15,
                    'message': 'Service claims not backed by proof'
                })
                recommendations.append('Upload proof documents for your declared services')
        
        # ===== CONTINUOUS VERIFICATION RULES =====
        
        # Rule 7: Verification expired (90 days since last verification)
        if user.trader_verified and user.verification_expiry:
            if datetime.utcnow() > user.verification_expiry:
                score += 25
                triggered_rules.append({
                    'rule': 'verification_expired',
                    'points': 25,
                    'message': 'Verification expired - renewal required'
                })
                recommendations.append('Renew your trader verification with updated proof')
                user.verification_renewal_required = True
        
        # Rule 8: Inactive value-add activity (verified but no activity in 30 days)
        if user.trader_verified and user.trader_value_services:
            # Check if they have logistics service but no recent bookings
            if 'transport' in (user.trader_value_services or ''):
                if (user.monthly_logistics_count or 0) == 0 and (user.total_purchases or 0) > 5:
                    score += 20
                    triggered_rules.append({
                        'rule': 'inactive_value_add',
                        'points': 20,
                        'message': 'Claims transport service but no logistics activity this month'
                    })
                    recommendations.append('Use platform logistics to maintain verified status')
        
        # Rule 9: Poor farmer ratings
        if user.trader_verified and (user.average_rating or 0) > 0:
            if user.average_rating < 3.0 and (user.total_ratings or 0) >= 3:
                score += 20
                triggered_rules.append({
                    'rule': 'poor_farmer_ratings',
                    'points': 20,
                    'message': f'Average farmer rating of {user.average_rating:.1f}/5 stars'
                })
                recommendations.append('Improve your service to farmers to maintain good standing')
        
        # Rule 10: Device fingerprint collision
        if (user.fingerprint_flags or 0) > 0:
            score += 15
            triggered_rules.append({
                'rule': 'device_collision',
                'points': 15,
                'message': 'Account shares device with other accounts'
            })
        
        # Rule 11: Multiple accounts from same IP
        if user.registration_ip:
            collision_count = self._check_ip_collision(user)
            if collision_count > 1:
                score += 10
                triggered_rules.append({
                    'rule': 'ip_farming',
                    'points': 10,
                    'message': f'{collision_count} accounts registered from same IP'
                })
        
        # Cap at 100
        score = min(100, score)
        
        # Update user record
        user.reseller_score = score
        user.last_reseller_check = datetime.utcnow()
        
        return (score, triggered_rules, recommendations)
    
    def _check_ip_collision(self, user):
        """Check how many accounts share this user's registration IP"""
        from models import User
        if not user.registration_ip:
            return 0
        
        count = User.query.filter(
            User.registration_ip == user.registration_ip,
            User.id != user.id
        ).count()
        return count
    
    def get_risk_level(self, score):
        """Get risk level from score"""
        if score >= 70:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'
    
    def can_trader_proceed(self, user, action='list_produce'):
        """Check if trader can proceed with an action
        Returns tuple: (allowed, reason, action_required)
        """
        if not user.is_trader():
            return (True, None, None)
        
        # Calculate fresh score
        score, rules, recommendations = self.calculate_trader_score(user)
        risk = self.get_risk_level(score)
        
        if action == 'list_produce':
            # Traders MUST be verified to list produce
            if not user.trader_verified:
                if user.trader_verification_status == 'pending':
                    return (False, 'Your trader verification is pending admin review', 'wait_for_verification')
                elif user.trader_verification_status == 'rejected':
                    return (False, 'Your trader verification was rejected. Please update your application.', 'reapply')
                elif user.trader_verification_status == 'suspended':
                    return (False, 'Your trader account has been suspended. Contact support.', 'contact_support')
                else:
                    return (False, 'Traders must be verified before listing produce. Please apply for verification.', 'apply_verification')
            return (True, None, None)
        
        elif action == 'view_listings':
            # Verified traders and those pending can view
            if user.trader_verification_status in ['verified', 'pending']:
                return (True, None, None)
            # New traders get limited view
            if user.trader_verification_status == 'none':
                return (True, 'Limited view - apply for verification to see full listings', 'apply_verification')
            return (False, 'Your account status prevents viewing listings', 'contact_support')
        
        elif action == 'contact_farmer':
            # Must be verified to contact farmers directly
            if not user.trader_verified:
                return (False, 'Only verified traders can contact farmers directly', 'apply_verification')
            return (True, None, None)
        
        return (True, None, None)
    
    def flag_suspicious_traders(self):
        """Batch job to flag traders with high reseller scores
        Returns list of flagged user IDs
        """
        from models import User
        
        flagged = []
        traders = User.query.filter(
            User.role == 'buyer',
            User.buyer_type == 'bulk_trader'
        ).all()
        
        for trader in traders:
            score, rules, _ = self.calculate_trader_score(trader)
            
            if score >= 70 and trader.trader_verification_status not in ['suspended', 'rejected']:
                # Auto-flag for review
                if trader.trader_verification_status == 'verified':
                    trader.trader_verification_status = 'pending'  # Needs re-review
                    trader.trader_verification_notes = (trader.trader_verification_notes or '') + \
                        f'\n[AUTO-FLAG {datetime.utcnow().strftime("%Y-%m-%d")}] High reseller score: {score}'
                flagged.append(trader.id)
                logger.warning(f"Trader {trader.id} ({trader.email}) flagged with reseller score {score}")
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error flagging traders: {e}")
        
        return flagged
    
    def get_pending_verifications(self):
        """Get list of traders pending verification"""
        from models import User
        
        return User.query.filter(
            User.role == 'buyer',
            User.buyer_type == 'bulk_trader',
            User.trader_verification_status == 'pending'
        ).order_by(User.registration_date.desc()).all()
    
    def get_flagged_traders(self, min_score=50):
        """Get traders above a reseller score threshold"""
        from models import User
        
        return User.query.filter(
            User.role == 'buyer',
            User.buyer_type == 'bulk_trader',
            User.reseller_score >= min_score
        ).order_by(User.reseller_score.desc()).all()
    
    def verify_trader(self, trader_id, admin_id, status, notes=None):
        """Admin action to verify/reject a trader
        status: 'verified', 'rejected', 'suspended'
        """
        from models import User
        
        trader = User.query.get(trader_id)
        if not trader or not trader.is_trader():
            return (False, 'Invalid trader')
        
        trader.trader_verification_status = status
        trader.trader_verified = (status == 'verified')
        trader.trader_verification_date = datetime.utcnow()
        trader.trader_verified_by = admin_id
        
        # Set verification expiry for continuous verification
        if status == 'verified':
            trader.verification_expiry = datetime.utcnow() + timedelta(days=self.VERIFICATION_VALIDITY_DAYS)
            trader.verification_renewal_required = False
        
        if notes:
            trader.trader_verification_notes = (trader.trader_verification_notes or '') + \
                f'\n[{datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] {status.upper()}: {notes}'
        
        try:
            db.session.commit()
            logger.info(f"Trader {trader_id} verification status changed to {status} by admin {admin_id}")
            return (True, f'Trader {status} successfully')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating trader verification: {e}")
            return (False, str(e))
    
    # ===== DEVICE FINGERPRINTING =====
    
    def generate_device_fingerprint(self, request):
        """Generate a device fingerprint from request headers"""
        components = [
            request.headers.get('User-Agent', ''),
            request.headers.get('Accept-Language', ''),
            request.headers.get('Accept-Encoding', ''),
            request.remote_addr or ''
        ]
        fingerprint_string = '|'.join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def record_device_fingerprint(self, user, request):
        """Record device fingerprint for a user and check for collisions"""
        from models import DeviceFingerprint, User
        
        fingerprint_hash = self.generate_device_fingerprint(request)
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')[:500]
        
        # Check if this fingerprint exists for this user
        existing = DeviceFingerprint.query.filter_by(
            user_id=user.id,
            fingerprint_hash=fingerprint_hash
        ).first()
        
        if existing:
            existing.last_seen = datetime.utcnow()
            existing.times_seen += 1
        else:
            # New fingerprint for this user
            new_fp = DeviceFingerprint(
                fingerprint_hash=fingerprint_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user.id
            )
            db.session.add(new_fp)
            
            # Check for collisions with other users
            collision = DeviceFingerprint.query.filter(
                DeviceFingerprint.fingerprint_hash == fingerprint_hash,
                DeviceFingerprint.user_id != user.id
            ).first()
            
            if collision:
                # Flag both accounts
                user.fingerprint_flags = (user.fingerprint_flags or 0) + 1
                collision_user = User.query.get(collision.user_id)
                if collision_user:
                    collision_user.fingerprint_flags = (collision_user.fingerprint_flags or 0) + 1
                    
                    # Update linked accounts
                    linked = json.loads(user.linked_accounts or '[]')
                    if collision.user_id not in linked:
                        linked.append(collision.user_id)
                        user.linked_accounts = json.dumps(linked)
                    
                    linked2 = json.loads(collision_user.linked_accounts or '[]')
                    if user.id not in linked2:
                        linked2.append(user.id)
                        collision_user.linked_accounts = json.dumps(linked2)
                
                logger.warning(f"Device fingerprint collision: User {user.id} and User {collision.user_id}")
        
        # Record IP
        if ip_address and not user.registration_ip:
            user.registration_ip = ip_address
        
        # Update known IPs
        known_ips = json.loads(user.known_ips or '[]')
        if ip_address and ip_address not in known_ips:
            known_ips.append(ip_address)
            user.known_ips = json.dumps(known_ips[-10:])  # Keep last 10 IPs
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording device fingerprint: {e}")
    
    def get_linked_accounts(self, user_id):
        """Get accounts potentially linked to this user"""
        from models import User
        
        user = User.query.get(user_id)
        if not user or not user.linked_accounts:
            return []
        
        linked_ids = json.loads(user.linked_accounts)
        return User.query.filter(User.id.in_(linked_ids)).all()
    
    # ===== CONTINUOUS VERIFICATION =====
    
    def run_monthly_verification_check(self):
        """Monthly batch job to check all verified traders for continued compliance
        Returns dict with check results
        """
        from models import User
        
        results = {
            'checked': 0,
            'expired': [],
            'inactive': [],
            'flagged': [],
            'ok': []
        }
        
        # Get all verified traders
        traders = User.query.filter(
            User.role == 'buyer',
            User.buyer_type == 'bulk_trader',
            User.trader_verified == True
        ).all()
        
        for trader in traders:
            results['checked'] += 1
            
            # Check verification expiry
            if trader.verification_expiry and datetime.utcnow() > trader.verification_expiry:
                trader.verification_renewal_required = True
                results['expired'].append(trader.id)
                logger.info(f"Trader {trader.id} verification expired")
            
            # Check monthly activity
            if (trader.monthly_logistics_count or 0) == 0 and (trader.monthly_purchase_count or 0) > 0:
                # Made purchases but no logistics - potential flip pattern
                trader.consecutive_inactive_months = (trader.consecutive_inactive_months or 0) + 1
                if trader.consecutive_inactive_months >= 2:
                    results['inactive'].append(trader.id)
                    logger.warning(f"Trader {trader.id} inactive for {trader.consecutive_inactive_months} months")
            else:
                trader.consecutive_inactive_months = 0
            
            # Calculate fresh score
            score, rules, _ = self.calculate_trader_score(trader)
            if score >= 50:
                results['flagged'].append(trader.id)
            else:
                results['ok'].append(trader.id)
            
            # Reset monthly counters
            trader.monthly_logistics_count = 0
            trader.monthly_purchase_count = 0
        
        try:
            db.session.commit()
            logger.info(f"Monthly verification check complete: {results}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in monthly verification check: {e}")
        
        return results
    
    def process_farmer_feedback(self, farmer_id, trader_id, produce_id, rating_data):
        """Process feedback from a farmer about a trader
        Returns tuple: (success, message)
        """
        from models import User, TraderFeedback
        
        farmer = User.query.get(farmer_id)
        trader = User.query.get(trader_id)
        
        if not farmer or not farmer.is_farmer():
            return (False, 'Invalid farmer')
        if not trader or not trader.is_trader():
            return (False, 'Invalid trader')
        
        # Create feedback record
        feedback = TraderFeedback(
            farmer_id=farmer_id,
            trader_id=trader_id,
            produce_id=produce_id,
            overall_rating=rating_data.get('overall_rating', 3),
            payment_speed_rating=rating_data.get('payment_speed_rating'),
            communication_rating=rating_data.get('communication_rating'),
            fairness_rating=rating_data.get('fairness_rating'),
            would_work_again=rating_data.get('would_work_again', True),
            provided_transport=rating_data.get('provided_transport', False),
            paid_upfront=rating_data.get('paid_upfront', False),
            added_value=rating_data.get('added_value', True),
            feedback_text=rating_data.get('feedback_text', '')
        )
        
        db.session.add(feedback)
        
        # Update trader's average rating
        all_feedback = TraderFeedback.query.filter_by(trader_id=trader_id).all()
        total_rating = sum(f.overall_rating for f in all_feedback) + rating_data.get('overall_rating', 3)
        count = len(all_feedback) + 1
        
        trader.average_rating = total_rating / count
        trader.total_ratings = count
        
        # If rating is poor, increment direct farmer deals only if farmer would work again
        if rating_data.get('would_work_again', True):
            trader.direct_farmer_deals = (trader.direct_farmer_deals or 0) + 1
        
        # Check if added_value is False - this is serious
        if not rating_data.get('added_value', True):
            logger.warning(f"Farmer {farmer_id} reported trader {trader_id} did NOT add value")
            # Increase reseller score
            self.calculate_trader_score(trader)
        
        try:
            db.session.commit()
            logger.info(f"Farmer {farmer_id} rated trader {trader_id}: {rating_data.get('overall_rating')}/5")
            return (True, 'Feedback recorded successfully')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording farmer feedback: {e}")
            return (False, str(e))
    
    def get_traders_needing_renewal(self):
        """Get traders whose verification is expiring soon or expired"""
        from models import User
        
        soon = datetime.utcnow() + timedelta(days=14)  # 2 weeks warning
        
        return User.query.filter(
            User.role == 'buyer',
            User.buyer_type == 'bulk_trader',
            User.trader_verified == True,
            User.verification_expiry < soon
        ).order_by(User.verification_expiry.asc()).all()


reseller_detector = ResellerDetector()
