"""
End-of-week ledger summary job for Tradoja.

Sends a weekly SMS/WhatsApp summary to every farmer who has at least one
LedgerEntry in the current week.  Uses APScheduler (already installed) wired
to the Flask app context.

To start the scheduler call `start_ledger_scheduler(app)` from your app
factory or main.py after `db.init_app(app)`.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def send_weekly_ledger_summaries(app):
    """Send weekly ledger summaries — runs inside an app context."""
    with app.app_context():
        try:
            from models import db, User, LedgerEntry
            from sqlalchemy import func

            week_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=7)

            # Find farmers with at least one entry this week
            farmer_ids = (
                db.session.query(LedgerEntry.farmer_id)
                .filter(LedgerEntry.created_at >= week_start)
                .distinct()
                .all()
            )
            farmer_ids = [row[0] for row in farmer_ids]

            if not farmer_ids:
                logger.info("Weekly ledger summary: no entries this week, skipping.")
                return

            farmers = User.query.filter(User.id.in_(farmer_ids)).all()

            for farmer in farmers:
                try:
                    _send_summary_to_farmer(farmer, week_start, db)
                except Exception as e:
                    logger.error(f"Weekly summary failed for farmer {farmer.id}: {e}")

        except Exception as e:
            logger.error(f"Weekly ledger summary job error: {e}")


def _send_summary_to_farmer(farmer, week_start, db):
    from models import LedgerEntry
    from sqlalchemy import func

    total_sales = db.session.query(func.sum(LedgerEntry.amount)).filter(
        LedgerEntry.farmer_id == farmer.id,
        LedgerEntry.entry_type == 'sale',
        LedgerEntry.created_at >= week_start,
    ).scalar() or 0

    # Best-selling item by total revenue
    best = (
        db.session.query(LedgerEntry.item, func.sum(LedgerEntry.amount).label('rev'))
        .filter(
            LedgerEntry.farmer_id == farmer.id,
            LedgerEntry.entry_type == 'sale',
            LedgerEntry.created_at >= week_start,
        )
        .group_by(LedgerEntry.item)
        .order_by(func.sum(LedgerEntry.amount).desc())
        .first()
    )

    # Low stock: latest stock_adjustment entry per item — flag qty containing small numbers
    stock_entries = (
        db.session.query(LedgerEntry)
        .filter(
            LedgerEntry.farmer_id == farmer.id,
            LedgerEntry.entry_type == 'stock_adjustment',
        )
        .order_by(LedgerEntry.created_at.desc())
        .all()
    )
    seen_items: set = set()
    low_stock_items = []
    for e in stock_entries:
        if e.item in seen_items:
            continue
        seen_items.add(e.item)
        import re
        nums = re.findall(r'\d+', e.quantity or '')
        if nums and int(nums[0]) <= 5:
            low_stock_items.append(f"{e.item} ({e.quantity})")

    msg_parts = [f"This week: ₦{total_sales:,.0f} sales."]
    if best:
        msg_parts.append(f"Best seller: {best.item}.")
    if low_stock_items:
        msg_parts.append(f"Low stock: {', '.join(low_stock_items[:2])}.")

    message = ' '.join(msg_parts)

    phone = farmer.phone_number or farmer.whatsapp_id
    if not phone:
        return

    channel = getattr(farmer, 'source_channel', 'sms')
    if channel == 'whatsapp' and farmer.whatsapp_id:
        try:
            from whatsapp_service import get_whatsapp_service
            wa = get_whatsapp_service()
            wa.send_message(farmer.whatsapp_id, message)
        except Exception as e:
            logger.warning(f"WhatsApp summary send failed for {farmer.id}: {e}")
    else:
        try:
            from sms_service import sms_service
            sms_service.send_sms(farmer.phone_number, message)
        except Exception as e:
            logger.warning(f"SMS summary send failed for {farmer.id}: {e}")


def start_ledger_scheduler(app):
    """Attach an APScheduler job to send weekly summaries every Sunday at 18:00 UTC."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=send_weekly_ledger_summaries,
            trigger=CronTrigger(day_of_week='sun', hour=18, minute=0, timezone='UTC'),
            args=[app],
            id='weekly_ledger_summary',
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Ledger weekly summary scheduler started (Sunday 18:00 UTC).")
        return scheduler
    except Exception as e:
        logger.error(f"Could not start ledger scheduler: {e}")
        return None
