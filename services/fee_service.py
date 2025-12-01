"""
Transaction Fee Service for AgroLink
Implements tiered fees: lower for farmer-direct, higher for trader transactions
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FeeService:
    """
    Tiered transaction fee system
    
    Fee Structure:
    - Farmer-to-Consumer: 2% (lowest - encourages direct buying)
    - Farmer-to-Verified-Trader: 3.5% (value-adding traders)
    - Farmer-to-Unverified-Trader: 5% (discourages pure resellers)
    - Trader-to-Consumer: 4% (resale markup)
    - SabiBuy: 2% of GMV (group buying benefits)
    - Logistics: ₦500 flat + 1% of goods value
    """
    
    FEE_TIERS = {
        'farmer_to_consumer': {
            'name': 'Farmer Direct',
            'rate': 0.02,
            'description': 'Buy directly from farmers at the lowest fee',
            'cap': 10000
        },
        'farmer_to_verified_trader': {
            'name': 'Verified Trader',
            'rate': 0.035,
            'description': 'Value-adding traders with verification',
            'cap': 25000
        },
        'farmer_to_unverified_trader': {
            'name': 'Standard Trader',
            'rate': 0.05,
            'description': 'Unverified trader purchases',
            'cap': 50000
        },
        'trader_to_consumer': {
            'name': 'Trader Resale',
            'rate': 0.04,
            'description': 'Buying from trader listings',
            'cap': 30000
        },
        'sabibuy': {
            'name': 'SabiBuy Group Buy',
            'rate': 0.02,
            'description': 'Group buying commission',
            'cap': 15000
        },
        'logistics_base': {
            'name': 'Logistics Base Fee',
            'flat_fee': 500,
            'rate': 0.01,
            'description': 'Transport booking fee',
            'cap': 5000
        }
    }
    
    PAYMENT_GATEWAY_FEE = 0.015
    PAYMENT_GATEWAY_FLAT = 100
    PAYMENT_GATEWAY_CAP = 2000
    
    def __init__(self):
        self.db = None
        self.User = None
        self.Produce = None
    
    def _lazy_load_models(self):
        """Lazy load database models"""
        if self.db is None:
            from app import db
            from models import User, Produce
            self.db = db
            self.User = User
            self.Produce = Produce
    
    def calculate_transaction_fee(
        self,
        seller_id: int,
        buyer_id: int,
        transaction_amount: float,
        is_sabibuy: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate appropriate fee for a transaction
        
        Returns:
            dict with fee breakdown:
            - tier: fee tier applied
            - platform_fee: our commission
            - payment_fee: payment gateway fee
            - total_fee: total deducted
            - seller_receives: amount after fees
        """
        self._lazy_load_models()
        
        try:
            if is_sabibuy:
                tier = 'sabibuy'
            else:
                seller = self.User.query.get(seller_id)
                buyer = self.User.query.get(buyer_id)
                
                if not seller or not buyer:
                    return {'success': False, 'error': 'Invalid users'}
                
                tier = self._determine_fee_tier(seller, buyer)
            
            tier_config = self.FEE_TIERS[tier]
            
            if 'flat_fee' in tier_config:
                platform_fee = tier_config['flat_fee'] + (transaction_amount * tier_config['rate'])
            else:
                platform_fee = transaction_amount * tier_config['rate']
            
            if tier_config.get('cap'):
                platform_fee = min(platform_fee, tier_config['cap'])
            
            payment_fee = min(
                (transaction_amount * self.PAYMENT_GATEWAY_FEE) + self.PAYMENT_GATEWAY_FLAT,
                self.PAYMENT_GATEWAY_CAP
            )
            
            total_fee = platform_fee + payment_fee
            seller_receives = transaction_amount - total_fee
            
            return {
                'success': True,
                'tier': tier,
                'tier_name': tier_config['name'],
                'tier_rate': tier_config['rate'],
                'transaction_amount': transaction_amount,
                'platform_fee': round(platform_fee, 2),
                'payment_fee': round(payment_fee, 2),
                'total_fee': round(total_fee, 2),
                'seller_receives': round(seller_receives, 2),
                'fee_percentage': round((total_fee / transaction_amount) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating fee: {e}")
            return {'success': False, 'error': str(e)}
    
    def _determine_fee_tier(self, seller, buyer) -> str:
        """Determine which fee tier applies based on seller and buyer types"""
        seller_is_farmer = seller.role == 'farmer'
        buyer_is_consumer = buyer.role == 'buyer' and buyer.buyer_type == 'consumer'
        buyer_is_verified_trader = (
            buyer.role == 'buyer' and 
            buyer.buyer_type == 'bulk_trader' and 
            buyer.trader_verified
        )
        buyer_is_unverified_trader = (
            buyer.role == 'buyer' and 
            buyer.buyer_type == 'bulk_trader' and 
            not buyer.trader_verified
        )
        
        if seller_is_farmer:
            if buyer_is_consumer:
                return 'farmer_to_consumer'
            elif buyer_is_verified_trader:
                return 'farmer_to_verified_trader'
            elif buyer_is_unverified_trader:
                return 'farmer_to_unverified_trader'
        
        return 'trader_to_consumer'
    
    def calculate_logistics_fee(
        self,
        goods_value: float,
        distance_km: Optional[float] = None,
        requires_cold_chain: bool = False
    ) -> Dict[str, Any]:
        """Calculate logistics booking fee"""
        try:
            base_config = self.FEE_TIERS['logistics_base']
            
            base_fee = base_config['flat_fee'] + (goods_value * base_config['rate'])
            
            distance_fee = 0
            if distance_km:
                distance_fee = distance_km * 50
            
            cold_chain_fee = 0
            if requires_cold_chain:
                cold_chain_fee = goods_value * 0.005
            
            total_fee = min(base_fee + distance_fee + cold_chain_fee, base_config['cap'] * 2)
            
            return {
                'success': True,
                'base_fee': round(base_fee, 2),
                'distance_fee': round(distance_fee, 2),
                'cold_chain_fee': round(cold_chain_fee, 2),
                'total_fee': round(total_fee, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating logistics fee: {e}")
            return {'success': False, 'error': str(e)}
    
    def calculate_sabibuy_fees(
        self,
        gmv: float,
        organizer_margin: float,
        batch_quantity: int
    ) -> Dict[str, Any]:
        """Calculate SabiBuy campaign fees"""
        try:
            tier_config = self.FEE_TIERS['sabibuy']
            
            platform_fee = min(gmv * tier_config['rate'], tier_config['cap'])
            
            payment_fees = min(
                (gmv * self.PAYMENT_GATEWAY_FEE) + self.PAYMENT_GATEWAY_FLAT,
                self.PAYMENT_GATEWAY_CAP
            )
            
            organizer_profit = organizer_margin * batch_quantity
            
            net_organizer_profit = organizer_profit - platform_fee
            
            return {
                'success': True,
                'gmv': round(gmv, 2),
                'platform_fee': round(platform_fee, 2),
                'payment_fees': round(payment_fees, 2),
                'gross_organizer_profit': round(organizer_profit, 2),
                'net_organizer_profit': round(net_organizer_profit, 2),
                'platform_take_rate': round((platform_fee / gmv) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating SabiBuy fees: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_fee_comparison(self, amount: float) -> Dict[str, Any]:
        """Get comparison of fees across all tiers for transparency"""
        comparisons = []
        
        for tier_key, tier_config in self.FEE_TIERS.items():
            if tier_key == 'logistics_base':
                continue
            
            if 'flat_fee' in tier_config:
                fee = tier_config['flat_fee'] + (amount * tier_config['rate'])
            else:
                fee = amount * tier_config['rate']
            
            if tier_config.get('cap'):
                fee = min(fee, tier_config['cap'])
            
            comparisons.append({
                'tier': tier_key,
                'name': tier_config['name'],
                'description': tier_config['description'],
                'fee': round(fee, 2),
                'percentage': tier_config['rate'] * 100,
                'seller_receives': round(amount - fee, 2)
            })
        
        comparisons.sort(key=lambda x: x['fee'])
        
        return {
            'transaction_amount': amount,
            'comparisons': comparisons,
            'recommendation': 'Buy directly from farmers for the lowest fees!'
        }
    
    def get_revenue_stats(self) -> Dict[str, Any]:
        """Get fee revenue statistics for admin dashboard"""
        return {
            'note': 'Revenue tracking requires transaction records integration',
            'fee_tiers': list(self.FEE_TIERS.keys()),
            'payment_gateway_rate': self.PAYMENT_GATEWAY_FEE
        }


fee_service = FeeService()
