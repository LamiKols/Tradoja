"""
Payment service for handling Paystack transactions, subscriptions, and fee calculations
"""
import os
import requests
from datetime import datetime, timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        self.paystack_secret_key = os.environ.get('PAYSTACK_SECRET_KEY')
        self.paystack_public_key = os.environ.get('PAYSTACK_PUBLIC_KEY')
        
        # Use sandbox for testing
        self.base_url = "https://api.paystack.co"
        
        if not self.paystack_secret_key:
            logger.warning("Paystack secret key not found in environment variables")
    
    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.paystack_secret_key}',
            'Content-Type': 'application/json'
        }
    
    def calculate_platform_fee(self, amount):
        """Calculate 1.5% platform fee"""
        return Decimal(str(amount)) * Decimal('0.015')
    
    def calculate_total_with_fee(self, amount, logistics_fee=0):
        """Calculate total amount including platform fee and logistics fee"""
        base_amount = Decimal(str(amount))
        platform_fee = self.calculate_platform_fee(amount)
        logistics_amount = Decimal(str(logistics_fee))
        
        return {
            'base_amount': float(base_amount),
            'platform_fee': float(platform_fee),
            'logistics_fee': float(logistics_amount),
            'total_amount': float(base_amount + platform_fee + logistics_amount)
        }
    
    def initialize_transaction(self, email, amount, reference, callback_url=None, metadata=None):
        """Initialize a transaction with Paystack"""
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/transaction/initialize"
        
        # Convert amount to kobo (multiply by 100)
        amount_kobo = int(float(amount) * 100)
        
        data = {
            'email': email,
            'amount': amount_kobo,
            'reference': reference,
            'currency': 'NGN'
        }
        
        if callback_url:
            data['callback_url'] = callback_url
        
        if metadata:
            data['metadata'] = metadata
        
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to initialize transaction: {e}")
            raise Exception(f"Payment initialization failed: {str(e)}")
    
    def verify_transaction(self, reference):
        """Verify a transaction with Paystack"""
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to verify transaction: {e}")
            raise Exception(f"Transaction verification failed: {str(e)}")
    
    def create_subscription_plan(self, name, amount, interval='monthly'):
        """Create a subscription plan"""
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/plan"
        
        # Convert amount to kobo
        amount_kobo = int(float(amount) * 100)
        
        data = {
            'name': name,
            'amount': amount_kobo,
            'interval': interval,
            'currency': 'NGN'
        }
        
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create subscription plan: {e}")
            raise Exception(f"Subscription plan creation failed: {str(e)}")
    
    def initialize_subscription(self, email, plan_code, reference):
        """Initialize a subscription"""
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/transaction/initialize"
        
        data = {
            'email': email,
            'plan': plan_code,
            'reference': reference
        }
        
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to initialize subscription: {e}")
            raise Exception(f"Subscription initialization failed: {str(e)}")
    
    def generate_reference(self, prefix="agrolink"):
        """Generate a unique transaction reference"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        import uuid
        unique_id = uuid.uuid4().hex[:6]
        return f"{prefix}_{timestamp}_{unique_id}"
    
    def charge_ussd(self, email, amount, reference, bank_code, account_number=None):
        """
        Charge via Paystack USSD - generates a USSD code for rural users to dial
        Supported banks: GTB (058), UBA (033), Zenith (057), First Bank (011), etc.
        Returns: USSD code string that user dials to complete payment
        """
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/charge"
        
        amount_kobo = int(float(amount) * 100)
        
        data = {
            'email': email,
            'amount': amount_kobo,
            'reference': reference,
            'ussd': {
                'type': bank_code
            }
        }
        
        if account_number:
            data['ussd']['account_number'] = account_number
        
        try:
            response = requests.post(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') and result.get('data', {}).get('ussd_code'):
                return {
                    'success': True,
                    'ussd_code': result['data']['ussd_code'],
                    'reference': reference,
                    'display_text': result['data'].get('display_text', ''),
                    'message': f"Dial {result['data']['ussd_code']} to complete payment"
                }
            else:
                return {
                    'success': False,
                    'message': result.get('message', 'USSD charge failed')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"USSD charge failed: {e}")
            return {
                'success': False,
                'message': f"USSD charge failed: {str(e)}"
            }
    
    def get_bank_ussd_codes(self):
        """Get supported bank USSD codes for Paystack"""
        return {
            '058': {'name': 'GTBank', 'code': '*737#'},
            '033': {'name': 'UBA', 'code': '*919#'},
            '057': {'name': 'Zenith Bank', 'code': '*966#'},
            '011': {'name': 'First Bank', 'code': '*894#'},
            '044': {'name': 'Access Bank', 'code': '*901#'},
            '050': {'name': 'Ecobank', 'code': '*326#'},
            '070': {'name': 'Fidelity Bank', 'code': '*770#'},
            '032': {'name': 'Union Bank', 'code': '*826#'},
            '039': {'name': 'Stanbic IBTC', 'code': '*909#'},
            '214': {'name': 'FCMB', 'code': '*329#'},
            '035': {'name': 'Wema Bank', 'code': '*945#'},
            '232': {'name': 'Sterling Bank', 'code': '*822#'},
            '082': {'name': 'Keystone Bank', 'code': '*7111#'},
            '076': {'name': 'Polaris Bank', 'code': '*833#'},
            '221': {'name': 'Heritage Bank', 'code': '*322#'},
            '215': {'name': 'Unity Bank', 'code': '*7799#'},
        }
    
    def format_bank_list_sms(self):
        """Format bank list for SMS response"""
        banks = self.get_bank_ussd_codes()
        lines = ["Banks for USSD payment:"]
        for code, info in list(banks.items())[:8]:
            lines.append(f"{info['name']}: Reply {code}")
        return "\n".join(lines)
    
    def check_charge_status(self, reference):
        """Check the status of a USSD charge"""
        if not self.paystack_secret_key:
            raise Exception("Paystack credentials not configured")
        
        url = f"{self.base_url}/charge/{reference}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            result = response.json()
            
            if result.get('status'):
                data = result.get('data', {})
                return {
                    'success': True,
                    'status': data.get('status'),
                    'gateway_response': data.get('gateway_response'),
                    'reference': reference,
                    'amount': data.get('amount', 0) / 100
                }
            return {'success': False, 'message': 'Charge not found'}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Charge status check failed: {e}")
            return {'success': False, 'message': str(e)}
    
    def calculate_tiered_fee(self, amount, user_type='farmer'):
        """
        Calculate tiered transaction fees based on user type
        Farmer-direct: 2%, Verified trader: 3.5%, Unverified trader: 5%
        """
        fee_rates = {
            'farmer': Decimal('0.02'),
            'verified_trader': Decimal('0.035'),
            'unverified_trader': Decimal('0.05'),
            'buyer': Decimal('0.02')
        }
        
        rate = fee_rates.get(user_type, Decimal('0.02'))
        base_amount = Decimal(str(amount))
        platform_fee = base_amount * rate
        
        return {
            'base_amount': float(base_amount),
            'platform_fee': float(platform_fee),
            'fee_rate': float(rate * 100),
            'total_amount': float(base_amount + platform_fee)
        }

# Initialize payment service
payment_service = PaymentService()