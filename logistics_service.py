"""
Logistics Service for AgroLink
Handles transporter matching, cold chain verification, and logistics notifications
"""
import os
import json
import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Nigerian states with approximate coordinates for distance calculation
NIGERIAN_STATES_COORDS = {
    'lagos': (6.5244, 3.3792),
    'oyo': (7.8500, 3.9333),
    'ogun': (7.1607, 3.3500),
    'osun': (7.5629, 4.5200),
    'ondo': (7.2500, 5.1931),
    'ekiti': (7.6209, 5.2194),
    'kwara': (8.4799, 4.5418),
    'kogi': (7.7337, 6.6906),
    'edo': (6.3350, 5.6037),
    'delta': (5.8904, 5.6803),
    'rivers': (4.8396, 6.9112),
    'bayelsa': (4.9057, 6.0699),
    'akwa ibom': (5.0079, 7.8494),
    'cross river': (5.8702, 8.5988),
    'abia': (5.4527, 7.5248),
    'imo': (5.4833, 7.0333),
    'anambra': (6.2104, 7.0694),
    'enugu': (6.4584, 7.5464),
    'ebonyi': (6.2649, 8.0137),
    'benue': (7.3369, 8.7404),
    'plateau': (9.2182, 9.5176),
    'nasarawa': (8.5179, 8.5776),
    'taraba': (7.8704, 9.7804),
    'adamawa': (9.3265, 12.3984),
    'gombe': (10.2897, 11.1711),
    'bauchi': (10.3158, 9.8442),
    'borno': (11.8333, 13.1500),
    'yobe': (12.0000, 11.5000),
    'jigawa': (12.2280, 9.5616),
    'kano': (12.0022, 8.5920),
    'kaduna': (10.5105, 7.4165),
    'katsina': (12.9908, 7.6006),
    'zamfara': (12.1704, 6.6600),
    'sokoto': (13.0622, 5.2339),
    'kebbi': (12.4500, 4.1997),
    'niger': (10.4000, 5.4667),
    'fct': (9.0765, 7.3986),  # Abuja
    'abuja': (9.0765, 7.3986),
    'onitsha': (6.1667, 6.7833),  # Major trading hub
}


def calculate_distance(from_state, to_state):
    """
    Calculate approximate distance between two Nigerian states in km
    Uses Haversine formula
    """
    from_state_lower = from_state.lower().strip()
    to_state_lower = to_state.lower().strip()
    
    if from_state_lower not in NIGERIAN_STATES_COORDS:
        logger.warning(f"Unknown state: {from_state}")
        return 500  # Default distance if state unknown
    
    if to_state_lower not in NIGERIAN_STATES_COORDS:
        logger.warning(f"Unknown state: {to_state}")
        return 500
    
    lat1, lon1 = NIGERIAN_STATES_COORDS[from_state_lower]
    lat2, lon2 = NIGERIAN_STATES_COORDS[to_state_lower]
    
    # Haversine formula
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


class LogisticsService:
    """Service for managing logistics, transport matching, and cold chain"""
    
    def __init__(self):
        self.max_matching_distance_km = 200
        
    def find_matching_transporters(self, logistics_request, limit=10):
        """
        Find transporters matching a logistics request
        Scores based on: distance, price, rating, cold chain match, on-time %
        """
        from models import TransportProfile, ColdChainDevice
        from app import db
        
        matching_transporters = []
        
        # Get all verified transporters (or all if few are verified)
        all_transporters = TransportProfile.query.filter_by(is_verified=True).all()
        if len(all_transporters) < 3:
            all_transporters = TransportProfile.query.all()
        
        for transporter in all_transporters:
            score = self._calculate_transporter_score(transporter, logistics_request)
            if score > 0:
                matching_transporters.append({
                    'transporter': transporter,
                    'score': score,
                    'estimated_price': self._estimate_price(transporter, logistics_request),
                    'has_cold_chain': transporter.cold_chain_capable
                })
        
        # Sort by score (highest first)
        matching_transporters.sort(key=lambda x: x['score'], reverse=True)
        
        return matching_transporters[:limit]
    
    def _calculate_transporter_score(self, transporter, logistics_request):
        """
        Calculate matching score for a transporter (0-100)
        Weights:
        - Route coverage: 25 points
        - Cold chain match: 25 points (critical - 0 if required but not available)
        - Rating: 20 points
        - On-time %: 15 points
        - Price competitiveness: 15 points
        """
        score = 0
        
        # Cold chain check (critical)
        if logistics_request.requires_cold_chain:
            if not transporter.cold_chain_capable:
                return 0  # Disqualify if cold chain required but not available
            
            # Check for active cold chain device
            from models import ColdChainDevice
            has_active_device = ColdChainDevice.query.filter_by(
                transporter_id=transporter.id,
                is_active=True
            ).first()
            
            if not has_active_device:
                return 0  # Disqualify without active device
            
            score += 25  # Cold chain bonus
        else:
            score += 15  # Partial score for non-cold chain
        
        # Route coverage check
        pickup_state = logistics_request.pickup_state or ''
        dest_state = logistics_request.destination_state or ''
        
        if pickup_state and dest_state:
            if transporter.covers_route(pickup_state, dest_state):
                score += 25
            else:
                # Check if transporter is near the pickup location
                routes = transporter.get_routes_covered_list()
                min_distance = float('inf')
                for route in routes:
                    if len(route) >= 2:
                        dist = calculate_distance(route[0], pickup_state)
                        min_distance = min(min_distance, dist)
                
                if min_distance <= self.max_matching_distance_km:
                    score += 15  # Partial score for nearby transporter
                elif min_distance <= self.max_matching_distance_km * 2:
                    score += 5
        else:
            score += 10  # Default score if states not specified
        
        # Rating score (0-5 -> 0-20 points)
        rating_score = (transporter.rating / 5.0) * 20
        score += rating_score
        
        # On-time percentage (0-100 -> 0-15 points)
        on_time_score = (transporter.on_time_percentage() / 100.0) * 15
        score += on_time_score
        
        # Price competitiveness (lower is better)
        # Average price is ~150 Naira/ton-km, score inversely
        avg_price = 150
        if transporter.price_per_ton_km > 0:
            price_ratio = avg_price / transporter.price_per_ton_km
            price_score = min(15, price_ratio * 7.5)  # Cap at 15
            score += price_score
        
        return score
    
    def _estimate_price(self, transporter, logistics_request):
        """Estimate transport price based on distance and weight"""
        pickup_state = logistics_request.pickup_state or 'lagos'
        dest_state = logistics_request.destination_state or 'lagos'
        
        distance = calculate_distance(pickup_state, dest_state)
        weight_tons = logistics_request.quantity_tons or 1.0
        
        base_price = transporter.price_per_ton_km * weight_tons * distance
        
        # Cold chain premium (20%)
        if logistics_request.requires_cold_chain and transporter.cold_chain_capable:
            base_price *= 1.20
        
        return round(base_price, 2)
    
    def notify_transporters(self, logistics_request, matching_transporters):
        """
        Send notifications to matching transporters via all channels
        """
        from models import User, TransportProfile
        
        notification_count = 0
        
        for match in matching_transporters:
            transporter = match['transporter']
            user = transporter.user
            
            if not user:
                continue
            
            # Prepare notification message
            message = self._format_job_notification(logistics_request, match)
            
            # Send via user's preferred channel
            if user.source_channel == 'ussd' or user.is_ussd_user:
                # Queue for USSD notification (they'll see it when they dial)
                self._queue_ussd_notification(user, logistics_request.id, message)
                notification_count += 1
            
            if user.sms_enabled and user.phone_number:
                self._send_sms_notification(user.phone_number, message, user.preferred_language)
                notification_count += 1
            
            if user.whatsapp_id:
                self._send_whatsapp_notification(user.whatsapp_id, message, user.preferred_language)
                notification_count += 1
        
        logger.info(f"Sent {notification_count} notifications for logistics request {logistics_request.id}")
        return notification_count
    
    def _format_job_notification(self, logistics_request, match):
        """Format job notification message"""
        produce_name = logistics_request.produce.name if logistics_request.produce else 'Produce'
        
        return {
            'job_id': logistics_request.id,
            'produce': produce_name,
            'from': logistics_request.pickup_location or logistics_request.pickup_state,
            'to': logistics_request.destination_address or logistics_request.destination_state,
            'weight_tons': logistics_request.quantity_tons,
            'cold_chain': logistics_request.requires_cold_chain,
            'preferred_date': logistics_request.preferred_date.strftime('%d/%m/%Y') if logistics_request.preferred_date else 'Flexible',
            'estimated_price': match.get('estimated_price', 0)
        }
    
    def _queue_ussd_notification(self, user, job_id, message):
        """Queue notification for USSD users (stored in session data)"""
        # In practice, this would add to a notification queue
        # For now, we log it
        logger.info(f"USSD notification queued for user {user.id}: Job #{job_id}")
    
    def _send_sms_notification(self, phone_number, message, language='en'):
        """Send SMS notification for new job"""
        try:
            from multilingual_service import multilingual
            
            # Get translated message template if available
            msg_template = multilingual.get_message('new_transport_job', language)
            if msg_template and '{job_id}' in msg_template:
                sms_text = msg_template.format(
                    job_id=message['job_id'],
                    produce=message['produce'],
                    from_location=message['from'],
                    to_location=message['to'],
                    weight=message['weight_tons'],
                    price=f"₦{message['estimated_price']:,.0f}"
                )
            else:
                # Fallback message
                sms_text = f"New Job #{message['job_id']}: Transport {message['produce']} from {message['from']} to {message['to']}. Est. ₦{message['estimated_price']:,.0f}. Reply BID {message['job_id']} [amount]"
            
            # Send via Africa's Talking
            import os
            username = os.environ.get('AFRICASTALKING_USERNAME', 'sandbox')
            api_key = os.environ.get('AFRICASTALKING_API_KEY', '')
            
            if api_key:
                from sms_service import SMSService
                sms_service = SMSService(username, api_key)
                sms_service.send_sms(phone_number, sms_text)
            
            logger.info(f"SMS sent to {phone_number} for job #{message['job_id']}")
            return True
        except Exception as e:
            logger.error(f"SMS notification failed: {e}")
            return False
    
    def _send_whatsapp_notification(self, whatsapp_id, message, language='en'):
        """Send WhatsApp notification for new job"""
        # WhatsApp integration placeholder
        logger.info(f"WhatsApp notification queued for {whatsapp_id}: Job #{message['job_id']}")
        return True
    
    def process_bid(self, logistics_request_id, transporter_id, bid_amount, eta_hours=24, notes='', source_channel='web'):
        """
        Process a new bid from a transporter
        """
        from models import LogisticsRequest, LogisticsBid, TransportProfile
        from app import db
        
        logistics_request = LogisticsRequest.query.get(logistics_request_id)
        if not logistics_request:
            return {'success': False, 'error': 'Job not found'}
        
        if logistics_request.status not in ['pending', 'bidding']:
            return {'success': False, 'error': 'Job no longer accepting bids'}
        
        transporter = TransportProfile.query.get(transporter_id)
        if not transporter:
            return {'success': False, 'error': 'Transporter not found'}
        
        # Check for duplicate bid
        existing_bid = LogisticsBid.query.filter_by(
            logistics_request_id=logistics_request_id,
            transporter_id=transporter_id
        ).first()
        
        if existing_bid:
            # Update existing bid
            existing_bid.bid_amount = bid_amount
            existing_bid.eta_hours = eta_hours
            existing_bid.notes = notes
            existing_bid.status = 'pending'
            db.session.commit()
            return {'success': True, 'bid_id': existing_bid.id, 'updated': True}
        
        # Create new bid
        new_bid = LogisticsBid(
            logistics_request_id=logistics_request_id,
            transporter_id=transporter_id,
            bid_amount=bid_amount,
            eta_hours=eta_hours,
            notes=notes,
            source_channel=source_channel
        )
        
        db.session.add(new_bid)
        
        # Update logistics request status to bidding
        if logistics_request.status == 'pending':
            logistics_request.status = 'bidding'
        
        db.session.commit()
        
        logger.info(f"New bid ₦{bid_amount:,.0f} from transporter {transporter_id} on job {logistics_request_id}")
        
        return {'success': True, 'bid_id': new_bid.id, 'updated': False}
    
    def accept_bid(self, logistics_request_id, bid_id, requester_id):
        """
        Accept a bid and assign transporter to job
        """
        from models import LogisticsRequest, LogisticsBid, Transaction
        from app import db
        
        logistics_request = LogisticsRequest.query.get(logistics_request_id)
        if not logistics_request:
            return {'success': False, 'error': 'Job not found'}
        
        if logistics_request.requester_id != requester_id:
            return {'success': False, 'error': 'Unauthorized'}
        
        bid = LogisticsBid.query.get(bid_id)
        if not bid or bid.logistics_request_id != logistics_request_id:
            return {'success': False, 'error': 'Bid not found'}
        
        if bid.status != 'pending':
            return {'success': False, 'error': 'Bid no longer available'}
        
        # Accept the winning bid
        bid.status = 'accepted'
        
        # Reject all other bids
        other_bids = LogisticsBid.query.filter(
            LogisticsBid.logistics_request_id == logistics_request_id,
            LogisticsBid.id != bid_id
        ).all()
        
        for other_bid in other_bids:
            other_bid.status = 'rejected'
        
        # Update logistics request
        logistics_request.status = 'assigned'
        logistics_request.winning_bid_id = bid.id
        logistics_request.escrow_amount = bid.bid_amount
        
        # Release first 50% payment to transporter
        first_payment = bid.bid_amount * 0.50
        self._release_payment(bid.transporter, first_payment, 'first_payment', logistics_request_id)
        logistics_request.first_payment_released = True
        
        db.session.commit()
        
        # Notify transporter of winning bid
        self._notify_bid_acceptance(bid)
        
        logger.info(f"Bid {bid_id} accepted for job {logistics_request_id}, first payment ₦{first_payment:,.0f} released")
        
        return {'success': True, 'message': 'Bid accepted, 50% payment released'}
    
    def _release_payment(self, transporter, amount, payment_type, logistics_request_id):
        """Release payment to transporter's wallet"""
        from models import Transaction
        from app import db
        
        # Update transporter wallet
        transporter.wallet_balance += amount
        
        # Create transaction record
        transaction = Transaction(
            user_id=transporter.user_id,
            transaction_type='logistics',
            amount=amount,
            status='success',
            reference=f"LOGISTICS-{payment_type.upper()}-{logistics_request_id}-{datetime.utcnow().timestamp()}"
        )
        db.session.add(transaction)
        
        logger.info(f"Payment ₦{amount:,.0f} ({payment_type}) released to transporter {transporter.id}")
    
    def _notify_bid_acceptance(self, bid):
        """Notify transporter that their bid was accepted"""
        user = bid.transporter.user
        if not user:
            return
        
        message = f"Congratulations! Your bid of ₦{bid.bid_amount:,.0f} for Job #{bid.logistics_request_id} has been accepted. 50% payment has been released to your wallet."
        
        if user.sms_enabled and user.phone_number:
            try:
                import os
                username = os.environ.get('AFRICASTALKING_USERNAME', 'sandbox')
                api_key = os.environ.get('AFRICASTALKING_API_KEY', '')
                if api_key:
                    from sms_service import SMSService
                    sms_service = SMSService(username, api_key)
                    sms_service.send_sms(user.phone_number, message)
            except Exception as e:
                logger.error(f"Failed to send bid acceptance SMS: {e}")
    
    def verify_cold_chain_trip(self, logistics_request_id):
        """
        Verify cold chain compliance for a trip
        Returns True if all temperature readings were within range
        """
        from models import LogisticsRequest, ColdChainLog, ColdChainDevice
        from app import db
        
        logistics_request = LogisticsRequest.query.get(logistics_request_id)
        if not logistics_request:
            return {'verified': False, 'error': 'Job not found'}
        
        if not logistics_request.requires_cold_chain:
            return {'verified': True, 'message': 'Cold chain not required'}
        
        # Get all temperature logs for this trip
        logs = ColdChainLog.query.filter_by(logistics_request_id=logistics_request_id).all()
        
        if not logs:
            return {'verified': False, 'error': 'No temperature data recorded'}
        
        # Get device settings
        device_id = logs[0].device_id if logs else None
        device = ColdChainDevice.query.filter_by(device_id=device_id).first()
        
        max_temp = device.max_temp_allowed if device else 4.0
        min_temp = device.min_temp_allowed if device else -2.0
        
        # Check all readings
        violations = []
        for log in logs:
            if not log.is_within_range(max_temp, min_temp):
                violations.append({
                    'timestamp': log.timestamp.isoformat(),
                    'temperature': log.temperature_celsius,
                    'allowed_range': f"{min_temp}°C to {max_temp}°C"
                })
                log.trip_verified = False
            else:
                log.trip_verified = True
        
        db.session.commit()
        
        verified = len(violations) == 0
        
        return {
            'verified': verified,
            'total_readings': len(logs),
            'violations': len(violations),
            'violation_details': violations[:5] if violations else [],
            'min_temp_recorded': min(log.temperature_celsius for log in logs),
            'max_temp_recorded': max(log.temperature_celsius for log in logs),
            'avg_temp': sum(log.temperature_celsius for log in logs) / len(logs)
        }
    
    def complete_delivery(self, logistics_request_id, requester_id):
        """
        Mark delivery as complete and release final payment
        """
        from models import LogisticsRequest
        from app import db
        
        logistics_request = LogisticsRequest.query.get(logistics_request_id)
        if not logistics_request:
            return {'success': False, 'error': 'Job not found'}
        
        if logistics_request.requester_id != requester_id:
            return {'success': False, 'error': 'Unauthorized'}
        
        if logistics_request.status != 'in_transit':
            return {'success': False, 'error': 'Job not in transit'}
        
        winning_bid = logistics_request.winning_bid
        if not winning_bid:
            return {'success': False, 'error': 'No winning bid found'}
        
        transporter = winning_bid.transporter
        
        # Verify cold chain if required
        bonus_amount = 0
        if logistics_request.requires_cold_chain:
            verification = self.verify_cold_chain_trip(logistics_request_id)
            if verification['verified']:
                # 15% bonus for successful cold chain delivery
                bonus_amount = winning_bid.bid_amount * 0.15
                logistics_request.cold_chain_bonus_earned = True
                logger.info(f"Cold chain verified for job {logistics_request_id}, ₦{bonus_amount:,.0f} bonus earned")
            else:
                logger.warning(f"Cold chain verification failed for job {logistics_request_id}: {verification.get('violations', 0)} violations")
        
        # Release final 50% + bonus
        final_payment = (winning_bid.bid_amount * 0.50) + bonus_amount
        self._release_payment(transporter, final_payment, 'final_payment', logistics_request_id)
        
        # Update logistics request
        logistics_request.status = 'delivered'
        logistics_request.final_payment_released = True
        
        # Update transporter stats
        transporter.total_trips += 1
        transporter.successful_trips += 1
        
        db.session.commit()
        
        # Notify transporter
        self._notify_delivery_complete(winning_bid, final_payment, bonus_amount)
        
        return {
            'success': True,
            'message': 'Delivery completed',
            'final_payment': final_payment,
            'cold_chain_bonus': bonus_amount
        }
    
    def _notify_delivery_complete(self, bid, final_payment, bonus):
        """Notify transporter of delivery completion"""
        user = bid.transporter.user
        if not user:
            return
        
        bonus_text = f" (includes ₦{bonus:,.0f} cold chain bonus)" if bonus > 0 else ""
        message = f"Delivery complete! Final payment of ₦{final_payment:,.0f}{bonus_text} has been released to your wallet."
        
        if user.sms_enabled and user.phone_number:
            try:
                import os
                username = os.environ.get('AFRICASTALKING_USERNAME', 'sandbox')
                api_key = os.environ.get('AFRICASTALKING_API_KEY', '')
                if api_key:
                    from sms_service import SMSService
                    sms_service = SMSService(username, api_key)
                    sms_service.send_sms(user.phone_number, message)
            except Exception as e:
                logger.error(f"Failed to send delivery completion SMS: {e}")
    
    def get_available_jobs(self, transporter_id, limit=10):
        """Get available jobs for a transporter based on their profile"""
        from models import LogisticsRequest, TransportProfile
        
        transporter = TransportProfile.query.get(transporter_id)
        if not transporter:
            return []
        
        # Get all pending/bidding jobs
        available_jobs = LogisticsRequest.query.filter(
            LogisticsRequest.status.in_(['pending', 'bidding'])
        ).order_by(LogisticsRequest.timestamp.desc()).limit(limit * 2).all()
        
        # Filter and score jobs
        matched_jobs = []
        for job in available_jobs:
            score = self._calculate_transporter_score(transporter, job)
            if score > 0:
                matched_jobs.append({
                    'job': job,
                    'score': score,
                    'estimated_price': self._estimate_price(transporter, job)
                })
        
        # Sort by score and return top matches
        matched_jobs.sort(key=lambda x: x['score'], reverse=True)
        return matched_jobs[:limit]
    
    def get_transporter_bids(self, transporter_id):
        """Get all bids for a transporter"""
        from models import LogisticsBid
        
        return LogisticsBid.query.filter_by(
            transporter_id=transporter_id
        ).order_by(LogisticsBid.created_at.desc()).all()
    
    def get_active_trips(self, transporter_id):
        """Get active trips for a transporter"""
        from models import LogisticsRequest, LogisticsBid
        
        # Get accepted bids for this transporter
        accepted_bids = LogisticsBid.query.filter_by(
            transporter_id=transporter_id,
            status='accepted'
        ).all()
        
        active_trips = []
        for bid in accepted_bids:
            if bid.logistics_request.status in ['assigned', 'in_transit']:
                active_trips.append(bid.logistics_request)
        
        return active_trips


# Singleton instance
logistics_service = LogisticsService()
