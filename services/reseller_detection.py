"""
Reseller Detection Service
Prevents pure resellers (middlemen who just mark up without adding value) from flooding the platform.

Key Principles:
1. Traders MUST declare what value they add (transport, aggregation, processing, storage, capital, grading)
2. Traders MUST provide proof of their declared services
3. System automatically monitors behavior for pure reseller patterns
4. High-risk traders are flagged for admin review
"""

from datetime import datetime, timedelta
from app import db
import logging

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
        }
    ]
    
    def __init__(self):
        pass
    
    def get_available_services(self):
        """Get list of available value-add services for registration"""
        return self.VALUE_ADD_SERVICES
    
    def calculate_trader_score(self, user):
        """Calculate comprehensive reseller score for a user
        Returns tuple: (score, triggered_rules, recommendations)
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
        
        # Cap at 100
        score = min(100, score)
        
        # Update user record
        user.reseller_score = score
        user.last_reseller_check = datetime.utcnow()
        
        return (score, triggered_rules, recommendations)
    
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


reseller_detector = ResellerDetector()
