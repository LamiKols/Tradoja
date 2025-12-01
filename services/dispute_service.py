"""
Dispute Resolution Service for AgroLink
Handles complaints with tiered SLAs: Critical (4hr), High (12hr), Medium (24hr), Low (48hr)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DisputeService:
    """
    Dispute resolution service with SLA tracking and escalation
    
    SLA Tiers:
    - Critical: 4hr response, 24hr resolution (fraud, major delivery failure)
    - High: 12hr response, 48hr resolution (payment issues, quality problems)
    - Medium: 24hr response, 72hr resolution (standard complaints)
    - Low: 48hr response, 7-day resolution (minor issues)
    """
    
    DISPUTE_TYPES = {
        'quality': {'name': 'Quality Issue', 'default_severity': 'medium'},
        'non_delivery': {'name': 'Non-Delivery', 'default_severity': 'high'},
        'payment': {'name': 'Payment Problem', 'default_severity': 'high'},
        'fraud': {'name': 'Suspected Fraud', 'default_severity': 'critical'},
        'quantity': {'name': 'Quantity Mismatch', 'default_severity': 'medium'},
        'damage': {'name': 'Damaged Goods', 'default_severity': 'medium'},
        'late_delivery': {'name': 'Late Delivery', 'default_severity': 'low'},
        'communication': {'name': 'Communication Issue', 'default_severity': 'low'},
        'other': {'name': 'Other Issue', 'default_severity': 'medium'}
    }
    
    def __init__(self):
        self.db = None
        self.Dispute = None
        self.User = None
        self.Produce = None
        self.LogisticsRequest = None
        self.SabiBuy = None
    
    def _lazy_load_models(self):
        """Lazy load database models to avoid circular imports"""
        if self.db is None:
            from app import db
            from models import Dispute, User, Produce, LogisticsRequest, SabiBuy
            self.db = db
            self.Dispute = Dispute
            self.User = User
            self.Produce = Produce
            self.LogisticsRequest = LogisticsRequest
            self.SabiBuy = SabiBuy
    
    def file_dispute(
        self,
        complainant_id: int,
        respondent_id: int,
        dispute_type: str,
        subject: str,
        description: str,
        severity: Optional[str] = None,
        produce_id: Optional[int] = None,
        logistics_id: Optional[int] = None,
        sabibuy_id: Optional[int] = None,
        evidence_files: Optional[List[str]] = None,
        source_channel: str = 'web'
    ) -> Dict[str, Any]:
        """
        File a new dispute/complaint
        
        Returns:
            dict with 'success', 'dispute', 'ticket_number', or 'error'
        """
        self._lazy_load_models()
        
        try:
            complainant = self.User.query.get(complainant_id)
            respondent = self.User.query.get(respondent_id)
            
            if not complainant:
                return {'success': False, 'error': 'Complainant not found'}
            if not respondent:
                return {'success': False, 'error': 'Respondent not found'}
            
            if dispute_type not in self.DISPUTE_TYPES:
                return {'success': False, 'error': f'Invalid dispute type: {dispute_type}'}
            
            if not severity:
                severity = self.DISPUTE_TYPES[dispute_type]['default_severity']
            
            import json
            dispute = self.Dispute(
                complainant_id=complainant_id,
                respondent_id=respondent_id,
                dispute_type=dispute_type,
                severity=severity,
                subject=subject,
                description=description,
                evidence_files=json.dumps(evidence_files) if evidence_files else None,
                produce_id=produce_id,
                logistics_id=logistics_id,
                sabibuy_id=sabibuy_id,
                source_channel=source_channel,
                status='open'
            )
            
            dispute.set_sla_deadlines()
            
            self.db.session.add(dispute)
            self.db.session.commit()
            
            ticket_number = f"DISP-{dispute.id:06d}"
            
            self._send_dispute_notification(dispute, 'filed')
            self._notify_respondent(dispute)
            
            logger.info(f"Dispute filed: {ticket_number} - {dispute_type} ({severity})")
            
            return {
                'success': True,
                'dispute': dispute,
                'ticket_number': ticket_number,
                'sla_response_by': dispute.sla_response_by,
                'sla_resolution_by': dispute.sla_resolution_by,
                'message': f'Dispute filed. Ticket: {ticket_number}. We will respond within {self._get_response_timeframe(severity)}.'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error filing dispute: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_response_timeframe(self, severity: str) -> str:
        """Get human-readable response timeframe"""
        timeframes = {
            'critical': '4 hours',
            'high': '12 hours',
            'medium': '24 hours',
            'low': '48 hours'
        }
        return timeframes.get(severity, '24 hours')
    
    def update_dispute_status(
        self,
        dispute_id: int,
        new_status: str,
        notes: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update dispute status (investigating, awaiting_response, etc.)"""
        self._lazy_load_models()
        
        try:
            dispute = self.Dispute.query.get(dispute_id)
            if not dispute:
                return {'success': False, 'error': 'Dispute not found'}
            
            valid_statuses = ['open', 'investigating', 'awaiting_response', 'resolved', 'escalated', 'closed']
            if new_status not in valid_statuses:
                return {'success': False, 'error': f'Invalid status: {new_status}'}
            
            old_status = dispute.status
            dispute.status = new_status
            
            if notes:
                dispute.resolution_notes = (dispute.resolution_notes or '') + \
                    f'\n[{datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] Status: {new_status}. {notes}'
            
            if new_status == 'investigating' and old_status == 'open':
                self._send_dispute_notification(dispute, 'acknowledged')
            
            self.db.session.commit()
            
            logger.info(f"Dispute {dispute_id} status changed: {old_status} -> {new_status}")
            
            return {
                'success': True,
                'dispute': dispute,
                'message': f'Dispute status updated to {new_status}'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error updating dispute status: {e}")
            return {'success': False, 'error': str(e)}
    
    def resolve_dispute(
        self,
        dispute_id: int,
        resolution_type: str,
        resolution_notes: str,
        admin_id: int,
        refund_amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """Resolve a dispute with specified resolution type"""
        self._lazy_load_models()
        
        try:
            dispute = self.Dispute.query.get(dispute_id)
            if not dispute:
                return {'success': False, 'error': 'Dispute not found'}
            
            if dispute.status in ['resolved', 'closed']:
                return {'success': False, 'error': 'Dispute already resolved'}
            
            valid_resolutions = ['refund_full', 'refund_partial', 'replacement', 'credit', 'dismissed', 'escalated']
            if resolution_type not in valid_resolutions:
                return {'success': False, 'error': f'Invalid resolution type: {resolution_type}'}
            
            dispute.status = 'resolved'
            dispute.resolution_type = resolution_type
            dispute.resolution_notes = resolution_notes
            dispute.resolution_amount = refund_amount
            dispute.resolved_by = admin_id
            dispute.resolved_at = datetime.utcnow()
            
            if dispute.sla_resolution_by and datetime.utcnow() > dispute.sla_resolution_by:
                dispute.sla_breached = True
            
            self.db.session.commit()
            
            self._send_dispute_notification(dispute, 'resolved')
            self._notify_respondent_resolution(dispute)
            
            logger.info(f"Dispute {dispute_id} resolved: {resolution_type}")
            
            return {
                'success': True,
                'dispute': dispute,
                'sla_met': not dispute.sla_breached,
                'message': f'Dispute resolved with {resolution_type}'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error resolving dispute: {e}")
            return {'success': False, 'error': str(e)}
    
    def escalate_dispute(
        self,
        dispute_id: int,
        escalation_reason: str,
        admin_id: int
    ) -> Dict[str, Any]:
        """Escalate a dispute to senior management"""
        self._lazy_load_models()
        
        try:
            dispute = self.Dispute.query.get(dispute_id)
            if not dispute:
                return {'success': False, 'error': 'Dispute not found'}
            
            dispute.status = 'escalated'
            dispute.severity = 'critical'
            dispute.resolution_notes = (dispute.resolution_notes or '') + \
                f'\n[ESCALATED {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}] {escalation_reason}'
            
            dispute.set_sla_deadlines()
            
            self.db.session.commit()
            
            self._send_admin_alert(dispute, 'escalated')
            
            logger.warning(f"Dispute {dispute_id} escalated: {escalation_reason}")
            
            return {
                'success': True,
                'dispute': dispute,
                'message': 'Dispute escalated to management'
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error escalating dispute: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_sla_breaches(self) -> Dict[str, Any]:
        """Batch job to check for SLA breaches - should run every hour"""
        self._lazy_load_models()
        
        results = {
            'checked': 0,
            'response_breaches': [],
            'resolution_breaches': [],
            'auto_escalated': []
        }
        
        try:
            now = datetime.utcnow()
            
            open_disputes = self.Dispute.query.filter(
                self.Dispute.status.in_(['open', 'investigating', 'awaiting_response'])
            ).all()
            
            results['checked'] = len(open_disputes)
            
            for dispute in open_disputes:
                if dispute.status == 'open' and dispute.sla_response_by and now > dispute.sla_response_by:
                    dispute.sla_breached = True
                    results['response_breaches'].append(dispute.id)
                    
                    if dispute.severity in ['critical', 'high']:
                        self.escalate_dispute(dispute.id, 'SLA response time breached', 0)
                        results['auto_escalated'].append(dispute.id)
                
                if dispute.sla_resolution_by and now > dispute.sla_resolution_by:
                    dispute.sla_breached = True
                    if dispute.id not in results['response_breaches']:
                        results['resolution_breaches'].append(dispute.id)
            
            self.db.session.commit()
            logger.info(f"SLA breach check: {results}")
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error checking SLA breaches: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_open_disputes(self, limit: int = 50) -> List['Dispute']:
        """Get all open disputes, ordered by severity and age"""
        self._lazy_load_models()
        
        severity_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
        
        disputes = self.Dispute.query.filter(
            self.Dispute.status.in_(['open', 'investigating', 'awaiting_response'])
        ).order_by(
            self.Dispute.created_at.asc()
        ).limit(limit).all()
        
        return sorted(disputes, key=lambda d: (severity_order.get(d.severity, 5), d.created_at))
    
    def get_disputes_by_user(self, user_id: int) -> Dict[str, List['Dispute']]:
        """Get all disputes filed by or against a user"""
        self._lazy_load_models()
        
        filed = self.Dispute.query.filter_by(complainant_id=user_id).order_by(
            self.Dispute.created_at.desc()
        ).all()
        
        received = self.Dispute.query.filter_by(respondent_id=user_id).order_by(
            self.Dispute.created_at.desc()
        ).all()
        
        return {
            'filed': filed,
            'received': received
        }
    
    def get_dispute_stats(self) -> Dict[str, Any]:
        """Get dispute statistics for admin dashboard"""
        self._lazy_load_models()
        
        try:
            all_disputes = self.Dispute.query.all()
            
            open_count = sum(1 for d in all_disputes if d.status in ['open', 'investigating', 'awaiting_response'])
            resolved_count = sum(1 for d in all_disputes if d.status == 'resolved')
            escalated_count = sum(1 for d in all_disputes if d.status == 'escalated')
            
            sla_breached = sum(1 for d in all_disputes if d.sla_breached)
            
            critical_open = sum(1 for d in all_disputes if d.severity == 'critical' and d.status not in ['resolved', 'closed'])
            
            week_ago = datetime.utcnow() - timedelta(days=7)
            weekly = [d for d in all_disputes if d.created_at >= week_ago]
            
            by_type = {}
            for d in all_disputes:
                by_type[d.dispute_type] = by_type.get(d.dispute_type, 0) + 1
            
            avg_resolution_time = None
            resolved_with_time = [d for d in all_disputes if d.resolved_at and d.created_at]
            if resolved_with_time:
                total_hours = sum(
                    (d.resolved_at - d.created_at).total_seconds() / 3600 
                    for d in resolved_with_time
                )
                avg_resolution_time = total_hours / len(resolved_with_time)
            
            return {
                'total': len(all_disputes),
                'open': open_count,
                'resolved': resolved_count,
                'escalated': escalated_count,
                'sla_breached': sla_breached,
                'critical_open': critical_open,
                'weekly_new': len(weekly),
                'by_type': by_type,
                'avg_resolution_hours': round(avg_resolution_time, 1) if avg_resolution_time else None,
                'sla_compliance_rate': round((1 - sla_breached / len(all_disputes)) * 100, 1) if all_disputes else 100
            }
            
        except Exception as e:
            logger.error(f"Error getting dispute stats: {e}")
            return {'error': str(e)}
    
    def file_dispute_via_sms(
        self,
        phone: str,
        message: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """Process dispute filed via SMS"""
        self._lazy_load_models()
        
        try:
            user = self.User.query.filter_by(phone_number=phone).first()
            if not user:
                return {
                    'success': False,
                    'error': 'Phone number not registered',
                    'sms_response': 'Please register first. Send REG to get started.'
                }
            
            parts = message.upper().strip().split()
            
            dispute_type = 'other'
            if 'FRAUD' in parts or 'SCAM' in parts:
                dispute_type = 'fraud'
            elif 'QUALITY' in parts or 'BAD' in parts:
                dispute_type = 'quality'
            elif 'PAYMENT' in parts or 'MONEY' in parts:
                dispute_type = 'payment'
            elif 'DELIVERY' in parts or 'DELIVER' in parts:
                dispute_type = 'non_delivery'
            elif 'LATE' in parts:
                dispute_type = 'late_delivery'
            
            result = self.file_dispute(
                complainant_id=user.id,
                respondent_id=0,
                dispute_type=dispute_type,
                subject=f"SMS Complaint: {message[:50]}",
                description=message,
                source_channel='sms'
            )
            
            if result.get('success'):
                return {
                    'success': True,
                    'ticket_number': result['ticket_number'],
                    'sms_response': f"Complaint received! Ticket: {result['ticket_number']}. We will call you within {self._get_response_timeframe(result['dispute'].severity)}."
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error'),
                    'sms_response': 'Could not process complaint. Please try again or call support.'
                }
                
        except Exception as e:
            logger.error(f"Error filing SMS dispute: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_dispute_notification(self, dispute: 'Dispute', event: str):
        """Send notification to complainant"""
        try:
            from sms_service import SMSService
            sms = SMSService()
            
            complainant = dispute.complainant
            if not complainant or not complainant.phone_number:
                return
            
            ticket = f"DISP-{dispute.id:06d}"
            
            if event == 'filed':
                message = f"Your complaint {ticket} has been received. We will respond within {self._get_response_timeframe(dispute.severity)}."
            elif event == 'acknowledged':
                message = f"Your complaint {ticket} is being investigated. We will update you soon."
            elif event == 'resolved':
                message = f"Your complaint {ticket} has been resolved. Resolution: {dispute.resolution_type}. Thank you for your patience."
            else:
                message = f"Update on complaint {ticket}: {event}"
            
            sms.send_sms(complainant.phone_number, message)
            
        except Exception as e:
            logger.error(f"Failed to send dispute notification: {e}")
    
    def _notify_respondent(self, dispute: 'Dispute'):
        """Notify respondent about complaint filed against them"""
        try:
            from sms_service import SMSService
            sms = SMSService()
            
            respondent = dispute.respondent
            if not respondent or not respondent.phone_number:
                return
            
            ticket = f"DISP-{dispute.id:06d}"
            message = f"A complaint ({ticket}) has been filed regarding your transaction. Please respond within {self._get_response_timeframe(dispute.severity)}."
            
            sms.send_sms(respondent.phone_number, message)
            
        except Exception as e:
            logger.error(f"Failed to notify respondent: {e}")
    
    def _notify_respondent_resolution(self, dispute: 'Dispute'):
        """Notify respondent about dispute resolution"""
        try:
            from sms_service import SMSService
            sms = SMSService()
            
            respondent = dispute.respondent
            if not respondent or not respondent.phone_number:
                return
            
            ticket = f"DISP-{dispute.id:06d}"
            message = f"Complaint {ticket} has been resolved. Resolution: {dispute.resolution_type}."
            
            sms.send_sms(respondent.phone_number, message)
            
        except Exception as e:
            logger.error(f"Failed to notify respondent of resolution: {e}")
    
    def _send_admin_alert(self, dispute: 'Dispute', event: str):
        """Send alert to admin for critical issues"""
        try:
            from sms_service import SMSService
            from models import User
            
            sms = SMSService()
            
            admins = User.query.filter_by(role='admin').all()
            ticket = f"DISP-{dispute.id:06d}"
            
            if event == 'escalated':
                message = f"[URGENT] Dispute {ticket} escalated. Type: {dispute.dispute_type}. Severity: CRITICAL."
            else:
                message = f"[ALERT] Dispute {ticket}: {event}"
            
            for admin in admins[:3]:
                if admin.phone_number:
                    sms.send_sms(admin.phone_number, message)
                    
        except Exception as e:
            logger.error(f"Failed to send admin alert: {e}")


dispute_service = DisputeService()
