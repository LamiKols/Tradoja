"""
Advanced Analytics Service for AgroLink
Provides comprehensive market insights and user engagement analytics
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_, extract, text
from models import db, User, Produce, Message, LogisticsRequest, FundingApplication, CSAData, ExportListing, SMSInteraction, MatchRecommendation
import json
import csv
import io
from flask import make_response

class AnalyticsService:
    """Advanced analytics service for market and user insights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_market_overview(self, days: int = 30) -> Dict:
        """Get comprehensive market overview"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total produce metrics
            total_produce = Produce.query.count()
            active_produce = Produce.query.filter_by(is_available=True).count()
            recent_listings = Produce.query.filter(Produce.date_listed >= cutoff_date).count()
            
            # Value metrics
            total_value = db.session.query(func.sum(Produce.price)).filter_by(is_available=True).scalar() or 0
            avg_price = db.session.query(func.avg(Produce.price)).filter_by(is_available=True).scalar() or 0
            
            # User metrics
            total_farmers = User.query.filter_by(role='farmer').count()
            total_buyers = User.query.filter_by(role='buyer').count()
            active_farmers = db.session.query(func.count(func.distinct(Produce.farmer_id))).filter_by(is_available=True).scalar()
            
            # Export metrics
            export_listings = ExportListing.query.count()
            approved_exports = ExportListing.query.filter_by(status='approved').count()
            export_value = db.session.query(func.sum(ExportListing.price)).scalar() or 0
            
            # SMS engagement
            sms_users = User.query.filter_by(sms_enabled=True).count()
            recent_sms = SMSInteraction.query.filter(SMSInteraction.timestamp >= cutoff_date).count()
            
            return {
                'total_produce_listings': total_produce,
                'active_listings': active_produce,
                'recent_listings': recent_listings,
                'total_market_value': total_value,
                'average_price': avg_price,
                'total_farmers': total_farmers,
                'total_buyers': total_buyers,
                'active_farmers': active_farmers,
                'export_listings': export_listings,
                'approved_exports': approved_exports,
                'export_value': export_value,
                'sms_enabled_users': sms_users,
                'recent_sms_interactions': recent_sms,
                'platform_growth_rate': self._calculate_growth_rate(days),
                'market_penetration': {
                    'sms_penetration': (sms_users / (total_farmers + total_buyers) * 100) if (total_farmers + total_buyers) > 0 else 0,
                    'export_penetration': (export_listings / total_produce * 100) if total_produce > 0 else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market overview: {e}")
            return {}
    
    def get_crop_analytics(self) -> Dict:
        """Get detailed crop-wise analytics"""
        try:
            # Crop distribution
            crop_query = db.session.query(
                Produce.name,
                func.count(Produce.id).label('listings'),
                func.sum(Produce.price).label('total_value'),
                func.avg(Produce.price).label('avg_price'),
                func.count(func.distinct(Produce.farmer_id)).label('unique_farmers')
            ).group_by(Produce.name).order_by(func.count(Produce.id).desc())
            
            crop_data = []
            for crop in crop_query.all():
                crop_data.append({
                    'crop_name': crop.name,
                    'total_listings': crop.listings,
                    'total_value': float(crop.total_value or 0),
                    'average_price': float(crop.avg_price or 0),
                    'unique_farmers': crop.unique_farmers,
                    'market_share': 0  # Will be calculated after getting totals
                })
            
            # Calculate market share
            total_listings = sum(crop['total_listings'] for crop in crop_data)
            for crop in crop_data:
                crop['market_share'] = (crop['total_listings'] / total_listings * 100) if total_listings > 0 else 0
            
            # Price trends by crop (last 6 months)
            price_trends = self._get_price_trends_by_crop()
            
            # Top performing crops
            top_crops = sorted(crop_data, key=lambda x: x['total_value'], reverse=True)[:10]
            
            return {
                'crop_distribution': crop_data,
                'price_trends': price_trends,
                'top_performing_crops': top_crops,
                'total_crop_types': len(crop_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting crop analytics: {e}")
            return {}
    
    def get_geographic_analytics(self) -> Dict:
        """Get geographic distribution and analytics"""
        try:
            # State-wise distribution of farmers
            farmers_by_state = db.session.query(
                User.state,
                func.count(User.id).label('farmer_count'),
                func.count(func.distinct(Produce.id)).label('produce_count'),
                func.sum(Produce.price).label('total_value')
            ).join(Produce, User.id == Produce.farmer_id, isouter=True)\
             .filter(User.role == 'farmer')\
             .group_by(User.state)\
             .order_by(func.count(User.id).desc()).all()
            
            state_data = []
            for state in farmers_by_state:
                if state.state:  # Only include states with data
                    state_data.append({
                        'state': state.state,
                        'farmer_count': state.farmer_count,
                        'produce_count': state.produce_count or 0,
                        'total_value': float(state.total_value or 0),
                        'avg_value_per_farmer': float((state.total_value or 0) / state.farmer_count) if state.farmer_count > 0 else 0
                    })
            
            # Buyer distribution
            buyers_by_state = db.session.query(
                User.state,
                func.count(User.id).label('buyer_count')
            ).filter(User.role == 'buyer')\
             .group_by(User.state)\
             .order_by(func.count(User.id).desc()).all()
            
            buyer_data = {state.state: state.buyer_count for state in buyers_by_state if state.state}
            
            # Supply-demand analysis by state
            supply_demand = []
            for state_info in state_data:
                state_name = state_info['state']
                supply = state_info['produce_count']
                demand = buyer_data.get(state_name, 0)
                
                supply_demand.append({
                    'state': state_name,
                    'supply': supply,
                    'demand': demand,
                    'supply_demand_ratio': supply / demand if demand > 0 else float('inf'),
                    'market_balance': 'oversupply' if supply > demand * 1.5 else 'undersupply' if demand > supply * 1.5 else 'balanced'
                })
            
            return {
                'farmers_by_state': state_data,
                'buyers_by_state': buyer_data,
                'supply_demand_analysis': supply_demand,
                'top_producing_states': sorted(state_data, key=lambda x: x['total_value'], reverse=True)[:5]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting geographic analytics: {e}")
            return {}
    
    def get_user_engagement_analytics(self) -> Dict:
        """Get detailed user engagement metrics"""
        try:
            # Platform usage patterns
            web_users = User.query.filter_by(sms_enabled=False).count()
            sms_users = User.query.filter_by(sms_enabled=True).count()
            
            # Message activity
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_messages = Message.query.filter(Message.timestamp >= thirty_days_ago).count()
            active_messagers = db.session.query(func.count(func.distinct(Message.sender_id)))\
                .filter(Message.timestamp >= thirty_days_ago).scalar()
            
            # SMS engagement
            recent_sms = SMSInteraction.query.filter(SMSInteraction.timestamp >= thirty_days_ago).count()
            unique_sms_users = db.session.query(func.count(func.distinct(SMSInteraction.phone_number)))\
                .filter(SMSInteraction.timestamp >= thirty_days_ago).scalar()
            
            # Listing engagement
            farmers_with_listings = db.session.query(func.count(func.distinct(Produce.farmer_id))).scalar()
            total_farmers = User.query.filter_by(role='farmer').count()
            listing_engagement_rate = (farmers_with_listings / total_farmers * 100) if total_farmers > 0 else 0
            
            # Feature adoption
            funding_applications = FundingApplication.query.count()
            csa_usage = CSAData.query.count()
            export_usage = ExportListing.query.count()
            logistics_usage = LogisticsRequest.query.count()
            
            # AI matchmaking engagement
            ai_recommendations = MatchRecommendation.query.count()
            accepted_recommendations = MatchRecommendation.query.filter_by(status='accepted').count()
            ai_acceptance_rate = (accepted_recommendations / ai_recommendations * 100) if ai_recommendations > 0 else 0
            
            return {
                'platform_usage': {
                    'web_users': web_users,
                    'sms_users': sms_users,
                    'sms_adoption_rate': (sms_users / (web_users + sms_users) * 100) if (web_users + sms_users) > 0 else 0
                },
                'communication_activity': {
                    'recent_messages': recent_messages,
                    'active_messagers': active_messagers,
                    'recent_sms': recent_sms,
                    'unique_sms_users': unique_sms_users,
                    'avg_messages_per_user': recent_messages / active_messagers if active_messagers > 0 else 0
                },
                'feature_adoption': {
                    'listing_engagement_rate': listing_engagement_rate,
                    'funding_applications': funding_applications,
                    'csa_tool_usage': csa_usage,
                    'export_listings': export_usage,
                    'logistics_requests': logistics_usage
                },
                'ai_matchmaking': {
                    'total_recommendations': ai_recommendations,
                    'accepted_recommendations': accepted_recommendations,
                    'acceptance_rate': ai_acceptance_rate
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user engagement analytics: {e}")
            return {}
    
    def get_bottleneck_analysis(self) -> Dict:
        """Identify platform bottlenecks and recommend interventions"""
        try:
            bottlenecks = []
            recommendations = []
            
            # 1. Unsold produce analysis
            total_listings = Produce.query.count()
            old_listings = Produce.query.filter(
                Produce.date_listed < datetime.utcnow() - timedelta(days=30),
                Produce.is_available == True
            ).count()
            
            if old_listings > total_listings * 0.3:  # More than 30% old listings
                bottlenecks.append({
                    'type': 'unsold_produce',
                    'severity': 'high',
                    'description': f'{old_listings} listings over 30 days old',
                    'impact': 'Farmer revenue loss, platform credibility'
                })
                recommendations.append({
                    'area': 'unsold_produce',
                    'action': 'Implement AI-powered demand forecasting and price optimization',
                    'priority': 'high'
                })
            
            # 2. Low buyer engagement
            total_buyers = User.query.filter_by(role='buyer').count()
            active_buyers = db.session.query(func.count(func.distinct(Message.sender_id)))\
                .join(User, Message.sender_id == User.id)\
                .filter(User.role == 'buyer').scalar()
            
            buyer_engagement_rate = (active_buyers / total_buyers * 100) if total_buyers > 0 else 0
            
            if buyer_engagement_rate < 50:
                bottlenecks.append({
                    'type': 'low_buyer_engagement',
                    'severity': 'medium',
                    'description': f'Only {buyer_engagement_rate:.1f}% of buyers are actively engaging',
                    'impact': 'Reduced marketplace liquidity'
                })
                recommendations.append({
                    'area': 'buyer_engagement',
                    'action': 'Launch buyer incentive programs and improve search/discovery features',
                    'priority': 'medium'
                })
            
            # 3. SMS adoption in rural areas
            total_users = User.query.count()
            sms_users = User.query.filter_by(sms_enabled=True).count()
            sms_adoption_rate = (sms_users / total_users * 100) if total_users > 0 else 0
            
            if sms_adoption_rate < 30:
                bottlenecks.append({
                    'type': 'low_sms_adoption',
                    'severity': 'medium',
                    'description': f'SMS adoption rate is only {sms_adoption_rate:.1f}%',
                    'impact': 'Limited rural farmer access'
                })
                recommendations.append({
                    'area': 'sms_adoption',
                    'action': 'Increase SMS marketing and partnerships with rural cooperatives',
                    'priority': 'medium'
                })
            
            # 4. Logistics bottlenecks
            pending_logistics = LogisticsRequest.query.filter_by(status='pending').count()
            total_logistics = LogisticsRequest.query.count()
            
            if total_logistics > 0 and pending_logistics / total_logistics > 0.4:
                bottlenecks.append({
                    'type': 'logistics_delays',
                    'severity': 'high',
                    'description': f'{pending_logistics} pending logistics requests',
                    'impact': 'Delivery delays, customer satisfaction'
                })
                recommendations.append({
                    'area': 'logistics',
                    'action': 'Expand logistics partner network and implement automated routing',
                    'priority': 'high'
                })
            
            # 5. Geographic imbalances
            geographic_data = self.get_geographic_analytics()
            supply_demand = geographic_data.get('supply_demand_analysis', [])
            
            oversupply_states = [s for s in supply_demand if s.get('market_balance') == 'oversupply']
            undersupply_states = [s for s in supply_demand if s.get('market_balance') == 'undersupply']
            
            if len(oversupply_states) > 3 or len(undersupply_states) > 3:
                bottlenecks.append({
                    'type': 'geographic_imbalance',
                    'severity': 'medium',
                    'description': f'{len(oversupply_states)} oversupply and {len(undersupply_states)} undersupply states',
                    'impact': 'Inefficient resource allocation'
                })
                recommendations.append({
                    'area': 'geographic_balance',
                    'action': 'Implement cross-state trading incentives and logistics optimization',
                    'priority': 'medium'
                })
            
            return {
                'bottlenecks': bottlenecks,
                'recommendations': recommendations,
                'bottleneck_count': len(bottlenecks),
                'critical_issues': len([b for b in bottlenecks if b['severity'] == 'high'])
            }
            
        except Exception as e:
            self.logger.error(f"Error in bottleneck analysis: {e}")
            return {}
    
    def get_time_series_data(self, metric: str, days: int = 90) -> List[Dict]:
        """Get time series data for various metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Generate daily data points
            time_series = []
            current_date = start_date
            
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                
                if metric == 'new_listings':
                    value = Produce.query.filter(
                        Produce.date_listed >= current_date,
                        Produce.date_listed < next_date
                    ).count()
                elif metric == 'new_users':
                    value = User.query.filter(
                        User.registration_date >= current_date,
                        User.registration_date < next_date
                    ).count()
                elif metric == 'sms_interactions':
                    value = SMSInteraction.query.filter(
                        SMSInteraction.timestamp >= current_date,
                        SMSInteraction.timestamp < next_date
                    ).count()
                elif metric == 'messages':
                    value = Message.query.filter(
                        Message.timestamp >= current_date,
                        Message.timestamp < next_date
                    ).count()
                else:
                    value = 0
                
                time_series.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'value': value
                })
                
                current_date = next_date
            
            return time_series
            
        except Exception as e:
            self.logger.error(f"Error getting time series data: {e}")
            return []
    
    def export_analytics_csv(self, report_type: str) -> str:
        """Export analytics data as CSV"""
        try:
            output = io.StringIO()
            
            if report_type == 'market_overview':
                data = self.get_market_overview()
                writer = csv.writer(output)
                writer.writerow(['Metric', 'Value'])
                for key, value in data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            writer.writerow([f"{key}_{sub_key}", sub_value])
                    else:
                        writer.writerow([key, value])
            
            elif report_type == 'crop_analytics':
                data = self.get_crop_analytics()
                writer = csv.writer(output)
                writer.writerow(['Crop Name', 'Total Listings', 'Total Value', 'Average Price', 'Unique Farmers', 'Market Share %'])
                for crop in data.get('crop_distribution', []):
                    writer.writerow([
                        crop['crop_name'],
                        crop['total_listings'],
                        crop['total_value'],
                        crop['average_price'],
                        crop['unique_farmers'],
                        crop['market_share']
                    ])
            
            elif report_type == 'geographic':
                data = self.get_geographic_analytics()
                writer = csv.writer(output)
                writer.writerow(['State', 'Farmer Count', 'Produce Count', 'Total Value', 'Avg Value per Farmer'])
                for state in data.get('farmers_by_state', []):
                    writer.writerow([
                        state['state'],
                        state['farmer_count'],
                        state['produce_count'],
                        state['total_value'],
                        state['avg_value_per_farmer']
                    ])
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {e}")
            return ""
    
    def _calculate_growth_rate(self, days: int) -> float:
        """Calculate platform growth rate"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            recent_users = User.query.filter(User.registration_date >= cutoff_date).count()
            total_users = User.query.count()
            
            previous_users = total_users - recent_users
            
            if previous_users > 0:
                growth_rate = (recent_users / previous_users) * 100
                return round(growth_rate, 2)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_price_trends_by_crop(self) -> Dict:
        """Get price trends for top crops over time"""
        try:
            # Get top 5 crops by listing count
            top_crops = db.session.query(Produce.name)\
                .group_by(Produce.name)\
                .order_by(func.count(Produce.id).desc())\
                .limit(5).all()
            
            trends = {}
            for crop in top_crops:
                crop_name = crop.name
                
                # Get monthly average prices for last 6 months
                monthly_prices = db.session.query(
                    extract('month', Produce.date_listed).label('month'),
                    extract('year', Produce.date_listed).label('year'),
                    func.avg(Produce.price).label('avg_price')
                ).filter(
                    Produce.name == crop_name,
                    Produce.date_listed >= datetime.utcnow() - timedelta(days=180)
                ).group_by(
                    extract('year', Produce.date_listed),
                    extract('month', Produce.date_listed)
                ).order_by(
                    extract('year', Produce.date_listed),
                    extract('month', Produce.date_listed)
                ).all()
                
                trends[crop_name] = [
                    {
                        'period': f"{int(price.year)}-{int(price.month):02d}",
                        'average_price': float(price.avg_price)
                    }
                    for price in monthly_prices
                ]
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting price trends: {e}")
            return {}