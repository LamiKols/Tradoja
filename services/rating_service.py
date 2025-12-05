"""
Rating Service for Tradoja
Handles star ratings for farmers, buyers, and transporters
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class RatingService:
    """
    Star rating system for marketplace participants
    
    Rating dimensions:
    - Farmers: quality, reliability, communication, pricing
    - Buyers/Traders: payment speed, communication, fairness
    - Transporters: timeliness, cargo care, professionalism
    """
    
    RATING_CATEGORIES = {
        'farmer': {
            'quality': 'Product Quality',
            'reliability': 'Delivery Reliability',
            'communication': 'Communication',
            'pricing': 'Fair Pricing'
        },
        'buyer': {
            'payment_speed': 'Payment Speed',
            'communication': 'Communication',
            'fairness': 'Negotiation Fairness',
            'reliability': 'Deal Reliability'
        },
        'transporter': {
            'timeliness': 'On-Time Delivery',
            'cargo_care': 'Cargo Care',
            'professionalism': 'Professionalism',
            'communication': 'Communication'
        }
    }
    
    def __init__(self):
        self.db = None
        self.User = None
        self.Rating = None
        self.Produce = None
        self.LogisticsRequest = None
    
    def _lazy_load_models(self):
        """Lazy load database models"""
        if self.db is None:
            from app import db
            from models import User, Produce, LogisticsRequest
            self.db = db
            self.User = User
            self.Produce = Produce
            self.LogisticsRequest = LogisticsRequest
    
    def submit_rating(
        self,
        rater_id: int,
        rated_id: int,
        overall_rating: int,
        category_ratings: Optional[Dict[str, int]] = None,
        comment: Optional[str] = None,
        produce_id: Optional[int] = None,
        logistics_id: Optional[int] = None,
        transaction_type: str = 'purchase'
    ) -> Dict[str, Any]:
        """
        Submit a rating for a user
        
        Args:
            rater_id: ID of user giving rating
            rated_id: ID of user being rated
            overall_rating: 1-5 star rating
            category_ratings: Optional dict of category ratings (1-5)
            comment: Optional text feedback
            produce_id: Related produce listing
            logistics_id: Related logistics request
            transaction_type: 'purchase', 'sale', 'logistics'
        
        Returns:
            dict with success status
        """
        self._lazy_load_models()
        
        try:
            if overall_rating < 1 or overall_rating > 5:
                return {'success': False, 'error': 'Rating must be between 1 and 5 stars'}
            
            rater = self.User.query.get(rater_id)
            rated = self.User.query.get(rated_id)
            
            if not rater:
                return {'success': False, 'error': 'Rater not found'}
            if not rated:
                return {'success': False, 'error': 'Rated user not found'}
            if rater_id == rated_id:
                return {'success': False, 'error': 'Cannot rate yourself'}
            
            current_total = (rated.average_rating or 0) * (rated.total_ratings or 0)
            new_count = (rated.total_ratings or 0) + 1
            rated.average_rating = (current_total + overall_rating) / new_count
            rated.total_ratings = new_count
            
            if transaction_type == 'sale' and rated.role == 'farmer':
                current_seller = (rated.rating_as_seller or 0) * max(1, new_count - 1)
                rated.rating_as_seller = (current_seller + overall_rating) / new_count
            
            if transaction_type == 'purchase' and rated.role == 'buyer':
                current_buyer = (rated.rating_as_buyer or 0) * max(1, new_count - 1)
                rated.rating_as_buyer = (current_buyer + overall_rating) / new_count
            
            self.db.session.commit()
            
            logger.info(f"Rating submitted: User {rater_id} rated User {rated_id} with {overall_rating}/5")
            
            return {
                'success': True,
                'new_average': rated.average_rating,
                'total_ratings': rated.total_ratings,
                'message': f'Thank you for your feedback! Rating: {overall_rating}/5 stars'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error submitting rating: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_rating_summary(self, user_id: int) -> Dict[str, Any]:
        """Get rating summary for a user"""
        self._lazy_load_models()
        
        try:
            user = self.User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            return {
                'success': True,
                'user_id': user_id,
                'average_rating': round(user.average_rating or 0, 1),
                'total_ratings': user.total_ratings or 0,
                'rating_as_seller': round(user.rating_as_seller or 0, 1),
                'rating_as_buyer': round(user.rating_as_buyer or 0, 1),
                'star_display': self._get_star_display(user.average_rating or 0),
                'badge': self._get_rating_badge(user.average_rating or 0, user.total_ratings or 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting rating summary: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_star_display(self, rating: float) -> str:
        """Get star emoji display for rating"""
        full_stars = int(rating)
        half_star = 1 if rating - full_stars >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        return '★' * full_stars + '½' * half_star + '☆' * empty_stars
    
    def _get_rating_badge(self, average: float, count: int) -> Optional[Dict[str, str]]:
        """Get achievement badge based on rating and count"""
        if count < 5:
            return None
        
        if average >= 4.8 and count >= 50:
            return {'name': 'Top Rated', 'class': 'bg-success', 'icon': '🏆'}
        elif average >= 4.5 and count >= 20:
            return {'name': 'Excellent', 'class': 'bg-primary', 'icon': '⭐'}
        elif average >= 4.0 and count >= 10:
            return {'name': 'Trusted', 'class': 'bg-info', 'icon': '✓'}
        elif average < 2.5:
            return {'name': 'Needs Improvement', 'class': 'bg-warning', 'icon': '⚠'}
        
        return None
    
    def get_top_rated_users(
        self,
        role: Optional[str] = None,
        limit: int = 20,
        min_ratings: int = 5
    ) -> List[Dict[str, Any]]:
        """Get leaderboard of top-rated users"""
        self._lazy_load_models()
        
        try:
            query = self.User.query.filter(
                self.User.total_ratings >= min_ratings
            )
            
            if role:
                query = query.filter_by(role=role)
            
            users = query.order_by(
                self.User.average_rating.desc(),
                self.User.total_ratings.desc()
            ).limit(limit).all()
            
            return [
                {
                    'rank': i + 1,
                    'user_id': u.id,
                    'name': u.name,
                    'role': u.role,
                    'average_rating': round(u.average_rating or 0, 1),
                    'total_ratings': u.total_ratings,
                    'star_display': self._get_star_display(u.average_rating or 0),
                    'badge': self._get_rating_badge(u.average_rating or 0, u.total_ratings or 0)
                }
                for i, u in enumerate(users)
            ]
            
        except Exception as e:
            logger.error(f"Error getting top rated users: {e}")
            return []
    
    def prompt_for_rating_after_transaction(
        self,
        buyer_id: int,
        seller_id: int,
        produce_id: int
    ) -> Dict[str, Any]:
        """Generate rating prompt info after a completed transaction"""
        self._lazy_load_models()
        
        try:
            buyer = self.User.query.get(buyer_id)
            seller = self.User.query.get(seller_id)
            produce = self.Produce.query.get(produce_id)
            
            if not all([buyer, seller, produce]):
                return {'success': False, 'error': 'Invalid transaction participants'}
            
            return {
                'success': True,
                'buyer': {
                    'id': buyer_id,
                    'should_rate_seller': True,
                    'seller_name': seller.name,
                    'produce_name': produce.name
                },
                'seller': {
                    'id': seller_id,
                    'should_rate_buyer': True,
                    'buyer_name': buyer.name,
                    'produce_name': produce.name
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating rating prompt: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_rating_stats(self) -> Dict[str, Any]:
        """Get platform-wide rating statistics"""
        self._lazy_load_models()
        
        try:
            rated_users = self.User.query.filter(
                self.User.total_ratings > 0
            ).all()
            
            if not rated_users:
                return {
                    'total_ratings': 0,
                    'average_platform_rating': 0,
                    'rated_users': 0
                }
            
            total_ratings = sum(u.total_ratings for u in rated_users)
            weighted_sum = sum(u.average_rating * u.total_ratings for u in rated_users)
            platform_average = weighted_sum / total_ratings if total_ratings > 0 else 0
            
            high_rated = sum(1 for u in rated_users if u.average_rating >= 4.0)
            low_rated = sum(1 for u in rated_users if u.average_rating < 3.0)
            
            farmers = [u for u in rated_users if u.role == 'farmer']
            buyers = [u for u in rated_users if u.role == 'buyer']
            
            farmer_avg = sum(u.average_rating for u in farmers) / len(farmers) if farmers else 0
            buyer_avg = sum(u.average_rating for u in buyers) / len(buyers) if buyers else 0
            
            return {
                'total_ratings': total_ratings,
                'rated_users': len(rated_users),
                'average_platform_rating': round(platform_average, 2),
                'high_rated_users': high_rated,
                'low_rated_users': low_rated,
                'farmer_average': round(farmer_avg, 2),
                'buyer_average': round(buyer_avg, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting rating stats: {e}")
            return {'error': str(e)}


rating_service = RatingService()
