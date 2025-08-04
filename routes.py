from flask import render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app import app, db
from models import User, Produce, Message, LogisticsRequest, FundingApplication
from forms import RegistrationForm, LoginForm, ProduceForm, SearchForm, MessageForm, MessageReplyForm, LogisticsRequestForm, LogisticsStatusForm, FundingApplicationForm, FundingStatusForm
from config import PRODUCE_IMAGE_MAP, DEFAULT_PRODUCE_IMAGE

@app.route('/')
def home():
    """Homepage route with featured produce data"""
    # List of featured produce with names and descriptions
    featured_produce = [
        {"name": "Yam Tubers", "desc": "Fresh from Kogi State"},
        {"name": "Tomatoes", "desc": "Organically grown, Ogun State"},
        {"name": "Pepper", "desc": "Direct from Niger State"},
        {"name": "Plantain", "desc": "Sweet and ripe, Lagos State"},
    ]
    
    return render_template('home.html', 
                         title='Welcome to AgroLink',
                         featured_produce=featured_produce,
                         image_map=PRODUCE_IMAGE_MAP,
                         default_image=DEFAULT_PRODUCE_IMAGE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash(f'Registration successful! Welcome to AgroLink Lagos, {user.name}!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard')
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Redirect to appropriate dashboard based on user role"""
    if current_user.is_farmer():
        return redirect(url_for('farmer_dashboard'))
    elif current_user.is_buyer():
        return redirect(url_for('buyer_dashboard'))
    elif current_user.is_admin():
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Invalid user role', 'danger')
        return redirect(url_for('home'))

@app.route('/farmer/dashboard')
@login_required
def farmer_dashboard():
    """Farmer dashboard route"""
    if not current_user.is_farmer():
        flash('Access denied. Farmers only.', 'danger')
        return redirect(url_for('home'))
    
    # Get farmer's produce listings
    produce_listings = Produce.query.filter_by(farmer_id=current_user.id).order_by(Produce.date_listed.desc()).all()
    
    # Get recent funding applications
    recent_funding = FundingApplication.query.filter_by(applicant_id=current_user.id)\
                                           .order_by(FundingApplication.timestamp.desc()).limit(3).all()
    
    return render_template('farmer_dashboard.html', 
                         title='Farmer Dashboard', 
                         produce_listings=produce_listings,
                         recent_funding=recent_funding)

@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    """Buyer dashboard route - marketplace view"""
    if not current_user.is_buyer():
        flash('Access denied. Buyers only.', 'danger')
        return redirect(url_for('home'))
    
    # Get search form
    form = SearchForm()
    
    # Get all available produce
    query = Produce.query.filter_by(is_available=True)
    
    # Apply search filter if provided
    if request.args.get('search_term'):
        search_term = request.args.get('search_term')
        query = query.filter(Produce.name.contains(search_term) | 
                           Produce.description.contains(search_term))
        form.search_term.data = search_term
    
    produce_listings = query.order_by(Produce.date_listed.desc()).all()
    
    return render_template('buyer_dashboard.html', 
                         title='Marketplace', 
                         produce_listings=produce_listings,
                         form=form)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard route"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    
    # Get all users and produce for oversight
    users = User.query.order_by(User.registration_date.desc()).all()
    produce_listings = Produce.query.order_by(Produce.date_listed.desc()).all()
    
    # Calculate statistics
    stats = {
        'total_users': User.query.count(),
        'total_farmers': User.query.filter_by(role='farmer').count(),
        'total_buyers': User.query.filter_by(role='buyer').count(),
        'total_produce': Produce.query.count(),
        'available_produce': Produce.query.filter_by(is_available=True).count(),
        'total_logistics': LogisticsRequest.query.count(),
        'pending_logistics': LogisticsRequest.query.filter_by(status='pending').count()
    }
    
    # Get recent logistics requests
    recent_logistics = LogisticsRequest.query.order_by(LogisticsRequest.timestamp.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                         title='Admin Dashboard', 
                         users=users, 
                         produce_listings=produce_listings,
                         recent_logistics=recent_logistics,
                         stats=stats)

@app.route('/produce/add', methods=['GET', 'POST'])
@login_required
def add_produce():
    """Add new produce listing - farmers only"""
    if not current_user.is_farmer():
        flash('Access denied. Farmers only.', 'danger')
        return redirect(url_for('home'))
    
    form = ProduceForm()
    if form.validate_on_submit():
        produce = Produce(
            name=form.name.data,
            quantity=form.quantity.data,
            price=form.price.data,
            price_unit=form.price_unit.data,
            description=form.description.data,
            is_available=form.is_available.data,
            farmer_id=current_user.id
        )
        
        try:
            db.session.add(produce)
            db.session.commit()
            flash(f'Produce "{produce.name}" has been added successfully!', 'success')
            return redirect(url_for('farmer_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Add produce error: {e}")
            flash('Failed to add produce. Please try again.', 'danger')
    
    return render_template('add_produce.html', title='Add Produce', form=form)

@app.route('/produce/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_produce(id):
    """Edit produce listing - owner only"""
    produce = Produce.query.get_or_404(id)
    
    # Check if current user owns this produce
    if produce.farmer_id != current_user.id and not current_user.is_admin():
        flash('Access denied. You can only edit your own produce listings.', 'danger')
        return redirect(url_for('farmer_dashboard'))
    
    form = ProduceForm(obj=produce)
    if form.validate_on_submit():
        produce.name = form.name.data
        produce.quantity = form.quantity.data
        produce.price = form.price.data
        produce.price_unit = form.price_unit.data
        produce.description = form.description.data
        produce.is_available = form.is_available.data
        
        try:
            db.session.commit()
            flash(f'Produce "{produce.name}" has been updated successfully!', 'success')
            return redirect(url_for('farmer_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Edit produce error: {e}")
            flash('Failed to update produce. Please try again.', 'danger')
    
    return render_template('edit_produce.html', title='Edit Produce', form=form, produce=produce)

@app.route('/produce/<int:id>')
def produce_detail(id):
    """View produce details"""
    produce = Produce.query.get_or_404(id)
    return render_template('produce_detail.html', title=produce.name, produce=produce)

@app.route('/produce/<int:id>/delete', methods=['POST'])
@login_required
def delete_produce(id):
    """Delete produce listing - owner only"""
    produce = Produce.query.get_or_404(id)
    
    # Check if current user owns this produce
    if produce.farmer_id != current_user.id and not current_user.is_admin():
        flash('Access denied. You can only delete your own produce listings.', 'danger')
        return redirect(url_for('farmer_dashboard'))
    
    try:
        db.session.delete(produce)
        db.session.commit()
        flash(f'Produce "{produce.name}" has been deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete produce error: {e}")
        flash('Failed to delete produce. Please try again.', 'danger')
    
    return redirect(url_for('farmer_dashboard'))

@app.route('/marketplace')
def marketplace():
    """Public marketplace view"""
    form = SearchForm()
    
    # Get all available produce
    query = Produce.query.filter_by(is_available=True)
    
    # Apply search filter if provided
    if request.args.get('search_term'):
        search_term = request.args.get('search_term')
        query = query.filter(Produce.name.contains(search_term) | 
                           Produce.description.contains(search_term))
        form.search_term.data = search_term
    
    produce_listings = query.order_by(Produce.date_listed.desc()).all()
    
    return render_template('produce_list.html', 
                         title='Marketplace', 
                         produce_listings=produce_listings,
                         form=form)

# Message routes
@app.route('/send_message/<int:receiver_id>')
@app.route('/send_message/<int:receiver_id>/<int:produce_id>')
@login_required
def send_message(receiver_id, produce_id=None):
    """Send message form"""
    receiver = User.query.get_or_404(receiver_id)
    produce = None
    if produce_id:
        produce = Produce.query.get_or_404(produce_id)
    
    form = MessageForm()
    form.receiver_id.data = receiver_id
    if produce_id:
        form.produce_id.data = produce_id
    
    return render_template('send_message.html', 
                         title='Send Message',
                         form=form, 
                         receiver=receiver, 
                         produce=produce)

@app.route('/send_message', methods=['POST'])
@login_required
def send_message_post():
    """Process message sending"""
    form = MessageForm()
    if form.validate_on_submit():
        receiver = User.query.get_or_404(form.receiver_id.data)
        
        message = Message(
            subject=form.subject.data,
            message_body=form.message_body.data,
            sender_id=current_user.id,
            receiver_id=form.receiver_id.data,
            produce_id=form.produce_id.data if form.produce_id.data else None
        )
        
        try:
            db.session.add(message)
            db.session.commit()
            flash(f'Message sent to {receiver.name} successfully!', 'success')
            return redirect(url_for('inbox'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Message sending error: {e}")
            flash('Failed to send message. Please try again.', 'danger')
    
    receiver = User.query.get_or_404(form.receiver_id.data)
    produce = None
    if form.produce_id.data:
        produce = Produce.query.get_or_404(form.produce_id.data)
    
    return render_template('send_message.html', 
                         title='Send Message',
                         form=form, 
                         receiver=receiver, 
                         produce=produce)

@app.route('/inbox')
@login_required
def inbox():
    """User inbox with received messages"""
    messages = Message.query.filter_by(receiver_id=current_user.id)\
                           .order_by(Message.timestamp.desc()).all()
    
    # Count unread messages
    unread_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    
    return render_template('inbox.html', 
                         title='Inbox',
                         messages=messages,
                         unread_count=unread_count)

@app.route('/sent_messages')
@login_required
def sent_messages():
    """User sent messages"""
    messages = Message.query.filter_by(sender_id=current_user.id)\
                           .order_by(Message.timestamp.desc()).all()
    
    return render_template('sent_messages.html', 
                         title='Sent Messages',
                         messages=messages)

@app.route('/message/<int:message_id>')
@login_required
def view_message(message_id):
    """View individual message and reply"""
    message = Message.query.get_or_404(message_id)
    
    # Check if user is sender or receiver
    if message.sender_id != current_user.id and message.receiver_id != current_user.id:
        abort(403)
    
    # Mark as read if current user is receiver
    if message.receiver_id == current_user.id and not message.is_read:
        message.mark_as_read()
    
    # Get conversation thread (messages between same users about same produce)
    conversation = Message.query.filter(
        ((Message.sender_id == message.sender_id) & (Message.receiver_id == message.receiver_id)) |
        ((Message.sender_id == message.receiver_id) & (Message.receiver_id == message.sender_id))
    )
    
    if message.produce_id:
        conversation = conversation.filter_by(produce_id=message.produce_id)
    
    conversation = conversation.order_by(Message.timestamp.asc()).all()
    
    form = MessageReplyForm()
    
    return render_template('view_message.html', 
                         title='Message',
                         message=message,
                         conversation=conversation,
                         form=form)

@app.route('/message/<int:message_id>/reply', methods=['POST'])
@login_required
def reply_message(message_id):
    """Reply to a message"""
    original_message = Message.query.get_or_404(message_id)
    
    # Check if user is sender or receiver of original message
    if original_message.sender_id != current_user.id and original_message.receiver_id != current_user.id:
        abort(403)
    
    form = MessageReplyForm()
    if form.validate_on_submit():
        # Determine receiver (if current user is sender, reply to receiver and vice versa)
        receiver_id = original_message.sender_id if current_user.id == original_message.receiver_id else original_message.receiver_id
        
        reply = Message(
            subject=f"Re: {original_message.subject}",
            message_body=form.message_body.data,
            sender_id=current_user.id,
            receiver_id=receiver_id,
            produce_id=original_message.produce_id
        )
        
        try:
            db.session.add(reply)
            db.session.commit()
            flash('Reply sent successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Reply sending error: {e}")
            flash('Failed to send reply. Please try again.', 'danger')
    
    return redirect(url_for('view_message', message_id=message_id))

# Logistics routes
@app.route('/logistics_request/<int:produce_id>')
@login_required
def logistics_request_form(produce_id):
    """Show logistics request form for specific produce"""
    produce = Produce.query.get_or_404(produce_id)
    form = LogisticsRequestForm()
    form.produce_id.data = produce_id
    
    return render_template('logistics_request.html', 
                         title='Request Logistics',
                         form=form, 
                         produce=produce)

@app.route('/logistics_request', methods=['POST'])
@login_required
def logistics_request_post():
    """Process logistics request submission"""
    form = LogisticsRequestForm()
    if form.validate_on_submit():
        produce = Produce.query.get_or_404(form.produce_id.data)
        
        logistics_request = LogisticsRequest(
            produce_id=form.produce_id.data,
            requester_id=current_user.id,
            request_type=form.request_type.data,
            preferred_date=form.preferred_date.data,
            preferred_time=form.preferred_time.data,
            pickup_location=form.pickup_location.data,
            destination_address=form.destination_address.data,
            notes=form.notes.data
        )
        
        try:
            db.session.add(logistics_request)
            db.session.commit()
            flash(f'Logistics request for {produce.name} submitted successfully!', 'success')
            return redirect(url_for('my_logistics_requests'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Logistics request error: {e}")
            flash('Failed to submit logistics request. Please try again.', 'danger')
    
    produce = Produce.query.get_or_404(form.produce_id.data)
    return render_template('logistics_request.html', 
                         title='Request Logistics',
                         form=form, 
                         produce=produce)

@app.route('/my_logistics_requests')
@login_required
def my_logistics_requests():
    """User's logistics requests dashboard"""
    requests = LogisticsRequest.query.filter_by(requester_id=current_user.id)\
                                   .order_by(LogisticsRequest.timestamp.desc()).all()
    
    return render_template('my_logistics_requests.html', 
                         title='My Logistics Requests',
                         requests=requests)

@app.route('/logistics_request/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_logistics_request(request_id):
    """Cancel a logistics request"""
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    
    # Check if user owns the request and can modify it
    if logistics_request.requester_id != current_user.id:
        abort(403)
    
    if not logistics_request.can_be_modified():
        flash('This request cannot be cancelled at this time.', 'warning')
        return redirect(url_for('my_logistics_requests'))
    
    try:
        logistics_request.status = 'cancelled'
        db.session.commit()
        flash('Logistics request cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Cancel logistics request error: {e}")
        flash('Failed to cancel request. Please try again.', 'danger')
    
    return redirect(url_for('my_logistics_requests'))

@app.route('/admin/logistics')
@login_required
def admin_logistics_dashboard():
    """Admin dashboard for managing all logistics requests"""
    if not current_user.is_admin():
        abort(403)
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = LogisticsRequest.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    requests = query.order_by(LogisticsRequest.timestamp.desc()).all()
    
    # Get statistics
    stats = {
        'total': LogisticsRequest.query.count(),
        'pending': LogisticsRequest.query.filter_by(status='pending').count(),
        'approved': LogisticsRequest.query.filter_by(status='approved').count(),
        'fulfilled': LogisticsRequest.query.filter_by(status='fulfilled').count(),
        'cancelled': LogisticsRequest.query.filter_by(status='cancelled').count()
    }
    
    return render_template('admin_logistics.html', 
                         title='Logistics Management',
                         requests=requests,
                         stats=stats,
                         current_filter=status_filter)

@app.route('/admin/logistics/<int:request_id>/update_status', methods=['POST'])
@login_required
def update_logistics_status(request_id):
    """Update logistics request status (admin only)"""
    if not current_user.is_admin():
        abort(403)
    
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    form = LogisticsStatusForm()
    
    if form.validate_on_submit():
        try:
            logistics_request.status = form.status.data
            db.session.commit()
            flash(f'Request status updated to {form.status.data}.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Update logistics status error: {e}")
            flash('Failed to update status. Please try again.', 'danger')
    
    return redirect(url_for('admin_logistics_dashboard'))

# Funding routes
@app.route('/funding_portal')
@login_required
def funding_portal():
    """Funding portal for farmers"""
    if not current_user.is_farmer():
        flash('Access denied. Funding portal is only available to farmers.', 'danger')
        return redirect(url_for('home'))
    
    # Get farmer's applications
    applications = FundingApplication.query.filter_by(applicant_id=current_user.id)\
                                         .order_by(FundingApplication.timestamp.desc()).all()
    
    return render_template('funding_portal.html', 
                         title='Funding Portal',
                         applications=applications)

@app.route('/funding_application', methods=['GET', 'POST'])
@login_required
def funding_application():
    """Create funding application"""
    if not current_user.is_farmer():
        flash('Access denied. Only farmers can apply for funding.', 'danger')
        return redirect(url_for('home'))
    
    # Get farmer's produce for dropdown
    user_produce = Produce.query.filter_by(farmer_id=current_user.id, is_available=True).all()
    form = FundingApplicationForm(user_produce=user_produce)
    
    if form.validate_on_submit():
        # Handle file upload
        supporting_document_path = None
        if form.supporting_document.data:
            from werkzeug.utils import secure_filename
            import os
            
            filename = secure_filename(form.supporting_document.data.filename)
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'funding')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            import uuid
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            try:
                form.supporting_document.data.save(file_path)
                supporting_document_path = f"uploads/funding/{unique_filename}"
            except Exception as e:
                app.logger.error(f"File upload error: {e}")
                flash('Failed to upload supporting document. Application saved without document.', 'warning')
        
        funding_app = FundingApplication(
            applicant_id=current_user.id,
            produce_id=form.produce_id.data,
            amount_requested=form.amount_requested.data,
            application_reason=form.application_reason.data,
            supporting_document=supporting_document_path
        )
        
        try:
            db.session.add(funding_app)
            db.session.commit()
            flash(f'Funding application for {funding_app.formatted_amount()} submitted successfully!', 'success')
            return redirect(url_for('funding_portal'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Funding application error: {e}")
            flash('Failed to submit funding application. Please try again.', 'danger')
    
    return render_template('funding_application.html', 
                         title='Apply for Funding',
                         form=form)

@app.route('/admin/funding')
@login_required
def admin_funding_dashboard():
    """Admin dashboard for managing funding applications"""
    if not current_user.is_admin():
        abort(403)
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = FundingApplication.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    applications = query.order_by(FundingApplication.timestamp.desc()).all()
    
    # Get statistics
    stats = {
        'total': FundingApplication.query.count(),
        'pending': FundingApplication.query.filter_by(status='pending').count(),
        'approved': FundingApplication.query.filter_by(status='approved').count(),
        'declined': FundingApplication.query.filter_by(status='declined').count(),
        'total_amount_requested': db.session.query(db.func.sum(FundingApplication.amount_requested)).scalar() or 0,
        'approved_amount': db.session.query(db.func.sum(FundingApplication.amount_requested)).filter_by(status='approved').scalar() or 0
    }
    
    return render_template('admin_funding.html', 
                         title='Funding Management',
                         applications=applications,
                         stats=stats,
                         current_filter=status_filter)

@app.route('/admin/funding/<int:app_id>/update_status', methods=['POST'])
@login_required
def update_funding_status(app_id):
    """Update funding application status (admin only)"""
    if not current_user.is_admin():
        abort(403)
    
    funding_app = FundingApplication.query.get_or_404(app_id)
    form = FundingStatusForm()
    
    if form.validate_on_submit():
        try:
            funding_app.status = form.status.data
            funding_app.admin_comment = form.admin_comment.data
            db.session.commit()
            flash(f'Application status updated to {form.status.data}.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Update funding status error: {e}")
            flash('Failed to update status. Please try again.', 'danger')
    
    return redirect(url_for('admin_funding_dashboard'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
