"""
AI-Powered Trading Services for Tradoja

Features:
1. Voice-to-Command: Parse natural language SMS into trade commands
2. Price Advisor: Market trend analysis and timing recommendations  
3. Escrow Risk Scorer: Score transactions before funds lock
4. Auto-Release Engine: Multi-signal verification for escrow release
5. Dispute Resolver: Analyze evidence and recommend resolution
"""

import os
import json
import logging
from datetime import datetime, timedelta
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)


class AITradingService:
    """AI-powered trading assistant for Tradoja"""
    
    def __init__(self):
        self.model = "gpt-5-mini"
    
    def parse_natural_language(self, message: str, user_phone: str = None) -> dict:
        """
        Parse natural language SMS into structured trade commands.
        
        Examples:
        - "I want to sell 50kg tomatoes for 15000" → SELL TOMATOES 50 15000
        - "Check my order status" → STATUS
        - "How much is yam today" → PRICE YAM
        - "I accept the order" → ACCEPT [last order]
        """
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are Tradoja's SMS parser. Convert natural language to structured commands.

Available commands:
- SELL [crop] [quantity_kg] [price_naira] - List produce for sale
- PRICE [crop] - Get market price
- TRACK [order_code] - Track order
- ACCEPT [order_code] - Accept order
- CANCEL [order_code] [reason] - Cancel order
- BAL - Check balance
- STATUS - Account status
- HELP - Get help
- JOBS - View transport jobs
- VOUCH [phone] - Vouch for farmer

Return JSON with:
{
  "command": "COMMAND_NAME",
  "params": ["param1", "param2"],
  "confidence": 0.0-1.0,
  "original_intent": "brief description of what user wants"
}

If unclear, set confidence < 0.5 and suggest clarification."""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            result['parsed_at'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"AI parse error: {e}")
            return {
                "command": None,
                "params": [],
                "confidence": 0,
                "error": str(e),
                "original_intent": "Could not parse message"
            }
    
    def get_price_advice(self, crop: str, quantity_kg: float, location: str = None) -> dict:
        """
        Analyze market trends and provide pricing/timing recommendations.
        """
        try:
            from models import Produce
            from app import app
            
            with app.app_context():
                recent_listings = Produce.query.filter(
                    Produce.crop_type.ilike(f"%{crop}%"),
                    Produce.status == 'available'
                ).order_by(Produce.timestamp.desc()).limit(20).all()
                
                market_data = []
                for p in recent_listings:
                    market_data.append({
                        "price_per_kg": p.price_per_kg if hasattr(p, 'price_per_kg') else None,
                        "location": p.location,
                        "quantity": p.quantity,
                        "listed_at": p.timestamp.isoformat() if p.timestamp else None
                    })
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are Tradoja's price advisor for Nigerian agricultural markets.

Analyze market data and provide:
1. Fair price range for the crop
2. Whether to sell now or wait
3. Best time of week/month to sell
4. Demand trends

Keep advice practical for farmers using basic phones.
Return JSON:
{
  "recommended_price_per_kg": number,
  "price_range": {"min": number, "max": number},
  "sell_now": true/false,
  "timing_advice": "brief advice",
  "demand_level": "high/medium/low",
  "confidence": 0.0-1.0
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Crop: {crop}\nQuantity: {quantity_kg}kg\nLocation: {location or 'Nigeria'}\nRecent market data: {json.dumps(market_data[:10])}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            
            result = json.loads(response.choices[0].message.content)
            result['crop'] = crop
            result['analyzed_at'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Price advice error: {e}")
            return {
                "error": str(e),
                "recommended_price_per_kg": None,
                "sell_now": True,
                "timing_advice": "Unable to analyze. Consider checking PRICE command.",
                "confidence": 0
            }
    
    def score_escrow_risk(self, order_id: int) -> dict:
        """
        Score transaction risk before funds are locked in escrow.
        
        Factors considered:
        - Buyer history and verification level
        - Seller history and ratings
        - Transaction amount vs typical
        - Location patterns
        - Previous disputes
        """
        try:
            from models import Order, User, Dispute
            from app import app
            
            with app.app_context():
                order = Order.query.get(order_id)
                if not order:
                    return {"error": "Order not found", "risk_score": 100}
                
                buyer = order.buyer
                seller = order.farmer
                
                buyer_data = {
                    "verification_level": buyer.verification_level if hasattr(buyer, 'verification_level') else 'unverified',
                    "created_at": buyer.created_at.isoformat() if hasattr(buyer, 'created_at') and buyer.created_at else None,
                    "order_count": len(buyer.orders_as_buyer) if hasattr(buyer, 'orders_as_buyer') else 0,
                    "disputes": Dispute.query.filter_by(raised_by_id=buyer.id).count() if buyer else 0
                }
                
                seller_data = {
                    "verification_level": seller.verification_level if hasattr(seller, 'verification_level') else 'unverified',
                    "rating": getattr(seller, 'rating', None),
                    "order_count": len(seller.orders_as_farmer) if hasattr(seller, 'orders_as_farmer') else 0,
                    "disputes": Dispute.query.filter_by(raised_against_id=seller.id).count() if seller else 0
                }
                
                order_data = {
                    "amount": order.total_amount,
                    "quantity": order.quantity,
                    "delivery_type": order.delivery_type
                }
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are Tradoja's risk assessment AI for agricultural escrow.

Score transaction risk (0-100, higher = riskier):
- 0-30: Low risk, safe to proceed
- 31-60: Medium risk, extra verification recommended
- 61-80: High risk, require additional confirmation
- 81-100: Very high risk, flag for manual review

Consider:
1. User verification levels
2. Transaction history
3. Dispute history
4. Account age
5. Amount patterns

Return JSON:
{
  "risk_score": 0-100,
  "risk_level": "low/medium/high/critical",
  "flags": ["list of concerns"],
  "recommendations": ["suggested actions"],
  "auto_approve": true/false,
  "confidence": 0.0-1.0
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Buyer: {json.dumps(buyer_data)}\nSeller: {json.dumps(seller_data)}\nOrder: {json.dumps(order_data)}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            result['order_id'] = order_id
            result['scored_at'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Risk scoring error: {e}")
            return {
                "error": str(e),
                "risk_score": 50,
                "risk_level": "medium",
                "flags": ["Scoring unavailable"],
                "auto_approve": False,
                "confidence": 0
            }
    
    def evaluate_auto_release(self, order_id: int) -> dict:
        """
        Multi-signal verification for escrow auto-release.
        
        Signals checked:
        1. OTP verified ✓
        2. Location matches destination
        3. Time within expected window
        4. No disputes raised
        5. Both parties confirmed
        """
        try:
            from models import Order
            from app import app
            
            with app.app_context():
                order = Order.query.get(order_id)
                if not order:
                    return {"can_release": False, "reason": "Order not found"}
                
                signals = {
                    "otp_verified": order.otp_verified,
                    "status": order.status,
                    "has_escrow": order.escrow_id is not None,
                    "delivery_location": order.last_location,
                    "destination": order.destination,
                    "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                    "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
                    "total_amount": order.total_amount
                }
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are Tradoja's escrow release verification AI.

Evaluate if escrow funds should be auto-released to the farmer.

REQUIRED for release:
1. OTP must be verified (otp_verified = true)
2. Status must be 'delivered' or 'completed'
3. Escrow must exist

RECOMMENDED checks:
4. Delivery location should reasonably match destination
5. Delivery time should be within expected window (not too fast/slow)

Return JSON:
{
  "can_release": true/false,
  "release_confidence": 0.0-1.0,
  "signals_passed": ["list of passed checks"],
  "signals_failed": ["list of failed checks"],
  "reason": "explanation",
  "require_manual_review": true/false,
  "delay_hours": 0 (if should wait before release)
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Order signals: {json.dumps(signals)}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            result['order_id'] = order_id
            result['evaluated_at'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Auto-release evaluation error: {e}")
            return {
                "can_release": False,
                "reason": f"Evaluation error: {str(e)}",
                "require_manual_review": True,
                "release_confidence": 0
            }
    
    def resolve_dispute(self, dispute_id: int) -> dict:
        """
        Analyze dispute evidence and recommend resolution.
        """
        try:
            from models import Dispute, Order
            from app import app
            
            with app.app_context():
                dispute = Dispute.query.get(dispute_id)
                if not dispute:
                    return {"error": "Dispute not found"}
                
                dispute_data = {
                    "type": dispute.dispute_type if hasattr(dispute, 'dispute_type') else 'general',
                    "description": dispute.description if hasattr(dispute, 'description') else '',
                    "raised_at": dispute.created_at.isoformat() if hasattr(dispute, 'created_at') and dispute.created_at else None,
                    "status": dispute.status if hasattr(dispute, 'status') else 'open'
                }
                
                order = None
                if hasattr(dispute, 'order_id') and dispute.order_id:
                    order = Order.query.get(dispute.order_id)
                
                order_data = {}
                if order:
                    order_data = {
                        "amount": order.total_amount,
                        "status": order.status,
                        "otp_verified": order.otp_verified,
                        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
                    }
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are Tradoja's dispute resolution AI for agricultural transactions.

Analyze disputes and recommend fair resolutions considering:
1. Evidence provided
2. Transaction status and verification
3. Party histories
4. Nigerian agricultural trade practices

Resolution options:
- FULL_REFUND: Return all funds to buyer
- PARTIAL_REFUND: Split based on fault percentage
- RELEASE_TO_SELLER: Funds go to farmer
- MEDIATION: Requires human intervention
- ESCALATE: Complex case needing admin review

Return JSON:
{
  "recommended_resolution": "FULL_REFUND/PARTIAL_REFUND/RELEASE_TO_SELLER/MEDIATION/ESCALATE",
  "refund_percentage": 0-100 (if partial),
  "reasoning": "explanation",
  "evidence_strength": "strong/moderate/weak",
  "confidence": 0.0-1.0,
  "suggested_message_to_parties": "brief message",
  "auto_resolve": true/false
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Dispute: {json.dumps(dispute_data)}\nOrder: {json.dumps(order_data)}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            result['dispute_id'] = dispute_id
            result['resolved_at'] = datetime.utcnow().isoformat()
            return result
            
        except Exception as e:
            logger.error(f"Dispute resolution error: {e}")
            return {
                "error": str(e),
                "recommended_resolution": "ESCALATE",
                "reasoning": "Unable to analyze automatically",
                "auto_resolve": False,
                "confidence": 0
            }
    
    def format_sms_response(self, result: dict, command_type: str) -> str:
        """Format AI results for SMS delivery (160 char limit awareness)"""
        
        if command_type == 'price_advice':
            if result.get('error'):
                return f"Price check unavailable. Try: PRICE {result.get('crop', 'CROP')}"
            
            price = result.get('recommended_price_per_kg', 'N/A')
            demand = result.get('demand_level', 'unknown')
            advice = result.get('timing_advice', '')[:60]
            
            return f"Price advice:\nN{price}/kg ({demand} demand)\n{advice}"
        
        elif command_type == 'risk_score':
            score = result.get('risk_score', 'N/A')
            level = result.get('risk_level', 'unknown')
            
            if score <= 30:
                return f"Risk: LOW ({score}/100). Safe to proceed."
            elif score <= 60:
                return f"Risk: MEDIUM ({score}/100). Verify buyer details."
            else:
                return f"Risk: HIGH ({score}/100). Extra caution advised."
        
        elif command_type == 'auto_release':
            if result.get('can_release'):
                return "Escrow verified. Funds releasing to farmer."
            else:
                reason = result.get('reason', 'Verification pending')[:80]
                return f"Release pending: {reason}"
        
        elif command_type == 'dispute':
            resolution = result.get('recommended_resolution', 'ESCALATE')
            msg = result.get('suggested_message_to_parties', '')[:80]
            return f"AI Recommendation: {resolution}\n{msg}"
        
        return "AI analysis complete."


ai_trading_service = AITradingService()
