"""
§7.1 Idempotency tests — duplicate webhook delivery must not create a second LedgerEntry.

Uses an in-memory SQLite database spun up before any app import.

Run: python -m pytest tests/test_ledger_idempotency.py -v
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# ── Must happen BEFORE any project import ────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Stub modules that would fail without real credentials
sys.modules['openai'] = MagicMock()
_openai = sys.modules['openai']
_openai.OpenAI.return_value = MagicMock()

sys.modules['africastalking'] = MagicMock()

# ── Now import app (which calls db.init_app + db.create_all) ─────────────────
from app import app as flask_app, db

# Ensure all tables (including LedgerEntry) are created
with flask_app.app_context():
    db.create_all()


# ─────────────────────────────────────────────────────────────────────────────

def _clear_tables():
    from models import User, LedgerEntry
    db.session.query(LedgerEntry).delete()
    db.session.query(User).delete()
    db.session.commit()


def _make_farmer(phone, email, whatsapp_id=None):
    from models import User
    user = User(
        name='Test Farmer',
        email=email,
        password_hash='x',
        role='farmer',
        phone_number=phone,
        whatsapp_id=whatsapp_id or phone,
        registration_status='lite',
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestSMSIdempotency(unittest.TestCase):
    """Duplicate Africa's Talking webhook (same `id`) → only one LedgerEntry."""

    def setUp(self):
        with flask_app.app_context():
            _clear_tables()
            user = _make_farmer('+2348011111111', 'sms@sms.tradoja.com')
            self.farmer_id = user.id

    def _send_sms(self, message, message_id):
        with flask_app.app_context():
            from sms_service import SMSService
            svc = SMSService.__new__(SMSService)
            svc._simulation_mode = True
            svc._current_metadata = {}
            svc._ledger_rate = {}

            metadata = {
                'message_id': message_id or '',
                'channel': 'sms',
                'gateway_ip': '127.0.0.1',
                'user_agent': '',
                'link_id': '',
                'network_code': '',
                'date': '',
            }
            with patch.object(svc, 'send_sms', return_value='ok'), \
                 patch.object(svc, '_log_sms_interaction'):
                return svc.process_incoming_sms(
                    '+2348011111111', message, metadata=metadata
                )

    def test_duplicate_sms_creates_only_one_entry(self):
        at_id = 'ATmsg-idp-001'
        self._send_sms('LOG SALE RICE 5BAGS 45000', at_id)
        self._send_sms('LOG SALE RICE 5BAGS 45000', at_id)   # exact duplicate

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(
                farmer_id=self.farmer_id,
                gateway_message_id=at_id,
            ).count()
            self.assertEqual(count, 1,
                f"Expected 1 entry for AT id '{at_id}', found {count}")

    def test_different_at_ids_create_two_entries(self):
        self._send_sms('LOG SALE RICE 5BAGS 45000', 'ATmsg-001')
        self._send_sms('LOG SALE MAIZE 3BAGS 30000', 'ATmsg-002')

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(farmer_id=self.farmer_id).count()
            self.assertEqual(count, 2,
                f"Expected 2 distinct entries, found {count}")

    def test_no_at_id_still_creates_entry(self):
        """Empty/missing gateway id (manual entry) is always inserted."""
        self._send_sms('LOG SALE YAMS 10BAGS 60000', '')

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(farmer_id=self.farmer_id).count()
            self.assertEqual(count, 1)


class TestWhatsAppIdempotency(unittest.TestCase):
    """Duplicate Twilio webhook (same MessageSid) → only one LedgerEntry."""

    def setUp(self):
        with flask_app.app_context():
            _clear_tables()
            user = _make_farmer('+2348022222222', 'wa@wa.tradoja.com',
                                whatsapp_id='+2348022222222')
            self.farmer_id = user.id

    def _send_wa(self, message, message_sid):
        with flask_app.app_context():
            from whatsapp_service import WhatsAppService
            svc = WhatsAppService.__new__(WhatsAppService)
            svc._sessions = {}
            svc._simulation_mode = True
            svc._ledger_rate = {}
            svc._current_gateway_message_id = None

            with patch.object(svc, 'send_message', return_value='ok'), \
                 patch.object(svc, '_log_interaction'):
                return svc.process_incoming(
                    '+2348022222222', message,
                    media_url=None,
                    gateway_message_id=message_sid or None,
                )

    def test_duplicate_whatsapp_creates_only_one_entry(self):
        sid = 'SM-dup-twilio-001'
        self._send_wa('LOG SALE TOMATOES 10KG 8000', sid)
        self._send_wa('LOG SALE TOMATOES 10KG 8000', sid)    # duplicate

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(
                farmer_id=self.farmer_id,
                gateway_message_id=sid,
            ).count()
            self.assertEqual(count, 1,
                f"Expected 1 entry for MessageSid '{sid}', found {count}")

    def test_different_sids_create_two_entries(self):
        self._send_wa('LOG SALE GARRI 5BAGS 20000', 'SM-wa-001')
        self._send_wa('LOG BUY SEED 1BAG 5000', 'SM-wa-002')

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(farmer_id=self.farmer_id).count()
            self.assertEqual(count, 2,
                f"Expected 2 distinct entries, found {count}")

    def test_no_sid_still_creates_entry(self):
        """WhatsApp messages without a SID (simulator) are inserted normally."""
        self._send_wa('LOG STOCK MAIZE 20BAGS', None)

        with flask_app.app_context():
            from models import LedgerEntry
            count = LedgerEntry.query.filter_by(farmer_id=self.farmer_id).count()
            self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
