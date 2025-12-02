"""
T2 Wallet Service for handling mobile wallet transactions
Supports credit/debit operations, balance checks, and transaction logging for SMS/USSD users
"""
import os
import logging
from datetime import datetime
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)


class WalletService:
    """T2 Wallet service for rural users who can't access Paystack directly"""
    
    MIN_BALANCE = Decimal('0.00')
    MAX_TRANSACTION = Decimal('500000.00')
    CAPTAIN_BOND_AMOUNT = Decimal('10000.00')
    
    def __init__(self):
        self.t2_api_key = os.environ.get('T2_API_KEY', '')
        self.t2_base_url = os.environ.get('T2_BASE_URL', 'https://api.t2.com.ng')
    
    def generate_transaction_ref(self, prefix='T2'):
        """Generate unique transaction reference"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = uuid.uuid4().hex[:8].upper()
        return f"{prefix}_{timestamp}_{unique_id}"
    
    def get_balance(self, user):
        """Get user's T2 wallet balance"""
        return Decimal(str(user.t2_wallet_balance or 0))
    
    def credit_wallet(self, user, amount, description, reference=None, db_session=None):
        """
        Credit user's T2 wallet
        Returns: (success, message, transaction_ref)
        """
        from models import WalletTransaction
        
        try:
            amount = Decimal(str(amount))
            
            if amount <= 0:
                return False, "Amount must be positive", None
            
            if amount > self.MAX_TRANSACTION:
                return False, f"Amount exceeds maximum of N{self.MAX_TRANSACTION:,.2f}", None
            
            ref = reference or self.generate_transaction_ref('CR')
            
            current_balance = Decimal(str(user.t2_wallet_balance or 0))
            new_balance = current_balance + amount
            
            user.t2_wallet_balance = float(new_balance)
            
            transaction = WalletTransaction(
                user_id=user.id,
                transaction_type='credit',
                amount=float(amount),
                balance_before=float(current_balance),
                balance_after=float(new_balance),
                description=description,
                reference=ref,
                status='completed',
                channel='system'
            )
            
            if db_session:
                db_session.add(transaction)
            
            logger.info(f"Wallet credit: User {user.id} +N{amount:,.2f} (Ref: {ref})")
            return True, f"N{amount:,.2f} credited successfully", ref
            
        except Exception as e:
            logger.error(f"Wallet credit error: {e}")
            return False, f"Credit failed: {str(e)}", None
    
    def debit_wallet(self, user, amount, description, reference=None, db_session=None):
        """
        Debit user's T2 wallet
        Returns: (success, message, transaction_ref)
        """
        from models import WalletTransaction
        
        try:
            amount = Decimal(str(amount))
            
            if amount <= 0:
                return False, "Amount must be positive", None
            
            if amount > self.MAX_TRANSACTION:
                return False, f"Amount exceeds maximum of N{self.MAX_TRANSACTION:,.2f}", None
            
            current_balance = Decimal(str(user.t2_wallet_balance or 0))
            
            if current_balance < amount:
                return False, f"Insufficient balance. You have N{current_balance:,.2f}", None
            
            ref = reference or self.generate_transaction_ref('DR')
            new_balance = current_balance - amount
            
            user.t2_wallet_balance = float(new_balance)
            
            transaction = WalletTransaction(
                user_id=user.id,
                transaction_type='debit',
                amount=float(amount),
                balance_before=float(current_balance),
                balance_after=float(new_balance),
                description=description,
                reference=ref,
                status='completed',
                channel='system'
            )
            
            if db_session:
                db_session.add(transaction)
            
            logger.info(f"Wallet debit: User {user.id} -N{amount:,.2f} (Ref: {ref})")
            return True, f"N{amount:,.2f} debited successfully", ref
            
        except Exception as e:
            logger.error(f"Wallet debit error: {e}")
            return False, f"Debit failed: {str(e)}", None
    
    def transfer(self, from_user, to_user, amount, description, db_session=None):
        """
        Transfer between wallets
        Returns: (success, message, transaction_ref)
        """
        try:
            amount = Decimal(str(amount))
            ref = self.generate_transaction_ref('TRF')
            
            success, msg, _ = self.debit_wallet(
                from_user, amount, 
                f"Transfer to {to_user.name}: {description}",
                f"{ref}_OUT", db_session
            )
            
            if not success:
                return False, msg, None
            
            success, msg, _ = self.credit_wallet(
                to_user, amount,
                f"Transfer from {from_user.name}: {description}",
                f"{ref}_IN", db_session
            )
            
            if not success:
                self.credit_wallet(from_user, amount, "Transfer reversal", f"{ref}_REV", db_session)
                return False, f"Transfer failed: {msg}", None
            
            logger.info(f"Wallet transfer: {from_user.id} -> {to_user.id} N{amount:,.2f}")
            return True, f"N{amount:,.2f} transferred to {to_user.name}", ref
            
        except Exception as e:
            logger.error(f"Wallet transfer error: {e}")
            return False, f"Transfer failed: {str(e)}", None
    
    def hold_escrow(self, user, amount, description, produce_id=None, db_session=None):
        """
        Hold funds in escrow for a transaction
        Returns: (success, message, escrow_ref)
        """
        from models import WalletTransaction, EscrowHold
        
        try:
            amount = Decimal(str(amount))
            ref = self.generate_transaction_ref('ESC')
            
            success, msg, debit_ref = self.debit_wallet(
                user, amount,
                f"Escrow hold: {description}",
                f"{ref}_HOLD", db_session
            )
            
            if not success:
                return False, msg, None
            
            escrow = EscrowHold(
                user_id=user.id,
                amount=float(amount),
                description=description,
                reference=ref,
                produce_id=produce_id,
                status='held',
                hold_date=datetime.utcnow()
            )
            
            if db_session:
                db_session.add(escrow)
            
            logger.info(f"Escrow held: User {user.id} N{amount:,.2f} (Ref: {ref})")
            return True, f"N{amount:,.2f} held in escrow", ref
            
        except Exception as e:
            logger.error(f"Escrow hold error: {e}")
            return False, f"Escrow failed: {str(e)}", None
    
    def release_escrow(self, escrow_ref, to_user, db_session=None):
        """
        Release escrowed funds to recipient
        Returns: (success, message)
        """
        from models import EscrowHold
        
        try:
            escrow = EscrowHold.query.filter_by(reference=escrow_ref, status='held').first()
            
            if not escrow:
                return False, "Escrow not found or already released"
            
            success, msg, _ = self.credit_wallet(
                to_user, escrow.amount,
                f"Escrow release: {escrow.description}",
                f"{escrow_ref}_RELEASE", db_session
            )
            
            if not success:
                return False, msg
            
            escrow.status = 'released'
            escrow.release_date = datetime.utcnow()
            escrow.released_to_id = to_user.id
            
            logger.info(f"Escrow released: {escrow_ref} to User {to_user.id}")
            return True, f"N{escrow.amount:,.2f} released to {to_user.name}"
            
        except Exception as e:
            logger.error(f"Escrow release error: {e}")
            return False, f"Release failed: {str(e)}"
    
    def refund_escrow(self, escrow_ref, db_session=None):
        """
        Refund escrowed funds back to original user
        Returns: (success, message)
        """
        from models import EscrowHold, User
        
        try:
            escrow = EscrowHold.query.filter_by(reference=escrow_ref, status='held').first()
            
            if not escrow:
                return False, "Escrow not found or already processed"
            
            user = User.query.get(escrow.user_id)
            if not user:
                return False, "User not found"
            
            success, msg, _ = self.credit_wallet(
                user, escrow.amount,
                f"Escrow refund: {escrow.description}",
                f"{escrow_ref}_REFUND", db_session
            )
            
            if not success:
                return False, msg
            
            escrow.status = 'refunded'
            escrow.release_date = datetime.utcnow()
            
            logger.info(f"Escrow refunded: {escrow_ref} to User {user.id}")
            return True, f"N{escrow.amount:,.2f} refunded"
            
        except Exception as e:
            logger.error(f"Escrow refund error: {e}")
            return False, f"Refund failed: {str(e)}"
    
    def collect_captain_bond(self, user, db_session=None):
        """
        Collect SabiBuy Captain bond (N10,000)
        Returns: (success, message, bond_ref)
        """
        from models import CaptainBond
        
        try:
            existing = CaptainBond.query.filter_by(
                user_id=user.id, status='active'
            ).first()
            
            if existing:
                return False, "You already have an active bond", None
            
            success, msg, ref = self.debit_wallet(
                user, self.CAPTAIN_BOND_AMOUNT,
                "SabiBuy Captain Bond",
                self.generate_transaction_ref('BOND'), db_session
            )
            
            if not success:
                return False, msg, None
            
            bond = CaptainBond(
                user_id=user.id,
                amount=float(self.CAPTAIN_BOND_AMOUNT),
                reference=ref,
                status='active',
                collected_date=datetime.utcnow()
            )
            
            if db_session:
                db_session.add(bond)
            
            logger.info(f"Captain bond collected: User {user.id} (Ref: {ref})")
            return True, f"Captain bond of N{self.CAPTAIN_BOND_AMOUNT:,.0f} collected", ref
            
        except Exception as e:
            logger.error(f"Captain bond error: {e}")
            return False, f"Bond collection failed: {str(e)}", None
    
    def refund_captain_bond(self, user, db_session=None):
        """
        Refund SabiBuy Captain bond
        Returns: (success, message)
        """
        from models import CaptainBond
        
        try:
            bond = CaptainBond.query.filter_by(
                user_id=user.id, status='active'
            ).first()
            
            if not bond:
                return False, "No active bond found"
            
            success, msg, _ = self.credit_wallet(
                user, bond.amount,
                "SabiBuy Captain Bond Refund",
                f"{bond.reference}_REFUND", db_session
            )
            
            if not success:
                return False, msg
            
            bond.status = 'refunded'
            bond.refunded_date = datetime.utcnow()
            
            logger.info(f"Captain bond refunded: User {user.id}")
            return True, f"Captain bond of N{bond.amount:,.0f} refunded"
            
        except Exception as e:
            logger.error(f"Captain bond refund error: {e}")
            return False, f"Bond refund failed: {str(e)}"
    
    def forfeit_captain_bond(self, user, reason, db_session=None):
        """
        Forfeit Captain bond due to policy violation
        Returns: (success, message)
        """
        from models import CaptainBond
        
        try:
            bond = CaptainBond.query.filter_by(
                user_id=user.id, status='active'
            ).first()
            
            if not bond:
                return False, "No active bond found"
            
            bond.status = 'forfeited'
            bond.forfeit_reason = reason
            bond.refunded_date = datetime.utcnow()
            
            logger.info(f"Captain bond forfeited: User {user.id} - {reason}")
            return True, f"Captain bond forfeited: {reason}"
            
        except Exception as e:
            logger.error(f"Captain bond forfeit error: {e}")
            return False, f"Forfeit failed: {str(e)}"
    
    def get_transaction_history(self, user, limit=10):
        """Get user's recent wallet transactions"""
        from models import WalletTransaction
        
        return WalletTransaction.query.filter_by(
            user_id=user.id
        ).order_by(
            WalletTransaction.created_at.desc()
        ).limit(limit).all()
    
    def format_balance_sms(self, user):
        """Format wallet balance for SMS response"""
        balance = self.get_balance(user)
        return f"Your AgroLink T2 Wallet balance is N{balance:,.2f}"
    
    def format_history_sms(self, user, limit=5):
        """Format transaction history for SMS response"""
        transactions = self.get_transaction_history(user, limit)
        
        if not transactions:
            return "No recent transactions"
        
        lines = ["Recent transactions:"]
        for txn in transactions:
            sign = "+" if txn.transaction_type == 'credit' else "-"
            date = txn.created_at.strftime('%d/%m')
            lines.append(f"{date}: {sign}N{txn.amount:,.0f} ({txn.description[:20]})")
        
        return "\n".join(lines)


wallet_service = WalletService()
