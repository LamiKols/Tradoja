"""
TradojaIQ - AI Market Intelligence Engine
Smart Price Discovery, Trust Scores, Demand Forecasting
Integrated across all channels: Web, SMS, USSD, WhatsApp
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)


class TradojaIQService:
    
    TRUST_TIERS = {
        'platinum': {'min_score': 90, 'label': 'Platinum', 'emoji': '💎', 'color': '#E5E4E2'},
        'gold': {'min_score': 70, 'label': 'Gold', 'emoji': '🥇', 'color': '#FFD700'},
        'silver': {'min_score': 40, 'label': 'Silver', 'emoji': '🥈', 'color': '#C0C0C0'},
        'bronze': {'min_score': 0, 'label': 'Bronze', 'emoji': '🥉', 'color': '#CD7F32'},
    }
    
    NIGERIAN_STATES = [
        'Lagos', 'Kano', 'Ogun', 'Oyo', 'Rivers', 'Kaduna', 'Enugu', 'Abia',
        'Benue', 'Plateau', 'Niger', 'Kwara', 'Ondo', 'Ekiti', 'Osun',
        'Nasarawa', 'Kebbi', 'Sokoto', 'Zamfara', 'Katsina', 'Jigawa',
        'Bauchi', 'Gombe', 'Adamawa', 'Taraba', 'Borno', 'Yobe',
        'Cross River', 'Akwa Ibom', 'Edo', 'Delta', 'Bayelsa',
        'Imo', 'Anambra', 'Ebonyi', 'FCT'
    ]
    
    def get_price_intelligence(self, crop_name):
        """Get market price intelligence for a crop across all regions"""
        from models import db, Produce, Transaction, Order
        
        crop_name_lower = crop_name.lower().strip()
        now = datetime.utcnow()
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)
        
        result = {
            'crop': crop_name,
            'avg_price': 0,
            'min_price': 0,
            'max_price': 0,
            'median_price': 0,
            'total_listings': 0,
            'active_listings': 0,
            'sold_count_30d': 0,
            'price_trend': 'stable',
            'trend_percentage': 0,
            'regional_prices': {},
            'demand_score': 0,
            'supply_score': 0,
            'recommendation': '',
            'last_updated': now.isoformat()
        }
        
        try:
            all_listings = Produce.query.filter(
                func.lower(Produce.name).like(f'%{crop_name_lower}%')
            ).all()
            
            if not all_listings:
                result['recommendation'] = f'No listings found for {crop_name}. You could be the first seller!'
                return result
            
            active_listings = [p for p in all_listings if p.is_available and not p.is_sold]
            sold_listings = [p for p in all_listings if p.is_sold or not p.is_available]
            recent_sold = [p for p in sold_listings if p.sale_date and p.sale_date >= thirty_days_ago]
            
            all_prices = [p.price for p in all_listings if p.price and p.price > 0]
            
            if all_prices:
                result['avg_price'] = round(sum(all_prices) / len(all_prices), 2)
                result['min_price'] = min(all_prices)
                result['max_price'] = max(all_prices)
                sorted_prices = sorted(all_prices)
                mid = len(sorted_prices) // 2
                result['median_price'] = sorted_prices[mid] if len(sorted_prices) % 2 else round((sorted_prices[mid-1] + sorted_prices[mid]) / 2, 2)
            
            result['total_listings'] = len(all_listings)
            result['active_listings'] = len(active_listings)
            result['sold_count_30d'] = len(recent_sold)
            
            for listing in all_listings:
                location = (listing.listing_location or '').strip()
                if not location:
                    location = 'Unknown'
                region = location.split(',')[0].strip().title() if location else 'Unknown'
                
                if region not in result['regional_prices']:
                    result['regional_prices'][region] = {'prices': [], 'count': 0}
                if listing.price and listing.price > 0:
                    result['regional_prices'][region]['prices'].append(listing.price)
                    result['regional_prices'][region]['count'] += 1
            
            for region, data in result['regional_prices'].items():
                if data['prices']:
                    data['avg_price'] = round(sum(data['prices']) / len(data['prices']), 2)
                    data['min_price'] = min(data['prices'])
                    data['max_price'] = max(data['prices'])
                else:
                    data['avg_price'] = 0
                del data['prices']
            
            older_listings = [p for p in all_listings 
                            if p.date_listed and p.date_listed < thirty_days_ago and p.date_listed >= ninety_days_ago]
            recent_listings = [p for p in all_listings 
                             if p.date_listed and p.date_listed >= thirty_days_ago]
            
            older_prices = [p.price for p in older_listings if p.price and p.price > 0]
            recent_prices = [p.price for p in recent_listings if p.price and p.price > 0]
            
            if older_prices and recent_prices:
                old_avg = sum(older_prices) / len(older_prices)
                new_avg = sum(recent_prices) / len(recent_prices)
                if old_avg > 0:
                    change_pct = ((new_avg - old_avg) / old_avg) * 100
                    result['trend_percentage'] = round(change_pct, 1)
                    if change_pct > 5:
                        result['price_trend'] = 'rising'
                    elif change_pct < -5:
                        result['price_trend'] = 'falling'
                    else:
                        result['price_trend'] = 'stable'
            
            demand_signals = len(recent_sold) * 10 + len(active_listings) * 2
            result['demand_score'] = min(100, demand_signals)
            result['supply_score'] = min(100, len(active_listings) * 5)
            
            if result['demand_score'] > 60 and result['supply_score'] < 30:
                result['recommendation'] = f'High demand, low supply for {crop_name}. Great time to sell!'
            elif result['demand_score'] < 30 and result['supply_score'] > 60:
                result['recommendation'] = f'High supply for {crop_name}. Consider competitive pricing.'
            elif result['price_trend'] == 'rising':
                result['recommendation'] = f'{crop_name} prices trending up {result["trend_percentage"]}%. Good market conditions.'
            elif result['price_trend'] == 'falling':
                result['recommendation'] = f'{crop_name} prices down {abs(result["trend_percentage"])}%. Consider holding or diversifying.'
            else:
                result['recommendation'] = f'{crop_name} market is stable. Average price: N{result["avg_price"]:,.0f}'
            
        except Exception as e:
            logger.error(f"Price intelligence error for {crop_name}: {e}")
            result['recommendation'] = f'Market data for {crop_name} is being updated.'
        
        return result
    
    def get_price_guidance(self, crop_name, user_price, location=None):
        """Get price guidance for a specific listing - tells farmer if price is fair"""
        intelligence = self.get_price_intelligence(crop_name)
        
        guidance = {
            'crop': crop_name,
            'your_price': user_price,
            'market_avg': intelligence['avg_price'],
            'price_position': 'fair',
            'difference_pct': 0,
            'message': '',
            'regional_context': ''
        }
        
        if intelligence['avg_price'] > 0 and user_price > 0:
            diff_pct = ((user_price - intelligence['avg_price']) / intelligence['avg_price']) * 100
            guidance['difference_pct'] = round(diff_pct, 1)
            
            if diff_pct > 20:
                guidance['price_position'] = 'above_market'
                guidance['message'] = f'Your price (N{user_price:,.0f}) is {diff_pct:.0f}% above average (N{intelligence["avg_price"]:,.0f}). May take longer to sell.'
            elif diff_pct < -20:
                guidance['price_position'] = 'below_market'
                guidance['message'] = f'Your price (N{user_price:,.0f}) is {abs(diff_pct):.0f}% below average (N{intelligence["avg_price"]:,.0f}). Consider raising it.'
            else:
                guidance['price_position'] = 'fair'
                guidance['message'] = f'Your price (N{user_price:,.0f}) is near the market average (N{intelligence["avg_price"]:,.0f}). Good pricing!'
        else:
            guidance['message'] = f'Not enough market data for {crop_name} yet. Your listing helps build market intelligence.'
        
        if location and intelligence['regional_prices']:
            location_key = location.strip().title()
            for region, data in intelligence['regional_prices'].items():
                if location_key.lower() in region.lower() or region.lower() in location_key.lower():
                    guidance['regional_context'] = f'In {region}, avg price is N{data["avg_price"]:,.0f} ({data["count"]} listings)'
                    break
        
        return guidance
    
    def calculate_trust_score(self, user):
        """Calculate dynamic trust score for a user (0-100)"""
        from models import Order, Dispute, TraderFeedback, FarmerVouch
        
        score = 0
        breakdown = {}
        
        try:
            if user.is_verified_account():
                score += 20
                breakdown['verification'] = 20
            elif user.registration_status == 'lite':
                score += 5
                breakdown['verification'] = 5
            else:
                score += 10
                breakdown['verification'] = 10
            
            completed_orders_as_seller = Order.query.filter_by(
                farmer_id=user.id, status='completed'
            ).count()
            completed_orders_as_buyer = Order.query.filter_by(
                buyer_id=user.id, status='completed'
            ).count()
            total_completed = completed_orders_as_seller + completed_orders_as_buyer
            
            tx_score = min(25, total_completed * 3)
            score += tx_score
            breakdown['transactions'] = tx_score
            breakdown['completed_orders'] = total_completed
            
            avg_rating = user.average_rating or 0
            total_ratings = user.total_ratings or 0
            if total_ratings > 0:
                rating_score = min(20, int((avg_rating / 5.0) * 20))
                score += rating_score
                breakdown['ratings'] = rating_score
                breakdown['avg_rating'] = avg_rating
                breakdown['total_ratings'] = total_ratings
            
            disputes_against = Dispute.query.filter_by(respondent_id=user.id).count()
            disputes_resolved = Dispute.query.filter_by(
                respondent_id=user.id, status='resolved'
            ).count()
            
            if disputes_against == 0:
                score += 15
                breakdown['disputes'] = 15
            elif disputes_against > 0 and disputes_resolved == disputes_against:
                score += 10
                breakdown['disputes'] = 10
            else:
                penalty = min(15, disputes_against * 5)
                score -= penalty
                breakdown['disputes'] = -penalty
            
            account_age_days = 0
            if user.registration_date:
                account_age_days = (datetime.utcnow() - user.registration_date).days
            
            tenure_score = min(10, account_age_days // 30)
            score += tenure_score
            breakdown['tenure'] = tenure_score
            breakdown['account_age_days'] = account_age_days
            
            extras = 0
            if user.phone_verified:
                extras += 3
            if user.agent_verified:
                extras += 4
            if hasattr(user, 'id_verification_status') and user.id_verification_status == 'verified':
                extras += 3
            extras = min(10, extras)
            score += extras
            breakdown['verification_extras'] = extras
            
            score = max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Trust score calculation error for user {user.id}: {e}")
            score = max(0, min(100, score))
        
        tier = self._get_trust_tier(score)
        
        return {
            'score': score,
            'tier': tier['label'],
            'tier_key': self._get_tier_key(score),
            'emoji': tier['emoji'],
            'color': tier['color'],
            'breakdown': breakdown
        }
    
    def _get_trust_tier(self, score):
        for tier_key in ['platinum', 'gold', 'silver', 'bronze']:
            tier = self.TRUST_TIERS[tier_key]
            if score >= tier['min_score']:
                return tier
        return self.TRUST_TIERS['bronze']
    
    def _get_tier_key(self, score):
        for tier_key in ['platinum', 'gold', 'silver', 'bronze']:
            if score >= self.TRUST_TIERS[tier_key]['min_score']:
                return tier_key
        return 'bronze'
    
    def get_trust_badge_html(self, user):
        """Get HTML badge for trust score display"""
        trust = self.calculate_trust_score(user)
        tier_key = trust['tier_key']
        
        badge_classes = {
            'platinum': 'bg-light text-dark',
            'gold': 'bg-warning text-dark',
            'silver': 'bg-secondary',
            'bronze': 'bg-dark'
        }
        
        badge_class = badge_classes.get(tier_key, 'bg-secondary')
        return f'<span class="badge {badge_class}">{trust["emoji"]} {trust["tier"]}</span>'
    
    def get_trust_badge_text(self, user):
        """Get text-only trust badge for SMS/USSD/WhatsApp"""
        trust = self.calculate_trust_score(user)
        completed = trust['breakdown'].get('completed_orders', 0)
        return f"{trust['emoji']} {trust['tier']} Seller ({completed} deals)"
    
    def get_demand_insights(self, limit=10):
        """Get top demand insights across the marketplace"""
        from models import Produce, Order, SabiBuy
        
        insights = []
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        try:
            recent_orders = Order.query.filter(
                Order.created_at >= seven_days_ago
            ).all()
            
            crop_demand = {}
            for order in recent_orders:
                if order.produce:
                    crop = order.produce.name.strip().title()
                    if crop not in crop_demand:
                        crop_demand[crop] = {'orders_7d': 0, 'total_value': 0}
                    crop_demand[crop]['orders_7d'] += 1
                    crop_demand[crop]['total_value'] += order.total_amount or 0
            
            active_campaigns = SabiBuy.query.filter_by(status='active').all()
            for campaign in active_campaigns:
                if campaign.produce:
                    crop = campaign.produce.name.strip().title()
                    if crop not in crop_demand:
                        crop_demand[crop] = {'orders_7d': 0, 'total_value': 0}
                    crop_demand[crop]['orders_7d'] += campaign.current_quantity or 0
                    crop_demand[crop]['total_value'] += (campaign.selling_price or 0) * (campaign.current_quantity or 0)
            
            for crop, data in crop_demand.items():
                price_intel = self.get_price_intelligence(crop)
                insights.append({
                    'crop': crop,
                    'demand_orders_7d': data['orders_7d'],
                    'total_value_7d': data['total_value'],
                    'avg_price': price_intel['avg_price'],
                    'price_trend': price_intel['price_trend'],
                    'trend_pct': price_intel['trend_percentage'],
                    'active_listings': price_intel['active_listings'],
                    'recommendation': price_intel['recommendation']
                })
            
            insights.sort(key=lambda x: x['demand_orders_7d'], reverse=True)
            
        except Exception as e:
            logger.error(f"Demand insights error: {e}")
        
        return insights[:limit]
    
    def get_farmer_alert(self, user):
        """Generate personalized market alert for a farmer"""
        from models import Produce
        
        alerts = []
        
        try:
            farmer_crops = Produce.query.filter_by(farmer_id=user.id).all()
            crop_names = list(set([p.name.strip().title() for p in farmer_crops if p.name]))
            
            for crop in crop_names[:3]:
                intel = self.get_price_intelligence(crop)
                
                if intel['price_trend'] == 'rising' and intel['trend_percentage'] > 10:
                    alerts.append(
                        f"{crop} prices up {intel['trend_percentage']}%! "
                        f"Avg: N{intel['avg_price']:,.0f}. Good time to list."
                    )
                
                if intel['demand_score'] > 60 and intel['supply_score'] < 30:
                    alerts.append(
                        f"High demand for {crop} with low supply. "
                        f"List now for best prices!"
                    )
            
            demand_insights = self.get_demand_insights(5)
            trending_crops = [d['crop'] for d in demand_insights if d['demand_orders_7d'] > 3]
            new_opportunities = [c for c in trending_crops if c not in crop_names]
            
            if new_opportunities:
                top_opp = new_opportunities[0]
                alerts.append(f"Trending: {top_opp} is in high demand this week!")
            
        except Exception as e:
            logger.error(f"Farmer alert error for user {user.id}: {e}")
        
        return alerts
    
    def get_marketplace_summary(self):
        """Get overall marketplace intelligence summary"""
        from models import Produce, Order, User, SabiBuy, Transaction
        
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        summary = {
            'total_active_listings': 0,
            'total_farmers': 0,
            'total_buyers': 0,
            'total_orders_30d': 0,
            'total_gmv_30d': 0,
            'active_sabibuy_campaigns': 0,
            'top_crops': [],
            'trending_regions': [],
            'platform_health': 'good'
        }
        
        try:
            summary['total_active_listings'] = Produce.query.filter_by(is_available=True, is_sold=False).count()
            summary['total_farmers'] = User.query.filter_by(role='farmer').count()
            summary['total_buyers'] = User.query.filter_by(role='buyer').count()
            
            recent_orders = Order.query.filter(Order.created_at >= thirty_days_ago).all()
            summary['total_orders_30d'] = len(recent_orders)
            summary['total_gmv_30d'] = sum(o.total_amount or 0 for o in recent_orders)
            
            summary['active_sabibuy_campaigns'] = SabiBuy.query.filter_by(status='active').count()
            
            crop_counts = {}
            active_produce = Produce.query.filter_by(is_available=True, is_sold=False).all()
            for p in active_produce:
                crop = p.name.strip().title() if p.name else 'Unknown'
                crop_counts[crop] = crop_counts.get(crop, 0) + 1
            
            summary['top_crops'] = sorted(crop_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
        except Exception as e:
            logger.error(f"Marketplace summary error: {e}")
        
        return summary
    
    def format_price_sms(self, crop_name):
        """Format price intelligence for SMS/WhatsApp channel"""
        intel = self.get_price_intelligence(crop_name)
        
        if intel['avg_price'] == 0:
            return f"No market data for {crop_name} yet."
        
        trend_arrow = {'rising': '📈', 'falling': '📉', 'stable': '➡️'}
        arrow = trend_arrow.get(intel['price_trend'], '➡️')
        
        msg = f"📊 {crop_name.title()} Market Intel\n"
        msg += f"Avg: N{intel['avg_price']:,.0f}\n"
        msg += f"Range: N{intel['min_price']:,.0f} - N{intel['max_price']:,.0f}\n"
        msg += f"Trend: {arrow} {intel['price_trend'].title()}"
        if intel['trend_percentage'] != 0:
            msg += f" ({intel['trend_percentage']:+.1f}%)"
        msg += f"\nActive: {intel['active_listings']} listings\n"
        msg += f"Sold (30d): {intel['sold_count_30d']}\n"
        msg += f"💡 {intel['recommendation']}"
        
        return msg


tradojaiq = TradojaIQService()
