"""
AI-Powered Marketplace Matchmaking Engine for AgroLink
Connects farmers with buyers using intelligent algorithms and data analysis
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy import func, and_, or_
from models import db, User, Produce, Message, SMSInteraction
import re

class MatchmakingEngine:
    """Rule-based matchmaking engine with ML preparation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def find_buyer_matches(self, farmer_id: int, produce_id: Optional[int] = None) -> List[Dict]:
        """Find best-matching buyers for a farmer's produce"""
        try:
            farmer = User.query.get(farmer_id)
            if not farmer or not farmer.is_farmer():
                return []
            
            # Get farmer's produce listings
            if produce_id:
                produce_listings = Produce.query.filter_by(
                    farmer_id=farmer_id, 
                    id=produce_id,
                    is_available=True
                ).all()
            else:
                produce_listings = Produce.query.filter_by(
                    farmer_id=farmer_id,
                    is_available=True
                ).all()
            
            if not produce_listings:
                return []
            
            all_matches = []
            for produce in produce_listings:
                matches = self._find_buyers_for_produce(farmer, produce)
                all_matches.extend(matches)
            
            # Sort by overall match score
            all_matches.sort(key=lambda x: x['match_score'], reverse=True)
            return all_matches[:10]  # Top 10 matches
            
        except Exception as e:
            self.logger.error(f"Error finding buyer matches: {e}")
            return []
    
    def find_seller_matches(self, buyer_id: int, crop_preferences: List[str] = None) -> List[Dict]:
        """Find best-matching sellers for a buyer"""
        try:
            buyer = User.query.get(buyer_id)
            if not buyer or not buyer.is_buyer():
                return []
            
            # Get buyer's message history to infer preferences
            if not crop_preferences:
                crop_preferences = self._infer_buyer_preferences(buyer_id)
            
            # Find relevant produce listings
            query = Produce.query.filter_by(is_available=True)
            
            if crop_preferences:
                # Filter by crop preferences
                crop_filter = or_(*[
                    Produce.name.ilike(f'%{crop}%') for crop in crop_preferences
                ])
                query = query.filter(crop_filter)
            
            produce_listings = query.limit(50).all()  # Limit for performance
            
            matches = []
            for produce in produce_listings:
                farmer = produce.farmer
                match_data = self._calculate_seller_match(buyer, farmer, produce)
                if match_data['match_score'] > 0.3:  # Minimum threshold
                    matches.append(match_data)
            
            # Sort by match score
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches[:10]  # Top 10 matches
            
        except Exception as e:
            self.logger.error(f"Error finding seller matches: {e}")
            return []
    
    def _find_buyers_for_produce(self, farmer: User, produce: Produce) -> List[Dict]:
        """Find buyers for a specific produce listing"""
        # Get all buyers
        buyers = User.query.filter_by(role='buyer').all()
        
        matches = []
        for buyer in buyers:
            match_data = self._calculate_buyer_match(farmer, buyer, produce)
            if match_data['match_score'] > 0.3:  # Minimum threshold
                matches.append(match_data)
        
        return matches
    
    def _calculate_buyer_match(self, farmer: User, buyer: User, produce: Produce) -> Dict:
        """Calculate match score between farmer and buyer"""
        score = 0.0
        factors = {}
        
        # 1. Crop interest match (based on message history)
        crop_interest = self._get_buyer_crop_interest(buyer.id, produce.name)
        factors['crop_interest'] = crop_interest
        score += crop_interest * 0.3
        
        # 2. Previous interaction history
        interaction_score = self._get_interaction_score(farmer.id, buyer.id)
        factors['interaction_history'] = interaction_score
        score += interaction_score * 0.25
        
        # 3. Price compatibility
        price_score = self._calculate_price_compatibility(buyer.id, produce.price)
        factors['price_compatibility'] = price_score
        score += price_score * 0.2
        
        # 4. Activity level (recent activity on platform)
        activity_score = self._get_user_activity_score(buyer.id)
        factors['activity_level'] = activity_score
        score += activity_score * 0.15
        
        # 5. Response rate (how quickly they respond to messages)
        response_score = self._get_response_rate_score(buyer.id)
        factors['response_rate'] = response_score
        score += response_score * 0.1
        
        return {
            'buyer_id': buyer.id,
            'buyer_name': buyer.name,
            'buyer_email': buyer.email,
            'buyer_phone': buyer.phone_number,
            'produce_id': produce.id,
            'produce_name': produce.name,
            'produce_price': produce.price,
            'match_score': min(score, 1.0),  # Cap at 1.0
            'match_factors': factors,
            'recommendation_reason': self._generate_recommendation_reason(factors)
        }
    
    def _calculate_seller_match(self, buyer: User, farmer: User, produce: Produce) -> Dict:
        """Calculate match score between buyer and seller"""
        score = 0.0
        factors = {}
        
        # 1. Crop preference match
        crop_preferences = self._infer_buyer_preferences(buyer.id)
        crop_match = 1.0 if any(crop.lower() in produce.name.lower() for crop in crop_preferences) else 0.3
        factors['crop_match'] = crop_match
        score += crop_match * 0.3
        
        # 2. Price attractiveness
        price_score = self._calculate_price_attractiveness(produce.price)
        factors['price_attractiveness'] = price_score
        score += price_score * 0.25
        
        # 3. Farmer reliability
        reliability_score = self._get_farmer_reliability(farmer.id)
        factors['farmer_reliability'] = reliability_score
        score += reliability_score * 0.2
        
        # 4. Freshness (how recently listed)
        freshness_score = self._calculate_listing_freshness(produce.date_listed)
        factors['listing_freshness'] = freshness_score
        score += freshness_score * 0.15
        
        # 5. Previous interaction history
        interaction_score = self._get_interaction_score(farmer.id, buyer.id)
        factors['interaction_history'] = interaction_score
        score += interaction_score * 0.1
        
        return {
            'farmer_id': farmer.id,
            'farmer_name': farmer.name,
            'farmer_email': farmer.email,
            'farmer_phone': farmer.phone_number,
            'produce_id': produce.id,
            'produce_name': produce.name,
            'produce_quantity': produce.quantity,
            'produce_price': produce.price,
            'match_score': min(score, 1.0),
            'match_factors': factors,
            'recommendation_reason': self._generate_recommendation_reason(factors)
        }
    
    def _get_buyer_crop_interest(self, buyer_id: int, crop_name: str) -> float:
        """Calculate buyer's interest in specific crop based on message history"""
        try:
            # Count messages mentioning this crop
            crop_mentions = Message.query.filter(
                or_(Message.sender_id == buyer_id, Message.receiver_id == buyer_id),
                Message.message_body.ilike(f'%{crop_name}%')
            ).count()
            
            # Also check SMS interactions if buyer has SMS enabled
            sms_mentions = SMSInteraction.query.filter(
                SMSInteraction.phone_number == User.query.get(buyer_id).phone_number,
                SMSInteraction.content.ilike(f'%{crop_name}%')
            ).count() if User.query.get(buyer_id).phone_number else 0
            
            total_mentions = crop_mentions + sms_mentions
            
            # Normalize score (more mentions = higher interest)
            return min(total_mentions / 10.0, 1.0)
            
        except Exception:
            return 0.5  # Default score
    
    def _get_interaction_score(self, farmer_id: int, buyer_id: int) -> float:
        """Calculate interaction score between farmer and buyer"""
        try:
            # Count messages between these users
            message_count = Message.query.filter(
                or_(
                    and_(Message.sender_id == farmer_id, Message.receiver_id == buyer_id),
                    and_(Message.sender_id == buyer_id, Message.receiver_id == farmer_id)
                )
            ).count()
            
            # Higher interaction = higher score
            return min(message_count / 20.0, 1.0)
            
        except Exception:
            return 0.0
    
    def _calculate_price_compatibility(self, buyer_id: int, price: float) -> float:
        """Calculate if price is compatible with buyer's typical range"""
        try:
            # Get buyer's message history to infer price preferences
            # This is a simplified version - in practice, you'd analyze message content
            # For now, we'll use a general price attractiveness formula
            
            # Assuming lower prices are more attractive to buyers
            if price < 50000:  # NGN 50,000
                return 1.0
            elif price < 100000:  # NGN 100,000
                return 0.8
            elif price < 200000:  # NGN 200,000
                return 0.6
            else:
                return 0.4
                
        except Exception:
            return 0.5
    
    def _get_user_activity_score(self, user_id: int) -> float:
        """Calculate user's activity level on platform"""
        try:
            # Check recent messages (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_messages = Message.query.filter(
                or_(Message.sender_id == user_id, Message.receiver_id == user_id),
                Message.timestamp >= thirty_days_ago
            ).count()
            
            # Check recent SMS activity
            user = User.query.get(user_id)
            recent_sms = 0
            if user and user.phone_number:
                recent_sms = SMSInteraction.query.filter(
                    SMSInteraction.phone_number == user.phone_number,
                    SMSInteraction.timestamp >= thirty_days_ago
                ).count()
            
            total_activity = recent_messages + recent_sms
            return min(total_activity / 30.0, 1.0)  # Normalize
            
        except Exception:
            return 0.5
    
    def _get_response_rate_score(self, user_id: int) -> float:
        """Calculate user's response rate and speed"""
        try:
            # This is a simplified version
            # In practice, you'd track response times between messages
            
            # For now, base it on recent activity
            recent_activity = self._get_user_activity_score(user_id)
            return recent_activity  # Active users tend to respond faster
            
        except Exception:
            return 0.5
    
    def _infer_buyer_preferences(self, buyer_id: int) -> List[str]:
        """Infer buyer's crop preferences from message history"""
        try:
            # Common Nigerian crops to look for in messages
            common_crops = [
                'tomatoes', 'tomato', 'rice', 'maize', 'corn', 'cassava', 'yam',
                'plantain', 'banana', 'pepper', 'onion', 'garlic', 'ginger',
                'beans', 'cowpea', 'soybean', 'groundnut', 'peanut'
            ]
            
            preferences = []
            
            # Check messages for crop mentions
            messages = Message.query.filter(
                or_(Message.sender_id == buyer_id, Message.receiver_id == buyer_id)
            ).all()
            
            for message in messages:
                content = message.message_body.lower()
                for crop in common_crops:
                    if crop in content and crop not in preferences:
                        preferences.append(crop)
            
            # Also check SMS interactions
            user = User.query.get(buyer_id)
            if user and user.phone_number:
                sms_interactions = SMSInteraction.query.filter_by(
                    phone_number=user.phone_number
                ).all()
                
                for sms in sms_interactions:
                    content = sms.content.lower()
                    for crop in common_crops:
                        if crop in content and crop not in preferences:
                            preferences.append(crop)
            
            return preferences[:5]  # Top 5 preferences
            
        except Exception:
            return ['tomatoes', 'rice', 'maize']  # Default preferences
    
    def _calculate_price_attractiveness(self, price: float) -> float:
        """Calculate how attractive a price is (generally lower is better for buyers)"""
        # This is a simplified formula
        if price < 30000:  # Very affordable
            return 1.0
        elif price < 60000:  # Affordable
            return 0.8
        elif price < 100000:  # Moderate
            return 0.6
        elif price < 200000:  # Expensive
            return 0.4
        else:  # Very expensive
            return 0.2
    
    def _get_farmer_reliability(self, farmer_id: int) -> float:
        """Calculate farmer's reliability score"""
        try:
            farmer = User.query.get(farmer_id)
            if not farmer:
                return 0.5
            
            # Factor 1: How long they've been on platform
            days_registered = (datetime.utcnow() - farmer.registration_date).days
            longevity_score = min(days_registered / 365.0, 1.0)  # Max 1 year
            
            # Factor 2: Number of produce listings (more listings = more active)
            listing_count = Produce.query.filter_by(farmer_id=farmer_id).count()
            activity_score = min(listing_count / 20.0, 1.0)  # Normalize
            
            # Factor 3: Response to messages
            response_score = self._get_response_rate_score(farmer_id)
            
            # Weighted average
            reliability = (longevity_score * 0.4 + activity_score * 0.4 + response_score * 0.2)
            return reliability
            
        except Exception:
            return 0.5
    
    def _calculate_listing_freshness(self, date_listed: datetime) -> float:
        """Calculate how fresh/recent a listing is"""
        try:
            days_ago = (datetime.utcnow() - date_listed).days
            
            if days_ago <= 1:  # Within 24 hours
                return 1.0
            elif days_ago <= 3:  # Within 3 days
                return 0.8
            elif days_ago <= 7:  # Within a week
                return 0.6
            elif days_ago <= 14:  # Within 2 weeks
                return 0.4
            else:  # Older than 2 weeks
                return 0.2
                
        except Exception:
            return 0.5
    
    def _generate_recommendation_reason(self, factors: Dict) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []
        
        if factors.get('crop_interest', 0) > 0.7:
            reasons.append("strong interest in this crop")
        elif factors.get('crop_match', 0) > 0.7:
            reasons.append("matches your crop preferences")
            
        if factors.get('interaction_history', 0) > 0.5:
            reasons.append("previous successful interactions")
            
        if factors.get('price_compatibility', 0) > 0.7 or factors.get('price_attractiveness', 0) > 0.7:
            reasons.append("attractive pricing")
            
        if factors.get('farmer_reliability', 0) > 0.7:
            reasons.append("reliable seller")
            
        if factors.get('activity_level', 0) > 0.7:
            reasons.append("active on platform")
            
        if factors.get('listing_freshness', 0) > 0.8:
            reasons.append("recently listed")
        
        if reasons:
            return "Recommended due to: " + ", ".join(reasons)
        else:
            return "Good potential match based on platform data"
    
    def record_match_outcome(self, farmer_id: int, buyer_id: int, produce_id: int, 
                           action: str, outcome: str = None) -> bool:
        """Record match outcome for ML training data"""
        try:
            # Store match outcome in database for future ML model training
            # For now, we'll log it for analysis
            
            self.logger.info(f"Match outcome recorded: "
                           f"Farmer {farmer_id} - Buyer {buyer_id} - Produce {produce_id} "
                           f"Action: {action} - Outcome: {outcome}")
            
            # In future versions, this would be stored in a MatchOutcome table
            return True
            
        except Exception as e:
            self.logger.error(f"Error recording match outcome: {e}")
            return False
    
    def get_match_statistics(self) -> Dict:
        """Get statistics about matchmaking performance"""
        try:
            # For now, return basic statistics
            # In production, this would analyze MatchOutcome table
            
            total_farmers = User.query.filter_by(role='farmer').count()
            total_buyers = User.query.filter_by(role='buyer').count()
            total_produce = Produce.query.filter_by(is_available=True).count()
            
            # Estimate potential matches
            potential_matches = total_farmers * total_buyers * 0.1  # Rough estimate
            
            return {
                'total_farmers': total_farmers,
                'total_buyers': total_buyers,
                'available_listings': total_produce,
                'potential_matches': int(potential_matches),
                'match_success_rate': 0.75,  # Placeholder
                'avg_match_score': 0.65,  # Placeholder
                'total_recommendations_sent': 0,  # Will be tracked in future
                'total_matches_accepted': 0  # Will be tracked in future
            }
            
        except Exception as e:
            self.logger.error(f"Error getting match statistics: {e}")
            return {}