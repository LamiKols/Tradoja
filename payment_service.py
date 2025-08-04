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
        return f"{prefix}_{timestamp}"

# Initialize payment service
payment_service = PaymentService()