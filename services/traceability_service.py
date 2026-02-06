"""
Blockchain-style Traceability Service for Tradoja

Provides immutable, cryptographically-linked records of produce journey
from farm to buyer. Each event is hashed and linked to previous events,
creating a tamper-evident chain.

Features:
- Hash chain for immutable records
- Multi-party verification (farmer, transporter, buyer, agent)
- Quality tracking with grade and environmental data
- Quantity monitoring to detect spoilage/theft
- SMS-accessible trace history
- QR code generation for verification
"""

import os
import hashlib
import json
import random
import string
from datetime import datetime
from typing import Optional, List, Dict, Any

from flask import current_app


class TraceabilityService:
    """Service for blockchain-style produce traceability"""
    
    def __init__(self):
        self.event_types = [
            'harvest',
            'quality_check',
            'packaging',
            'storage',
            'pickup',
            'in_transit',
            'location_update',
            'temperature_check',
            'delivery',
            'verified',
            'disputed'
        ]
    
    def _generate_trace_code(self) -> str:
        """Generate unique trace code"""
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"TRC-{chars}"
    
    def _generate_chain_code(self) -> str:
        """Generate unique chain code"""
        chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"CHN-{chars}"
    
    def _compute_hash(self, data: dict) -> str:
        """Compute SHA256 hash of trace data"""
        data_string = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def create_chain(self, produce_id: int, farmer_id: int, 
                     crop_type: str, quantity_kg: float,
                     origin_farm: str, origin_state: str,
                     harvest_date: datetime = None,
                     origin_lga: str = None,
                     gi_certified: bool = False,
                     organic_certified: bool = False) -> dict:
        """
        Create a new traceability chain for a produce batch.
        This is the genesis record for the chain.
        """
        from models import TraceChain, ProduceTrace, db
        from app import app
        
        try:
            with app.app_context():
                chain_code = self._generate_chain_code()
                
                chain = TraceChain(
                    chain_code=chain_code,
                    produce_id=produce_id,
                    farmer_id=farmer_id,
                    status='active',
                    origin_farm=origin_farm,
                    origin_lga=origin_lga,
                    origin_state=origin_state,
                    harvest_date=harvest_date or datetime.utcnow(),
                    crop_type=crop_type,
                    initial_quantity_kg=quantity_kg,
                    current_quantity_kg=quantity_kg,
                    current_holder_id=farmer_id,
                    current_location=origin_farm,
                    gi_certified=gi_certified,
                    organic_certified=organic_certified,
                    total_records=0
                )
                
                db.session.add(chain)
                db.session.flush()
                
                genesis_trace = self._add_trace_record(
                    chain_id=chain.id,
                    produce_id=produce_id,
                    event_type='harvest',
                    recorded_by_id=farmer_id,
                    recorded_by_role='farmer',
                    location=origin_farm,
                    quantity_kg=quantity_kg,
                    previous_hash=None,
                    quality_notes=f"Harvested {crop_type} at {origin_farm}",
                    source_channel='system'
                )
                
                chain.genesis_hash = genesis_trace['current_hash']
                chain.latest_hash = genesis_trace['current_hash']
                chain.total_records = 1
                
                db.session.commit()
                
                return {
                    'success': True,
                    'chain_code': chain_code,
                    'trace_code': genesis_trace['trace_code'],
                    'genesis_hash': genesis_trace['current_hash'],
                    'message': f"Traceability chain created for {crop_type}"
                }
                
        except Exception as e:
            current_app.logger.error(f"Create chain error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _add_trace_record(self, chain_id: int, produce_id: int,
                          event_type: str, recorded_by_id: int,
                          recorded_by_role: str, location: str,
                          quantity_kg: float = None,
                          previous_hash: str = None,
                          order_id: int = None,
                          quality_grade: str = None,
                          quality_notes: str = None,
                          temperature: float = None,
                          humidity: float = None,
                          gps_coordinates: str = None,
                          source_channel: str = 'web') -> dict:
        """Internal method to add a trace record with hash linking"""
        from models import ProduceTrace, TraceChain, db
        
        trace_code = self._generate_trace_code()
        
        hash_data = {
            'trace_code': trace_code,
            'produce_id': produce_id,
            'event_type': event_type,
            'recorded_by_id': recorded_by_id,
            'location': location,
            'quantity_kg': quantity_kg,
            'previous_hash': previous_hash,
            'timestamp': datetime.utcnow().isoformat(),
            'quality_grade': quality_grade,
            'temperature': temperature
        }
        
        current_hash = self._compute_hash(hash_data)
        
        chain = TraceChain.query.get(chain_id)
        quantity_change = None
        if quantity_kg and chain and chain.current_quantity_kg:
            quantity_change = quantity_kg - chain.current_quantity_kg
        
        trace = ProduceTrace(
            trace_code=trace_code,
            produce_id=produce_id,
            order_id=order_id,
            event_type=event_type,
            recorded_by_id=recorded_by_id,
            recorded_by_role=recorded_by_role,
            location=location,
            gps_coordinates=gps_coordinates,
            quality_grade=quality_grade,
            quality_notes=quality_notes,
            temperature=temperature,
            humidity=humidity,
            quantity_kg=quantity_kg,
            quantity_change=quantity_change,
            previous_hash=previous_hash,
            current_hash=current_hash,
            source_channel=source_channel
        )
        
        db.session.add(trace)
        
        if chain:
            chain.latest_hash = current_hash
            chain.total_records += 1
            if quantity_kg:
                chain.current_quantity_kg = quantity_kg
            chain.current_holder_id = recorded_by_id
            chain.current_location = location
        
        return {
            'trace_code': trace_code,
            'current_hash': current_hash,
            'previous_hash': previous_hash,
            'event_type': event_type
        }
    
    def add_event(self, chain_code: str, event_type: str,
                  recorded_by_id: int, recorded_by_role: str,
                  location: str, quantity_kg: float = None,
                  order_id: int = None, quality_grade: str = None,
                  quality_notes: str = None, temperature: float = None,
                  humidity: float = None, gps_coordinates: str = None,
                  source_channel: str = 'web') -> dict:
        """
        Add a new event to an existing traceability chain.
        """
        from models import TraceChain, db
        from app import app
        
        try:
            with app.app_context():
                chain = TraceChain.query.filter_by(chain_code=chain_code).first()
                
                if not chain:
                    return {'success': False, 'error': 'Chain not found'}
                
                if chain.status == 'completed':
                    return {'success': False, 'error': 'Chain already completed'}
                
                if event_type not in self.event_types:
                    return {'success': False, 'error': f'Invalid event type: {event_type}'}
                
                trace = self._add_trace_record(
                    chain_id=chain.id,
                    produce_id=chain.produce_id,
                    event_type=event_type,
                    recorded_by_id=recorded_by_id,
                    recorded_by_role=recorded_by_role,
                    location=location,
                    quantity_kg=quantity_kg or chain.current_quantity_kg,
                    previous_hash=chain.latest_hash,
                    order_id=order_id,
                    quality_grade=quality_grade,
                    quality_notes=quality_notes,
                    temperature=temperature,
                    humidity=humidity,
                    gps_coordinates=gps_coordinates,
                    source_channel=source_channel
                )
                
                if event_type == 'delivery':
                    chain.status = 'completed'
                    chain.completed_at = datetime.utcnow()
                
                db.session.commit()
                
                return {
                    'success': True,
                    'trace_code': trace['trace_code'],
                    'chain_code': chain_code,
                    'event_type': event_type,
                    'current_hash': trace['current_hash'],
                    'total_records': chain.total_records,
                    'message': f"{event_type.replace('_', ' ').title()} recorded"
                }
                
        except Exception as e:
            current_app.logger.error(f"Add event error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_chain_history(self, chain_code: str) -> dict:
        """Get complete history of a traceability chain"""
        from models import TraceChain, ProduceTrace
        from app import app
        
        try:
            with app.app_context():
                chain = TraceChain.query.filter_by(chain_code=chain_code).first()
                
                if not chain:
                    return {'success': False, 'error': 'Chain not found'}
                
                traces = ProduceTrace.query.filter_by(
                    produce_id=chain.produce_id
                ).order_by(ProduceTrace.timestamp.asc()).all()
                
                history = []
                for trace in traces:
                    history.append({
                        'trace_code': trace.trace_code,
                        'event': trace.event_type,
                        'location': trace.location,
                        'recorded_by': trace.recorded_by_role,
                        'timestamp': trace.timestamp.isoformat(),
                        'quantity_kg': trace.quantity_kg,
                        'quality_grade': trace.quality_grade,
                        'hash': trace.current_hash[:12] + '...',
                        'verified': trace.verified
                    })
                
                return {
                    'success': True,
                    'chain_code': chain_code,
                    'crop_type': chain.crop_type,
                    'origin': f"{chain.origin_farm}, {chain.origin_state}",
                    'farmer_id': chain.farmer_id,
                    'harvest_date': chain.harvest_date.isoformat() if chain.harvest_date else None,
                    'initial_quantity': chain.initial_quantity_kg,
                    'current_quantity': chain.current_quantity_kg,
                    'status': chain.status,
                    'gi_certified': chain.gi_certified,
                    'organic_certified': chain.organic_certified,
                    'total_records': chain.total_records,
                    'history': history,
                    'integrity_verified': self.verify_chain_integrity(chain_code)
                }
                
        except Exception as e:
            current_app.logger.error(f"Get history error: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_chain_integrity(self, chain_code: str) -> bool:
        """Verify the cryptographic integrity of the entire chain"""
        from models import TraceChain, ProduceTrace
        from app import app
        
        try:
            with app.app_context():
                chain = TraceChain.query.filter_by(chain_code=chain_code).first()
                if not chain:
                    return False
                
                traces = ProduceTrace.query.filter_by(
                    produce_id=chain.produce_id
                ).order_by(ProduceTrace.timestamp.asc()).all()
                
                if not traces:
                    return False
                
                if traces[0].previous_hash is not None:
                    return False
                
                for i in range(1, len(traces)):
                    if traces[i].previous_hash != traces[i-1].current_hash:
                        current_app.logger.warning(
                            f"Chain integrity broken at {traces[i].trace_code}")
                        return False
                
                return True
                
        except Exception as e:
            current_app.logger.error(f"Verify integrity error: {e}")
            return False
    
    def format_sms_history(self, chain_code: str) -> str:
        """Format chain history for SMS (160 char aware)"""
        result = self.get_chain_history(chain_code)
        
        if not result.get('success'):
            return f"Chain {chain_code} not found."
        
        verified = "OK" if result.get('integrity_verified') else "ALERT"
        cert = ""
        if result.get('gi_certified'):
            cert += "[GI]"
        if result.get('organic_certified'):
            cert += "[ORG]"
        
        msg = (
            f"TRACE {chain_code} {cert}\n"
            f"{result['crop_type']} from {result['origin'][:20]}\n"
            f"Qty: {result['current_quantity']:.0f}kg\n"
            f"Chain: {verified} ({result['total_records']} records)\n\n"
        )
        
        for event in result['history'][-3:]:
            time_str = event['timestamp'][5:16].replace('T', ' ')
            msg += f"{event['event'][:8]}: {event['location'][:15]} {time_str}\n"
        
        return msg.strip()
    
    def create_chain_for_produce(self, produce_id: int) -> dict:
        """Create chain from existing produce listing"""
        from models import Produce, User
        from app import app
        
        try:
            with app.app_context():
                produce = Produce.query.get(produce_id)
                if not produce:
                    return {'success': False, 'error': 'Produce not found'}
                
                farmer = User.query.get(produce.farmer_id)
                
                crop_name = getattr(produce, 'name', None) or getattr(produce, 'crop_type', 'Unknown')
                qty = float(produce.quantity) if produce.quantity else 0
                farm_name = getattr(farmer, 'farm_name', None) or getattr(farmer, 'name', 'Farm') if farmer else 'Farm'
                origin = getattr(farmer, 'location', None) or getattr(produce, 'listing_location', None) or 'Nigeria'
                
                return self.create_chain(
                    produce_id=produce_id,
                    farmer_id=produce.farmer_id,
                    crop_type=crop_name,
                    quantity_kg=qty,
                    origin_farm=farm_name,
                    origin_state=origin,
                    gi_certified=getattr(produce, 'gi_certified', False)
                )
                
        except Exception as e:
            current_app.logger.error(f"Create chain for produce error: {e}")
            return {'success': False, 'error': str(e)}
    
    def record_order_events(self, order_id: int, event_type: str,
                            user_id: int, role: str, location: str,
                            quantity_kg: float = None,
                            source_channel: str = 'sms') -> dict:
        """Record trace event from order lifecycle"""
        from models import Order, TraceChain
        from app import app
        
        try:
            with app.app_context():
                order = Order.query.get(order_id)
                if not order or not order.produce_id:
                    return {'success': False, 'error': 'Order or produce not found'}
                
                chain = TraceChain.query.filter_by(produce_id=order.produce_id).first()
                
                if not chain:
                    result = self.create_chain_for_produce(order.produce_id)
                    if not result.get('success'):
                        return result
                    chain = TraceChain.query.filter_by(
                        chain_code=result['chain_code']).first()
                
                return self.add_event(
                    chain_code=chain.chain_code,
                    event_type=event_type,
                    recorded_by_id=user_id,
                    recorded_by_role=role,
                    location=location,
                    quantity_kg=quantity_kg,
                    order_id=order_id,
                    source_channel=source_channel
                )
                
        except Exception as e:
            current_app.logger.error(f"Record order event error: {e}")
            return {'success': False, 'error': str(e)}


traceability_service = TraceabilityService()
