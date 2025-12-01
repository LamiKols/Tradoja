from flask import render_template, url_for, flash, redirect, request, abort, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app import app, db, csrf_exempt
from models import User, Produce, Message, LogisticsRequest, FundingApplication, CSAData, ExportListing, PrecisionField, SMSInteraction, MatchRecommendation, Transaction, Subscription, PaymentLog, ProduceLagosRegistration, BulkOnboarding, ProcessorProfile, LoanApplication, TransportProfile, ColdChainDevice, ColdChainLog, LogisticsBid, ScamFlag, SabiBuy, SabiBuyOrder, SabiBuyerProfile
from forms import RegistrationForm, LoginForm, ProduceForm, SearchForm, MessageForm, MessageReplyForm, LogisticsRequestForm, LogisticsStatusForm, FundingApplicationForm, FundingStatusForm, CSAWeatherForm, CSASoilForm, ExportListingForm, ExportFilterForm, ExportStatusForm, GIAdminForm, PrecisionFieldForm, FieldAnalyticsForm, PurchaseForm, SubscriptionForm, LogisticsPaymentForm, OnboardingStep1Form, OnboardingStep2Form, OnboardingStep3FarmerForm, OnboardingStep3AggregatorForm, OnboardingStep3TransportForm, OnboardingStep3BulkTraderForm, OnboardingStep3RetailerForm, OnboardingStep3InputSupplierForm, OnboardingStep4Form, OnboardingAdminReviewForm, BulkOnboardingForm, ProcessorOnboardingStep1Form, ProcessorOnboardingStep2Form, ProcessorOnboardingStep3Form, ProcessorOnboardingStep4Form, ProcessorOnboardingStep5Form, BOILoanApplicationForm, TransportRegistrationForm, TransportRouteForm, ColdChainDeviceForm, TransportBidForm, EnhancedLogisticsRequestForm
from weather_service import WeatherService
from trade_data_service import TradeDataService
from gi_service import GIService
import os
from werkzeug.utils import secure_filename
from config import PRODUCE_IMAGE_MAP, DEFAULT_PRODUCE_IMAGE
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload

# Initialize services
weather_service = WeatherService()
trade_service = TradeDataService()
gi_service = GIService()

# Initialize matchmaking engine
try:
    from matchmaking_service import MatchmakingEngine
    matchmaking_engine = MatchmakingEngine()
except Exception as e:
    app.logger.error(f"Matchmaking engine initialization failed: {e}")
    matchmaking_engine = None

# Initialize analytics service
try:
    from analytics_service import AnalyticsService
    analytics_service = AnalyticsService()
except Exception as e:
    app.logger.error(f"Analytics service initialization failed: {e}")
    analytics_service = None

# Initialize SMS service
try:
    from sms_service import SMSService
    # Use environment variables for Africa's Talking credentials
    sms_service = SMSService(
        username=os.environ.get('AFRICASTALKING_USERNAME', 'sandbox'),
        api_key=os.environ.get('AFRICASTALKING_API_KEY', '')
    )
except Exception as e:
    app.logger.error(f"SMS service initialization failed: {e}")
    sms_service = None

# Initialize payment service
try:
    from payment_service import payment_service
except Exception as e:
    app.logger.error(f"Payment service initialization failed: {e}")
    payment_service = None

# Initialize scam detector service (Layer 5)
try:
    from services.scam_detector import scam_detector
except Exception as e:
    app.logger.error(f"Scam detector initialization failed: {e}")
    scam_detector = None

@app.route('/')
def home():
    """Homepage route - redirect authenticated users to their dashboard"""
    # Redirect authenticated users to their appropriate dashboard
    if current_user.is_authenticated:
        app.logger.info(f"User {current_user.email} role: {current_user.role}")
        if current_user.is_farmer():
            app.logger.info("Redirecting to farmer dashboard")
            # The farmer dashboard will handle onboarding redirection
            return redirect(url_for('farmer_dashboard'))
        elif current_user.is_buyer():
            app.logger.info("Redirecting to buyer dashboard")
            return redirect(url_for('buyer_dashboard'))
        elif current_user.is_admin():
            app.logger.info("Redirecting to admin dashboard")
            return redirect(url_for('admin_dashboard'))
        else:
            app.logger.warning(f"Unknown user role: {current_user.role}")
    
    # For non-authenticated users, show homepage with featured produce
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
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Get client IP for scam detection
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Check for scam patterns before registration (Layer 5)
        scam_reason = None
        scam_score = 0
        if scam_detector:
            is_scam, reason, score = scam_detector.is_scam_likely(
                user=None,
                action_type='registration',
                data={'name': form.name.data, 'email': form.email.data},
                ip_address=client_ip
            )
            
            if score >= 70:
                app.logger.warning(f"Registration blocked - Scam score {score}: {reason}")
                flash('Registration temporarily unavailable. Please try again later.', 'warning')
                return render_template('register.html', title='Register', form=form)
            elif score >= 50:
                scam_reason = reason
                scam_score = score
        
        # Create new user
        user = User(
            name=form.name.data,
            email=form.email.data.lower(),
            role=form.role.data,
            last_ip=client_ip,
            scam_score=scam_score if scam_score >= 50 else 0
        )
        
        # Set buyer_type if user is a buyer
        if form.role.data == 'buyer' and form.buyer_type.data:
            user.buyer_type = form.buyer_type.data
        
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Flag medium-score users after creation (Layer 5 post-registration hook)
            if scam_detector and scam_score >= 50:
                scam_detector.flag_new_user(user, scam_reason, scam_score, client_ip)
            
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
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('home')  # This will redirect to appropriate dashboard
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
    """Farmer dashboard route with AI-powered buyer recommendations"""
    if not current_user.is_farmer():
        flash('Access denied. Farmers only.', 'danger')
        return redirect(url_for('home'))
    
    # Check if farmer has completed Produce for Lagos onboarding
    registration = ProduceLagosRegistration.query.filter_by(user_id=current_user.id).first()
    if not registration:
        # Redirect new farmers to complete onboarding
        flash('Welcome! Please complete your Produce for Lagos registration to access all features.', 'info')
        return redirect(url_for('onboarding_start'))
    elif registration.registration_status == 'pending':
        # Show pending approval message but allow dashboard access
        flash('Your Produce for Lagos registration is under review. You have limited access until approved.', 'warning')
    elif registration.registration_status == 'rejected':
        flash('Your registration was rejected. Please contact support or resubmit your application.', 'danger')
        return redirect(url_for('onboarding_status'))
    
    # Get farmer's produce listings
    produce_listings = Produce.query.filter_by(farmer_id=current_user.id).order_by(Produce.date_listed.desc()).all()
    
    # Get recent funding applications
    recent_funding = FundingApplication.query.filter_by(applicant_id=current_user.id)\
                                           .order_by(FundingApplication.timestamp.desc()).limit(3).all()
    
    # Get latest CSA data for weather display
    latest_csa = CSAData.query.filter_by(farmer_id=current_user.id).order_by(CSAData.updated_at.desc()).first()
    
    # Get AI-powered buyer recommendations
    buyer_recommendations = []
    if matchmaking_engine:
        try:
            available_listings = [p for p in produce_listings if p.is_available]
            if available_listings:
                recommendations = matchmaking_engine.find_buyer_matches(current_user.id)
                buyer_recommendations = recommendations[:5]  # Top 5 recommendations
        except Exception as e:
            app.logger.error(f"Error getting buyer recommendations: {e}")
    
    # Get pending match recommendations for this farmer
    pending_matches = MatchRecommendation.query.filter_by(
        farmer_id=current_user.id,
        status='pending'
    ).order_by(MatchRecommendation.sent_at.desc()).limit(5).all()
    
    return render_template('farmer_dashboard.html', 
                         title='Farmer Dashboard', 
                         produce_listings=produce_listings,
                         recent_funding=recent_funding,
                         latest_csa=latest_csa,
                         buyer_recommendations=buyer_recommendations,
                         pending_matches=pending_matches)

@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    """Buyer dashboard route - overview and recommendations"""
    if not current_user.is_buyer():
        flash('Access denied. Buyers only.', 'danger')
        return redirect(url_for('home'))
    
    # Redirect agro-processors to their specific dashboard
    if current_user.is_agro_processor():
        return redirect(url_for('processor_dashboard'))
    
    # Get buyer's recent purchases
    recent_purchases = Produce.query.filter_by(buyer_id=current_user.id).order_by(Produce.sale_date.desc()).limit(5).all()
    
    # Get AI-powered seller recommendations
    seller_recommendations = []
    if matchmaking_engine:
        try:
            recommendations = matchmaking_engine.find_seller_matches(current_user.id)
            seller_recommendations = recommendations[:5]  # Top 5 recommendations
        except Exception as e:
            app.logger.error(f"Error getting seller recommendations: {e}")
    
    # Get pending match recommendations for this buyer
    pending_matches = MatchRecommendation.query.filter_by(
        buyer_id=current_user.id,
        status='pending'
    ).order_by(MatchRecommendation.sent_at.desc()).limit(5).all()
    
    # Get buyer statistics
    total_purchases = Produce.query.filter_by(buyer_id=current_user.id).count()
    total_spent = db.session.query(func.sum(Produce.price)).filter_by(buyer_id=current_user.id).scalar() or 0
    
    # Get recent logistics requests
    recent_logistics = LogisticsRequest.query.filter_by(requester_id=current_user.id).order_by(LogisticsRequest.timestamp.desc()).limit(3).all()
    
    return render_template('buyer_dashboard.html', 
                         title='Buyer Dashboard', 
                         recent_purchases=recent_purchases,
                         seller_recommendations=seller_recommendations,
                         pending_matches=pending_matches,
                         total_purchases=total_purchases,
                         total_spent=total_spent,
                         recent_logistics=recent_logistics)

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
    # Populate GI choices
    form.gi_label.choices = gi_service.get_gi_choices_for_form()
    
    if form.validate_on_submit():
        # Check for scam patterns before listing (Layer 5)
        listing_held = False
        scam_reason = None
        scam_score = 0
        if scam_detector:
            is_scam, reason, score = scam_detector.is_scam_likely(
                user=current_user,
                action_type='produce_listing',
                data={
                    'crop': form.name.data,
                    'name': form.name.data,
                    'price': form.price.data,
                    'location': current_user.location
                }
            )
            
            if score >= 70:
                app.logger.warning(f"Listing blocked - Scam score {score}: {reason}")
                flash('Listing temporarily held for review. Our team will verify shortly.', 'warning')
                return render_template('add_produce.html', title='Add Produce', form=form)
            elif score >= 50:
                listing_held = True
                scam_reason = reason
                scam_score = score
                flash('Listing will be verified by an agent before going live.', 'info')
        
        # Handle GI data
        gi_label = None
        gi_status = 'none'
        gi_custom_label = form.gi_custom_label.data
        
        if form.gi_label.data and form.gi_label.data != '':
            if form.gi_label.data == 'other' and gi_custom_label:
                gi_label = gi_custom_label
                gi_status = 'pending'  # Custom GI requests need admin review
            elif form.gi_label.data != 'other':
                gi_label = form.gi_label.data
                # Validate GI claim
                validation = gi_service.validate_gi_claim(form.name.data, gi_label, current_user.location or 'unknown')
                if validation['valid']:
                    gi_status = 'pending'  # Valid claims need admin verification
                else:
                    flash(f"GI Validation: {validation['message']}", 'warning')
                    gi_status = 'none'
                    gi_label = None
        
        produce = Produce(
            name=form.name.data,
            quantity=form.quantity.data,
            price=form.price.data,
            price_unit=form.price_unit.data,
            description=form.description.data,
            is_available=form.is_available.data,
            farmer_id=current_user.id,
            gi_label=gi_label,
            gi_status=gi_status
        )
        
        try:
            db.session.add(produce)
            db.session.commit()
            
            if scam_detector and scam_score >= 50:
                from models import ScamFlag
                flag = ScamFlag(
                    user_id=current_user.id,
                    action_type='produce_listing',
                    scam_score=scam_score,
                    reason=scam_reason,
                    status='pending',
                    detected_at=datetime.utcnow()
                )
                db.session.add(flag)
                current_user.scam_score = max(current_user.scam_score or 0, scam_score)
                db.session.commit()
            
            if produce.gi_status == 'pending':
                flash(f'Produce "{produce.name}" added! GI certification "{produce.gi_label}" is pending admin review.', 'success')
            else:
                flash(f'Produce "{produce.name}" has been added successfully!', 'success')
            return redirect(url_for('farmer_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Add produce error: {e}")
            flash('Failed to add produce. Please try again.', 'danger')
    
    return render_template('add_produce.html', title='Add Produce', form=form)


@app.route('/gi/registry')
def gi_registry():
    """Nigerian GI Registry - public view of registered GI products"""
    registered_gis = gi_service.get_registered_gis()
    pending_gis = gi_service.get_pending_gis()
    gi_stats = gi_service.get_gi_statistics()
    
    return render_template('gi_registry.html',
                         title='Nigerian GI Registry',
                         registered_gis=registered_gis,
                         pending_gis=pending_gis,
                         gi_stats=gi_stats)


@app.route('/gi/search')
def gi_search():
    """Search GI products"""
    query = request.args.get('q', '')
    results = []
    
    if query:
        results = gi_service.search_gis(query)
    else:
        results = gi_service.get_all_gis()
    
    return render_template('gi_search.html',
                         title='Search GI Products',
                         results=results,
                         query=query)


@app.route('/admin/gi/dashboard')
@login_required
def admin_gi_dashboard():
    """Admin GI management dashboard"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    
    # Get produce with pending GI claims
    pending_gi_claims = Produce.query.filter_by(gi_status='pending').all()
    verified_gi_products = Produce.query.filter_by(gi_status='verified').all()
    rejected_gi_claims = Produce.query.filter_by(gi_status='rejected').all()
    
    gi_stats = gi_service.get_gi_statistics()
    
    return render_template('admin_gi_dashboard.html',
                         title='GI Management Dashboard',
                         pending_claims=pending_gi_claims,
                         verified_products=verified_gi_products,
                         rejected_claims=rejected_gi_claims,
                         gi_stats=gi_stats)


@app.route('/admin/gi/manage/<int:produce_id>', methods=['GET', 'POST'])
@login_required
def manage_gi_claim(produce_id):
    """Manage individual GI claim"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    
    produce = Produce.query.get_or_404(produce_id)
    form = GIAdminForm()
    
    if form.validate_on_submit():
        produce.gi_status = form.gi_status.data
        produce.gi_certificate_number = form.gi_certificate_number.data
        produce.gi_admin_comment = form.gi_admin_comment.data
        
        if form.gi_status.data == 'verified':
            produce.gi_certified = True
        else:
            produce.gi_certified = False
        
        try:
            db.session.commit()
            flash(f'GI status for "{produce.name}" updated successfully!', 'success')
            return redirect(url_for('admin_gi_dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"GI management error: {e}")
            flash('Failed to update GI status. Please try again.', 'danger')
    
    # Pre-populate form with current values
    if request.method == 'GET':
        form.gi_status.data = produce.gi_status
        form.gi_certificate_number.data = produce.gi_certificate_number
        form.gi_admin_comment.data = produce.gi_admin_comment
    
    # Get GI information for reference
    gi_info = gi_service.get_gi_by_name(produce.gi_label) if produce.gi_label else None
    
    return render_template('manage_gi_claim.html',
                         title=f'Manage GI Claim - {produce.name}',
                         produce=produce,
                         form=form,
                         gi_info=gi_info)


@app.route('/precision-ag')
@login_required
def precision_agriculture():
    """Precision agriculture dashboard for farmers"""
    if current_user.role != 'farmer':
        flash('Access denied. This feature is for farmers only.', 'danger')
        return redirect(url_for('home'))
    
    # Get farmer's fields
    fields = PrecisionField.query.filter_by(farmer_id=current_user.id).all()
    
    # Get productivity KPIs
    from precision_service import PrecisionAgricultureService
    service = PrecisionAgricultureService()
    kpis = service.get_productivity_kpis(fields)
    
    return render_template('precision_agriculture.html',
                         title='Precision Agriculture',
                         fields=fields,
                         kpis=kpis)


@app.route('/precision-ag/field/new', methods=['GET', 'POST'])
@login_required
def add_precision_field():
    """Add new precision agriculture field"""
    if current_user.role != 'farmer':
        flash('Access denied. This feature is for farmers only.', 'danger')
        return redirect(url_for('home'))
    
    form = PrecisionFieldForm()
    
    if form.validate_on_submit():
        # Parse coordinates and calculate area if provided
        coordinates_data = None
        calculated_area = None
        
        if form.coordinates.data:
            try:
                import json
                coordinates_data = json.loads(form.coordinates.data)
                from precision_service import PrecisionAgricultureService
                service = PrecisionAgricultureService()
                calculated_area = service.calculate_field_area(coordinates_data)
            except Exception as e:
                app.logger.error(f"Coordinate parsing error: {e}")
        
        # Use manual coordinates if provided, otherwise use form hidden fields
        latitude = None
        longitude = None
        
        if form.manual_latitude.data and form.manual_longitude.data:
            latitude = float(form.manual_latitude.data)
            longitude = float(form.manual_longitude.data)
        elif form.center_latitude.data and form.center_longitude.data:
            latitude = float(form.center_latitude.data)
            longitude = float(form.center_longitude.data)
        
        # Create new field
        field = PrecisionField(
            farmer_id=current_user.id,
            field_name=form.field_name.data,
            crop_type=form.crop_type.data,
            field_size_hectares=calculated_area or form.field_size_hectares.data,
            planting_date=form.planting_date.data,
            soil_type=form.soil_type.data,
            irrigation_type=form.irrigation_type.data,
            fertilizer_type=form.fertilizer_type.data,
            address=form.address.data.strip() if form.address.data else None,
            center_latitude=latitude,
            center_longitude=longitude
        )
        
        if coordinates_data:
            field.set_coordinates(coordinates_data)
        
        # Calculate recommendations
        from precision_service import PrecisionAgricultureService
        service = PrecisionAgricultureService()
        recommendations = service.calculate_recommendations(
            field.crop_type, field.field_size_hectares, field.soil_type,
            field.irrigation_type, field.fertilizer_type, field.planting_date
        )
        
        # Store calculated values
        field.recommended_fertilizer_kg_ha = recommendations['fertilizer_kg_ha']
        field.recommended_irrigation_l_ha = recommendations['irrigation_l_ha']
        field.estimated_yield_tons_ha = recommendations['estimated_yield_tons_ha']
        field.planting_season_fit = recommendations['season_fit']
        field.set_risk_warnings(recommendations['warnings'])
        
        try:
            db.session.add(field)
            db.session.commit()
            flash(f'Field "{field.field_name}" added successfully with analytics!', 'success')
            return redirect(url_for('precision_agriculture'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Add field error: {e}")
            flash('Failed to add field. Please try again.', 'danger')
    
    return render_template('add_precision_field.html', title='Add Field', form=form)


@app.route('/precision-ag/field/<int:field_id>')
@login_required
def view_precision_field(field_id):
    """View detailed field analytics"""
    field = PrecisionField.query.get_or_404(field_id)
    
    if field.farmer_id != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('precision_agriculture'))
    
    # Get fresh recommendations
    from precision_service import PrecisionAgricultureService
    service = PrecisionAgricultureService()
    recommendations = service.calculate_recommendations(
        field.crop_type, field.field_size_hectares, field.soil_type,
        field.irrigation_type, field.fertilizer_type, field.planting_date
    )
    
    return render_template('precision_field_detail.html',
                         title=f'Field: {field.field_name}',
                         field=field,
                         recommendations=recommendations)


@app.route('/precision-ag/field/<int:field_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_precision_field(field_id):
    """Edit precision agriculture field"""
    field = PrecisionField.query.get_or_404(field_id)
    
    if field.farmer_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('precision_agriculture'))
    
    form = FieldAnalyticsForm()
    
    if form.validate_on_submit():
        # Update field data
        field.crop_type = form.crop_type.data
        field.planting_date = form.planting_date.data
        field.soil_type = form.soil_type.data
        field.irrigation_type = form.irrigation_type.data
        field.fertilizer_type = form.fertilizer_type.data
        
        # Recalculate recommendations
        from precision_service import PrecisionAgricultureService
        service = PrecisionAgricultureService()
        recommendations = service.calculate_recommendations(
            field.crop_type, field.field_size_hectares, field.soil_type,
            field.irrigation_type, field.fertilizer_type, field.planting_date
        )
        
        # Update calculated values
        field.recommended_fertilizer_kg_ha = recommendations['fertilizer_kg_ha']
        field.recommended_irrigation_l_ha = recommendations['irrigation_l_ha']
        field.estimated_yield_tons_ha = recommendations['estimated_yield_tons_ha']
        field.planting_season_fit = recommendations['season_fit']
        field.set_risk_warnings(recommendations['warnings'])
        field.last_updated = datetime.utcnow()
        
        try:
            db.session.commit()
            flash(f'Field "{field.field_name}" updated successfully!', 'success')
            return redirect(url_for('view_precision_field', field_id=field.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Edit field error: {e}")
            flash('Failed to update field. Please try again.', 'danger')
    
    # Pre-populate form
    if request.method == 'GET':
        form.crop_type.data = field.crop_type
        form.planting_date.data = field.planting_date
        form.soil_type.data = field.soil_type
        form.irrigation_type.data = field.irrigation_type
        form.fertilizer_type.data = field.fertilizer_type
    
    return render_template('edit_precision_field.html',
                         title=f'Edit Field: {field.field_name}',
                         field=field,
                         form=form)


@app.route('/precision-ag/field/<int:field_id>/report')
@login_required
def field_report(field_id):
    """Generate field report for export"""
    field = PrecisionField.query.get_or_404(field_id)
    
    if field.farmer_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('precision_agriculture'))
    
    from precision_service import PrecisionAgricultureService
    service = PrecisionAgricultureService()
    report = service.generate_field_report(field)
    
    return render_template('precision_field_report.html',
                         title=f'Field Report: {field.field_name}',
                         field=field,
                         report=report)


@app.route('/precision-ag/field/<int:field_id>/delete', methods=['POST'])
@login_required
def delete_precision_field(field_id):
    """Delete precision agriculture field"""
    field = PrecisionField.query.get_or_404(field_id)
    
    if field.farmer_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('precision_agriculture'))
    
    try:
        field_name = field.field_name
        db.session.delete(field)
        db.session.commit()
        flash(f'Field "{field_name}" deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Delete field error: {e}")
        flash('Failed to delete field. Please try again.', 'danger')
    
    return redirect(url_for('precision_agriculture'))


@app.route('/api/precision-ag/calculate', methods=['POST'])
@login_required
def calculate_field_analytics():
    """API endpoint for real-time field analytics calculation"""
    if current_user.role != 'farmer':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        from precision_service import PrecisionAgricultureService
        service = PrecisionAgricultureService()
        
        # Parse planting date
        planting_date = None
        if data.get('planting_date'):
            from datetime import datetime
            planting_date = datetime.strptime(data['planting_date'], '%Y-%m-%d').date()
        
        recommendations = service.calculate_recommendations(
            data.get('crop_type'),
            float(data.get('field_size_hectares', 1.0)),
            data.get('soil_type'),
            data.get('irrigation_type'),
            data.get('fertilizer_type'),
            planting_date
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
        
    except Exception as e:
        app.logger.error(f"Analytics calculation error: {e}")
        return jsonify({'error': 'Calculation failed'}), 500

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


# Climate-Smart Agriculture Routes
@app.route('/csa')
@login_required
def csa_dashboard():
    """Climate-Smart Agriculture dashboard"""
    if not current_user.is_farmer():
        flash('Climate-Smart Agriculture tools are available for farmers only.', 'warning')
        return redirect(url_for('home'))
    
    # Get user's latest CSA data
    latest_csa = CSAData.query.filter_by(farmer_id=current_user.id).order_by(CSAData.updated_at.desc()).first()
    
    return render_template('csa_dashboard.html', 
                         title='Climate-Smart Agriculture',
                         latest_csa=latest_csa)


@app.route('/csa/weather', methods=['GET', 'POST'])
@login_required
def csa_weather():
    """Weather data and analysis page"""
    if not current_user.is_farmer():
        flash('Access denied. Farmers only.', 'danger')
        return redirect(url_for('home'))
    
    weather_form = CSAWeatherForm()
    soil_form = CSASoilForm()
    weather_service = WeatherService()
    
    weather_data = None
    crop_recommendations = []
    carbon_footprint = None
    csa_record = None
    
    if weather_form.validate_on_submit() and weather_form.submit.data:
        # Fetch weather data
        if weather_form.latitude.data and weather_form.longitude.data:
            weather_data = weather_service.get_weather_by_coordinates(
                weather_form.latitude.data, 
                weather_form.longitude.data
            )
        else:
            weather_data = weather_service.get_current_weather(weather_form.city.data)
        
        if weather_data:
            # Create or update CSA record
            csa_record = CSAData.query.filter_by(farmer_id=current_user.id).first()
            if not csa_record:
                csa_record = CSAData(farmer_id=current_user.id)
                db.session.add(csa_record)
            
            csa_record.city = weather_form.city.data
            csa_record.latitude = weather_form.latitude.data
            csa_record.longitude = weather_form.longitude.data
            csa_record.set_weather_data(weather_data)
            
            db.session.commit()
            flash(f'Weather data updated for {weather_data["city"]}!', 'success')
        else:
            flash('Unable to fetch weather data. Please check your location and try again.', 'danger')
    
    elif soil_form.validate_on_submit() and soil_form.submit.data:
        # Handle soil data and generate recommendations
        csa_record = CSAData.query.filter_by(farmer_id=current_user.id).first()
        if not csa_record:
            csa_record = CSAData(farmer_id=current_user.id, city='Lagos')
            db.session.add(csa_record)
        
        # Update soil and carbon data
        csa_record.soil_type = soil_form.soil_type.data
        csa_record.soil_moisture = soil_form.soil_moisture.data
        csa_record.field_size = soil_form.field_size.data
        csa_record.fertilizer_type = soil_form.fertilizer_type.data
        csa_record.fertilizer_amount = soil_form.fertilizer_amount.data or 0
        csa_record.estimated_yield = soil_form.estimated_yield.data
        
        # Get weather data for recommendations
        weather_data = csa_record.get_weather_data()
        
        # Generate crop recommendations
        crop_recommendations = weather_service.get_crop_recommendations(
            weather_data, 
            soil_form.soil_type.data,
            soil_form.soil_moisture.data
        )
        csa_record.set_crop_recommendations(crop_recommendations)
        
        # Calculate carbon footprint
        carbon_footprint = weather_service.calculate_carbon_footprint(
            soil_form.field_size.data,
            soil_form.fertilizer_type.data,
            soil_form.fertilizer_amount.data or 0,
            soil_form.estimated_yield.data
        )
        csa_record.carbon_footprint = carbon_footprint['total_emissions']
        
        db.session.commit()
        flash('Soil analysis completed! Check your crop recommendations and carbon footprint below.', 'success')
    
    # Load existing data if available
    csa_record = CSAData.query.filter_by(farmer_id=current_user.id).first()
    if csa_record:
        weather_data = csa_record.get_weather_data()
        crop_recommendations = csa_record.get_crop_recommendations()
        
        if csa_record.carbon_footprint:
            # Reconstruct carbon footprint data
            carbon_footprint = weather_service.calculate_carbon_footprint(
                csa_record.field_size or 1,
                csa_record.fertilizer_type or 'none',
                csa_record.fertilizer_amount or 0,
                csa_record.estimated_yield or 1
            )
        
        # Pre-fill forms with existing data
        if not weather_form.city.data:
            weather_form.city.data = csa_record.city
        if not soil_form.soil_type.data and csa_record.soil_type:
            soil_form.soil_type.data = csa_record.soil_type
            soil_form.soil_moisture.data = csa_record.soil_moisture
            soil_form.field_size.data = csa_record.field_size
            soil_form.fertilizer_type.data = csa_record.fertilizer_type
            soil_form.fertilizer_amount.data = csa_record.fertilizer_amount
            soil_form.estimated_yield.data = csa_record.estimated_yield
    
    return render_template('csa_weather.html',
                         title='Climate-Smart Agriculture - Weather & Analysis',
                         weather_form=weather_form,
                         soil_form=soil_form,
                         weather_data=weather_data,
                         crop_recommendations=crop_recommendations,
                         carbon_footprint=carbon_footprint,
                         weather_service=weather_service)


# Cross-Border Trade Routes
@app.route('/export')
@login_required
def export_dashboard():
    """Export trade dashboard"""
    trade_service = TradeDataService()
    
    # Get trending exports and market opportunities
    trending_exports = trade_service.get_trending_exports()
    market_opportunities = trade_service.get_market_opportunities()
    seasonal_calendar = trade_service.get_seasonal_calendar()
    
    # Get user's export listings if farmer
    user_exports = []
    if current_user.is_farmer():
        user_exports = ExportListing.query.filter_by(farmer_id=current_user.id).order_by(ExportListing.created_at.desc()).limit(5).all()
    
    # Get recent approved listings for buyers
    approved_exports = ExportListing.query.filter_by(status='approved').order_by(ExportListing.created_at.desc()).limit(10).all()
    
    return render_template('export_dashboard.html',
                         title='Cross-Border Trade',
                         trending_exports=trending_exports,
                         market_opportunities=market_opportunities,
                         seasonal_calendar=seasonal_calendar,
                         user_exports=user_exports,
                         approved_exports=approved_exports)


@app.route('/export/create', methods=['GET', 'POST'])
@login_required
def create_export_listing():
    """Create new export listing (farmers only)"""
    if not current_user.is_farmer():
        flash('Only farmers can create export listings.', 'danger')
        return redirect(url_for('export_dashboard'))
    
    form = ExportListingForm()
    
    if form.validate_on_submit():
        try:
            # Handle file upload
            phytosanitary_filename = None
            if form.phytosanitary_file.data:
                file = form.phytosanitary_file.data
                filename = secure_filename(file.filename)
                # Add timestamp to avoid conflicts
                import time
                timestamp = str(int(time.time()))
                phytosanitary_filename = f"{timestamp}_{filename}"
                filepath = os.path.join('static/uploads/certificates', phytosanitary_filename)
                file.save(filepath)
            
            # Collect compliance standards
            compliance_standards = []
            if form.eu_gi.data:
                compliance_standards.append('EU Geographical Indication (GI)')
            if form.usda_organic.data:
                compliance_standards.append('USDA Organic Certified')
            if form.fair_trade.data:
                compliance_standards.append('Fair Trade Certified')
            if form.global_gap.data:
                compliance_standards.append('GlobalGAP Certified')
            if form.iso_22000.data:
                compliance_standards.append('ISO 22000 Food Safety')
            if form.haccp.data:
                compliance_standards.append('HACCP Certified')
            
            # Create export listing
            export_listing = ExportListing(
                farmer_id=current_user.id,
                produce_name=form.produce_name.data,
                quantity=form.quantity.data,
                price=form.price.data,
                origin_state=form.origin_state.data,
                target_market=form.target_market.data,
                has_phytosanitary=form.has_phytosanitary.data,
                phytosanitary_file=phytosanitary_filename,
                description=form.description.data,
                harvest_date=form.harvest_date.data,
                shipment_window_start=form.shipment_window_start.data,
                shipment_window_end=form.shipment_window_end.data
            )
            
            export_listing.set_compliance_standards(compliance_standards)
            
            db.session.add(export_listing)
            db.session.commit()
            
            flash('Export listing created successfully! It will be reviewed by administrators.', 'success')
            return redirect(url_for('my_export_listings'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Export listing creation error: {e}")
            flash('Failed to create export listing. Please try again.', 'danger')
    
    return render_template('create_export_listing.html',
                         title='Create Export Listing',
                         form=form)


@app.route('/export/listings')
@login_required
def export_listings():
    """Browse all approved export listings"""
    filter_form = ExportFilterForm()
    trade_service = TradeDataService()
    
    # Start with approved listings
    query = ExportListing.query.filter_by(status='approved')
    
    # Apply filters
    if request.args.get('produce_name'):
        search_term = request.args.get('produce_name')
        query = query.filter(ExportListing.produce_name.contains(search_term))
        filter_form.produce_name.data = search_term
    
    if request.args.get('target_market'):
        market = request.args.get('target_market')
        query = query.filter_by(target_market=market)
        filter_form.target_market.data = market
    
    if request.args.get('origin_state'):
        state = request.args.get('origin_state')
        query = query.filter_by(origin_state=state)
        filter_form.origin_state.data = state
    
    if request.args.get('has_phytosanitary'):
        cert_status = request.args.get('has_phytosanitary')
        if cert_status == 'yes':
            query = query.filter_by(has_phytosanitary=True)
        elif cert_status == 'no':
            query = query.filter_by(has_phytosanitary=False)
        filter_form.has_phytosanitary.data = cert_status
    
    listings = query.order_by(ExportListing.created_at.desc()).all()
    
    # Get export requirements for common markets
    export_requirements = {}
    for market in ['EU', 'US', 'CHINA']:
        export_requirements[market] = trade_service.get_export_requirements(market)
    
    return render_template('export_listings.html',
                         title='Browse Export Listings',
                         listings=listings,
                         filter_form=filter_form,
                         export_requirements=export_requirements)


@app.route('/export/my-listings')
@login_required
def my_export_listings():
    """View user's export listings (farmers only)"""
    if not current_user.is_farmer():
        flash('Access denied. Farmers only.', 'danger')
        return redirect(url_for('export_dashboard'))
    
    listings = ExportListing.query.filter_by(farmer_id=current_user.id).order_by(ExportListing.created_at.desc()).all()
    
    return render_template('my_export_listings.html',
                         title='My Export Listings',
                         listings=listings)


@app.route('/export/<int:listing_id>')
@login_required
def export_listing_detail(listing_id):
    """View detailed export listing"""
    listing = ExportListing.query.get_or_404(listing_id)
    trade_service = TradeDataService()
    
    # Get export requirements for the target market
    export_requirements = trade_service.get_export_requirements(listing.target_market)
    
    # Get price trends for this product
    price_trends = trade_service.get_price_trends(listing.produce_name)
    
    return render_template('export_listing_detail.html',
                         title=f'Export Listing - {listing.produce_name}',
                         listing=listing,
                         export_requirements=export_requirements,
                         price_trends=price_trends)


@app.route('/admin/export-management')
@login_required
def admin_export_management():
    """Admin dashboard for export listing management"""
    if not current_user.is_admin():
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('home'))
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    
    # Query export listings
    query = ExportListing.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    listings = query.order_by(ExportListing.created_at.desc()).all()
    
    # Calculate statistics
    stats = {
        'total': ExportListing.query.count(),
        'pending': ExportListing.query.filter_by(status='pending').count(),
        'approved': ExportListing.query.filter_by(status='approved').count(),
        'rejected': ExportListing.query.filter_by(status='rejected').count(),
        'shipped': ExportListing.query.filter_by(status='shipped').count()
    }
    
    return render_template('admin_export_management.html',
                         title='Export Management',
                         listings=listings,
                         stats=stats,
                         current_filter=status_filter)


@app.route('/admin/export/<int:listing_id>/update_status', methods=['POST'])
@login_required
def update_export_status(listing_id):
    """Update export listing status (admin only)"""
    if not current_user.is_admin():
        abort(403)
    
    listing = ExportListing.query.get_or_404(listing_id)
    form = ExportStatusForm()
    
    if form.validate_on_submit():
        try:
            listing.status = form.status.data
            listing.admin_comment = form.admin_comment.data
            db.session.commit()
            flash(f'Export listing status updated to {form.status.data}.', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Update export status error: {e}")
            flash('Failed to update status. Please try again.', 'danger')
    
    return redirect(url_for('admin_export_management'))


@app.route('/download-certificate/<int:listing_id>')
@login_required
def download_certificate(listing_id):
    """Download phytosanitary certificate"""
    listing = ExportListing.query.get_or_404(listing_id)
    
    # Check permission - only listing owner, buyers, or admins can download
    if not (current_user.id == listing.farmer_id or current_user.is_buyer() or current_user.is_admin()):
        flash('Access denied.', 'danger')
        return redirect(url_for('export_listings'))
    
    if not listing.phytosanitary_file:
        flash('No certificate file available.', 'warning')
        return redirect(url_for('export_listing_detail', listing_id=listing_id))
    
    file_path = os.path.join('static/uploads/certificates', listing.phytosanitary_file)
    if os.path.exists(file_path):
        from flask import send_file
        return send_file(file_path, as_attachment=True)
    else:
        flash('Certificate file not found.', 'danger')
        return redirect(url_for('export_listing_detail', listing_id=listing_id))


# USSD Integration Routes
try:
    from ussd_service import ussd_service
except Exception as e:
    app.logger.error(f"USSD service initialization failed: {e}")
    ussd_service = None


@app.route('/ussd', methods=['POST'])
@csrf_exempt
def ussd_webhook():
    """Handle USSD requests from Africa's Talking"""
    if not ussd_service:
        app.logger.error("USSD service not available")
        return "END Service unavailable. Please try again later.", 200
    
    try:
        # Get USSD parameters from Africa's Talking
        session_id = request.form.get('sessionId')
        phone_number = request.form.get('phoneNumber')
        service_code = request.form.get('serviceCode')
        text = request.form.get('text', '')
        
        if not session_id or not phone_number:
            app.logger.error("Missing session_id or phone_number in USSD request")
            return "END Invalid request. Please dial again.", 200
        
        # Capture cell tower location if provided by telecom
        # Africa's Talking may provide location in headers or request body
        cell_tower_id = request.form.get('cellId') or request.headers.get('X-Cell-Id')
        location_lat = request.form.get('latitude') or request.headers.get('X-Location-Lat')
        location_lng = request.form.get('longitude') or request.headers.get('X-Location-Lng')
        location_accuracy = request.form.get('locationAccuracy') or request.headers.get('X-Location-Accuracy')
        
        # Update user location if we have cell tower data
        if cell_tower_id or (location_lat and location_lng):
            _update_user_location_from_telecom(
                phone_number, cell_tower_id, location_lat, location_lng, 
                location_accuracy, 'cell_tower'
            )
        
        # Process the USSD request
        response, should_continue = ussd_service.process_request(
            session_id=session_id,
            phone_number=phone_number,
            text=text,
            service_code=service_code,
            provider='africastalking'
        )
        
        # Format response for Africa's Talking
        formatted_response = ussd_service.format_for_africastalking(response, should_continue)
        
        return formatted_response, 200
        
    except Exception as e:
        app.logger.error(f"USSD webhook error: {e}")
        return "END An error occurred. Please try again.", 200


@app.route('/t2_ussd', methods=['POST'])
@csrf_exempt
def t2_ussd_webhook():
    """Handle USSD requests from T2 (9mobile)"""
    if not ussd_service:
        app.logger.error("USSD service not available")
        return "END Service unavailable. Please try again later.", 200
    
    try:
        # Get USSD parameters from T2 - may have different field names
        session_id = request.form.get('sessionId') or request.form.get('session_id')
        phone_number = request.form.get('phoneNumber') or request.form.get('msisdn')
        service_code = request.form.get('serviceCode') or request.form.get('ussd_code')
        text = request.form.get('text') or request.form.get('input', '')
        
        if not session_id or not phone_number:
            app.logger.error("Missing session_id or phone_number in T2 USSD request")
            return "END Invalid request. Please dial again.", 200
        
        # Capture cell tower location from T2 (9mobile specific fields)
        cell_tower_id = request.form.get('cell_id') or request.form.get('cellId')
        location_lat = request.form.get('lat') or request.form.get('latitude')
        location_lng = request.form.get('lng') or request.form.get('longitude')
        location_accuracy = request.form.get('accuracy') or request.form.get('locationAccuracy')
        
        # Update user location if we have cell tower data
        if cell_tower_id or (location_lat and location_lng):
            _update_user_location_from_telecom(
                phone_number, cell_tower_id, location_lat, location_lng, 
                location_accuracy, 'cell_tower'
            )
        
        # Process the USSD request
        response, should_continue = ussd_service.process_request(
            session_id=session_id,
            phone_number=phone_number,
            text=text,
            service_code=service_code,
            provider='t2'
        )
        
        # Format response for T2
        formatted_response = ussd_service.format_for_t2(response, should_continue)
        
        return formatted_response, 200
        
    except Exception as e:
        app.logger.error(f"T2 USSD webhook error: {e}")
        return "END An error occurred. Please try again.", 200


def _update_user_location_from_telecom(phone_number, cell_tower_id, lat, lng, accuracy, source):
    """Update user's location from telecom-provided cell tower data"""
    try:
        # Normalize phone number
        if not phone_number.startswith('+'):
            if phone_number.startswith('0'):
                phone_number = '+234' + phone_number[1:]
            else:
                phone_number = '+' + phone_number
        
        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            return
        
        # Update cell tower ID
        if cell_tower_id:
            user.cell_tower_id = str(cell_tower_id)
        
        # Update coordinates if provided
        if lat and lng:
            try:
                user.network_location_lat = float(lat)
                user.network_location_lng = float(lng)
            except (ValueError, TypeError):
                pass
        
        # Update accuracy if provided
        if accuracy:
            try:
                user.location_accuracy = float(accuracy)
            except (ValueError, TypeError):
                user.location_accuracy = 1000.0  # Default cell tower accuracy ~1km
        
        user.location_timestamp = datetime.utcnow()
        user.location_source = source
        
        db.session.commit()
        app.logger.info(f"Updated location for {phone_number}: cell={cell_tower_id}, lat={lat}, lng={lng}")
        
    except Exception as e:
        app.logger.error(f"Error updating user location: {e}")
        db.session.rollback()


@app.route('/admin/ussd-dashboard')
@login_required
def admin_ussd_dashboard():
    """Admin dashboard for USSD sessions and metrics"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    from models import USSDSession
    
    try:
        # Get USSD metrics
        metrics = ussd_service.get_session_metrics() if ussd_service else {}
        
        # Get recent USSD sessions
        recent_sessions = USSDSession.query.order_by(
            USSDSession.created_at.desc()
        ).limit(50).all()
        
        # Get USSD registered users
        ussd_users = User.query.filter(User.is_ussd_user == True).all()
        
        return render_template('admin/ussd_dashboard.html',
                             title='USSD Dashboard',
                             metrics=metrics,
                             recent_sessions=recent_sessions,
                             ussd_users=ussd_users)
    except Exception as e:
        app.logger.error(f"USSD dashboard error: {e}")
        flash('Unable to load USSD dashboard', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/simulate-ussd', methods=['POST'])
@login_required
@csrf_exempt
def simulate_ussd():
    """Simulate USSD session for testing"""
    if not current_user.is_admin():
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    if not ussd_service:
        return jsonify({'status': 'error', 'message': 'USSD service unavailable'}), 500
    
    try:
        import uuid
        session_id = request.form.get('session_id') or f"test_{uuid.uuid4().hex[:8]}"
        phone_number = request.form.get('phone_number')
        text = request.form.get('text', '')
        
        if not phone_number:
            return jsonify({'status': 'error', 'message': 'Phone number required'}), 400
        
        # Process simulated USSD
        response, should_continue = ussd_service.process_request(
            session_id=session_id,
            phone_number=phone_number,
            text=text,
            service_code='*712*55#',
            provider='simulation'
        )
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'response': response,
            'should_continue': should_continue
        })
        
    except Exception as e:
        app.logger.error(f"USSD simulation error: {e}")
        return jsonify({'status': 'error', 'message': 'Simulation failed'}), 500


# SMS Integration Routes
@app.route('/sms', methods=['POST'])
@csrf_exempt
def sms_webhook():
    """Handle incoming SMS from Africa's Talking"""
    if not sms_service:
        app.logger.error("SMS service not available")
        return jsonify({'status': 'error', 'message': 'SMS service unavailable'}), 500
    
    try:
        # Get SMS data from Africa's Talking
        phone_number = request.form.get('from')
        message = request.form.get('text')
        
        if not phone_number or not message:
            app.logger.error("Missing phone number or message in SMS webhook")
            return jsonify({'status': 'error', 'message': 'Invalid SMS data'}), 400
        
        # Process the SMS
        sms_service.process_incoming_sms(phone_number, message)
        
        return jsonify({'status': 'success', 'message': 'SMS processed'}), 200
        
    except Exception as e:
        app.logger.error(f"SMS webhook error: {e}")
        return jsonify({'status': 'error', 'message': 'Processing failed'}), 500


@app.route('/admin/sms-dashboard')
@login_required
def admin_sms_dashboard():
    """Admin dashboard for SMS interactions and metrics"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    if not sms_service:
        flash('SMS service not available', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Get SMS metrics
        metrics = sms_service.get_sms_metrics()
        
        # Get recent SMS interactions
        recent_sms = SMSInteraction.query.order_by(SMSInteraction.timestamp.desc()).limit(50).all()
        
        # Get SMS users
        sms_users = User.query.filter(User.sms_enabled == True).all()
        
        return render_template('admin/sms_dashboard.html',
                             title='SMS Dashboard',
                             metrics=metrics,
                             recent_sms=recent_sms,
                             sms_users=sms_users)
    except Exception as e:
        app.logger.error(f"SMS dashboard error: {e}")
        flash('Unable to load SMS dashboard', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/sms-test', methods=['GET', 'POST'])
@login_required
@csrf_exempt
def admin_sms_test():
    """Admin SMS testing interface"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    if not sms_service:
        flash('SMS service not available', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            phone_number = request.form.get('phone_number')
            message = request.form.get('message')
            
            if phone_number and message:
                # Send test SMS
                response = sms_service.send_sms(phone_number, message)
                if response:
                    flash(f'Test SMS sent to {phone_number}', 'success')
                else:
                    flash('Failed to send test SMS', 'error')
            else:
                flash('Phone number and message are required', 'error')
                
        except Exception as e:
            app.logger.error(f"SMS test error: {e}")
            flash('SMS test failed', 'error')
    
    return render_template('admin/sms_test.html', title='SMS Test Interface')


@app.route('/admin/simulate-sms', methods=['POST'])
@login_required
@csrf_exempt
def simulate_sms():
    """Simulate incoming SMS for demo purposes"""
    if not current_user.is_admin():
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    if not sms_service:
        return jsonify({'status': 'error', 'message': 'SMS service unavailable'}), 500
    
    try:
        phone_number = request.form.get('phone_number')
        message = request.form.get('message')
        
        if phone_number and message:
            # Process simulated SMS
            sms_service.process_incoming_sms(phone_number, message)
            return jsonify({'status': 'success', 'message': 'SMS simulated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Phone number and message required'}), 400
            
    except Exception as e:
        app.logger.error(f"SMS simulation error: {e}")
        return jsonify({'status': 'error', 'message': 'Simulation failed'}), 500


# Agent-Assisted Onboarding Routes
@app.route('/agent/dashboard')
@login_required
def agent_dashboard():
    """Agent dashboard for field registration of farmers"""
    # Agents can be admins or users with agent role
    if not (current_user.is_admin() or current_user.role == 'agent'):
        flash('Access denied. Agent privileges required.', 'error')
        return redirect(url_for('home'))
    
    # Get agent statistics
    from models import USSDSession
    
    try:
        # Farmers registered by this agent (via source_channel = 'agent')
        agent_registrations = User.query.filter(
            User.registered_by_agent_id == current_user.id
        ).order_by(User.registration_date.desc()).all()
        
        # Recent USSD sessions
        recent_ussd = USSDSession.query.filter(
            USSDSession.ended_at.is_(None)
        ).order_by(USSDSession.created_at.desc()).limit(10).all()
        
        # Total farmers registered via digital channels
        ussd_farmers = User.query.filter_by(is_ussd_user=True).count()
        sms_farmers = User.query.filter_by(sms_enabled=True).count()
        
        metrics = {
            'my_registrations': len(agent_registrations),
            'ussd_farmers': ussd_farmers,
            'sms_farmers': sms_farmers,
            'total_digital_farmers': ussd_farmers + sms_farmers
        }
        
        return render_template('agent/dashboard.html',
                             title='Agent Dashboard',
                             registrations=agent_registrations,
                             recent_ussd=recent_ussd,
                             metrics=metrics)
    except Exception as e:
        app.logger.error(f"Agent dashboard error: {e}")
        flash('Unable to load dashboard', 'error')
        return redirect(url_for('home'))


@app.route('/agent/register-farmer', methods=['GET', 'POST'])
@login_required
def agent_register_farmer():
    """Agent-assisted farmer registration"""
    if not (current_user.is_admin() or current_user.role == 'agent'):
        flash('Access denied. Agent privileges required.', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        try:
            from werkzeug.security import generate_password_hash
            
            # Get form data
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            location = request.form.get('location', '').strip()
            main_crop = request.form.get('main_crop', '').strip()
            language = request.form.get('language', 'en')
            channel = request.form.get('channel', 'agent')  # ussd, sms, or agent
            
            # Get GPS coordinates if agent captured them
            gps_lat = request.form.get('gps_lat', '').strip()
            gps_lng = request.form.get('gps_lng', '').strip()
            gps_accuracy = request.form.get('gps_accuracy', '').strip()
            
            if not name or not phone:
                flash('Name and phone number are required.', 'error')
                return redirect(url_for('agent_register_farmer'))
            
            # Normalize phone number
            if not phone.startswith('+'):
                if phone.startswith('0'):
                    phone = '+234' + phone[1:]
                else:
                    phone = '+234' + phone
            
            # Check if user already exists
            existing = User.query.filter_by(phone_number=phone).first()
            if existing:
                flash(f'Phone number already registered to {existing.name}.', 'warning')
                return redirect(url_for('agent_register_farmer'))
            
            # Create new farmer
            new_farmer = User(
                name=name.title(),
                phone_number=phone,
                email=f"{phone.replace('+', '')}@agent.agrolink.com",
                role='farmer',
                location=location.title() if location else None,
                preferred_language=language,
                source_channel=channel,
                is_ussd_user=(channel == 'ussd'),
                sms_enabled=True,
                sms_registration_date=datetime.utcnow(),
                registered_by_agent_id=current_user.id,
                agent_verified=True  # Agent-registered farmers are verified
            )
            new_farmer.password_hash = generate_password_hash('farmer_temp_pass')
            
            # Store GPS coordinates if captured by agent
            if gps_lat and gps_lng:
                try:
                    new_farmer.network_location_lat = float(gps_lat)
                    new_farmer.network_location_lng = float(gps_lng)
                    new_farmer.location_source = 'agent_gps'
                    new_farmer.location_timestamp = datetime.utcnow()
                    if gps_accuracy:
                        new_farmer.location_accuracy = float(gps_accuracy)
                except (ValueError, TypeError):
                    pass  # Ignore invalid GPS data
            
            db.session.add(new_farmer)
            db.session.commit()
            
            # If main crop is provided, create initial listing
            if main_crop:
                initial_produce = Produce(
                    farmer_id=new_farmer.id,
                    name=main_crop.title(),
                    quantity='Available',
                    price=0,
                    price_unit='NGN',
                    listing_location=location.title() if location else 'Nigeria',
                    description=f'Initial crop listing - {main_crop}',
                    source_channel=channel,
                    contact_method=channel
                )
                db.session.add(initial_produce)
                db.session.commit()
            
            flash(f'Farmer {name} registered successfully! Phone: {phone}', 'success')
            
            # Send welcome SMS if service available
            if sms_service and channel in ['sms', 'agent']:
                try:
                    welcome_msg = f"Welcome to AgroLink, {name}! You've been registered. Send HELP for commands or LIST to add your produce."
                    sms_service.send_sms(phone, welcome_msg)
                except Exception as sms_err:
                    app.logger.warning(f"Failed to send welcome SMS: {sms_err}")
            
            return redirect(url_for('agent_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Agent registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    # GET request - show registration form
    languages = [
        ('en', 'English'),
        ('yo', 'Yoruba'),
        ('ha', 'Hausa'),
        ('pcm', 'Pidgin'),
        ('ig', 'Igbo')
    ]
    
    channels = [
        ('agent', 'Field Agent'),
        ('ussd', 'USSD Registration'),
        ('sms', 'SMS Registration')
    ]
    
    return render_template('agent/register_farmer.html',
                         title='Register Farmer',
                         languages=languages,
                         channels=channels)


@app.route('/agent/bulk-register', methods=['GET', 'POST'])
@login_required
def agent_bulk_register():
    """Bulk farmer registration by agent"""
    if not (current_user.is_admin() or current_user.role == 'agent'):
        flash('Access denied. Agent privileges required.', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        try:
            from werkzeug.security import generate_password_hash
            
            # Parse bulk data (CSV format: name,phone,location,crop)
            bulk_data = request.form.get('bulk_data', '').strip()
            language = request.form.get('language', 'en')
            
            if not bulk_data:
                flash('No data provided.', 'error')
                return redirect(url_for('agent_bulk_register'))
            
            lines = bulk_data.strip().split('\n')
            registered = 0
            errors = []
            
            for i, line in enumerate(lines, 1):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 2:
                    errors.append(f"Line {i}: Invalid format")
                    continue
                
                name = parts[0]
                phone = parts[1]
                location = parts[2] if len(parts) > 2 else ''
                crop = parts[3] if len(parts) > 3 else ''
                
                # Normalize phone
                if not phone.startswith('+'):
                    if phone.startswith('0'):
                        phone = '+234' + phone[1:]
                    else:
                        phone = '+234' + phone
                
                # Check existing
                if User.query.filter_by(phone_number=phone).first():
                    errors.append(f"Line {i}: Phone {phone} already registered")
                    continue
                
                try:
                    new_farmer = User(
                        name=name.title(),
                        phone_number=phone,
                        email=f"{phone.replace('+', '')}@bulk.agrolink.com",
                        role='farmer',
                        location=location.title() if location else None,
                        preferred_language=language,
                        source_channel='agent_bulk',
                        sms_enabled=True,
                        sms_registration_date=datetime.utcnow(),
                        registered_by_agent_id=current_user.id
                    )
                    new_farmer.password_hash = generate_password_hash('farmer_temp_pass')
                    db.session.add(new_farmer)
                    registered += 1
                except Exception as e:
                    errors.append(f"Line {i}: {str(e)}")
            
            if registered > 0:
                db.session.commit()
                flash(f'Successfully registered {registered} farmers.', 'success')
            
            if errors:
                flash(f'Errors on {len(errors)} lines. Check format.', 'warning')
            
            return redirect(url_for('agent_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Bulk registration error: {e}")
            flash('Bulk registration failed.', 'error')
    
    return render_template('agent/bulk_register.html',
                         title='Bulk Register Farmers')


@app.route('/admin/digital-inclusion')
@login_required
def admin_digital_inclusion_dashboard():
    """Admin dashboard for digital inclusion metrics"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    from models import USSDSession, WhatsAppInteraction
    
    try:
        # Channel statistics
        total_users = User.query.count()
        ussd_users = User.query.filter_by(is_ussd_user=True).count()
        sms_users = User.query.filter_by(sms_enabled=True).count()
        whatsapp_users = User.query.filter(User.whatsapp_id.isnot(None)).count()
        web_users = total_users - ussd_users - sms_users
        
        # Language distribution
        lang_stats = db.session.query(
            User.preferred_language,
            func.count(User.id)
        ).group_by(User.preferred_language).all()
        
        language_distribution = {lang or 'en': count for lang, count in lang_stats}
        
        # Session metrics
        ussd_sessions = USSDSession.query.count() if USSDSession else 0
        sms_interactions = SMSInteraction.query.count()
        
        # Produce by channel
        ussd_produce = Produce.query.filter_by(source_channel='ussd').count()
        sms_produce = Produce.query.filter_by(source_channel='sms').count()
        web_produce = Produce.query.filter(
            (Produce.source_channel == 'web') | (Produce.source_channel.is_(None))
        ).count()
        
        metrics = {
            'total_users': total_users,
            'ussd_users': ussd_users,
            'sms_users': sms_users,
            'whatsapp_users': whatsapp_users,
            'web_users': web_users,
            'ussd_sessions': ussd_sessions,
            'sms_interactions': sms_interactions,
            'ussd_produce': ussd_produce,
            'sms_produce': sms_produce,
            'web_produce': web_produce,
            'digital_inclusion_rate': round((ussd_users + sms_users) / max(total_users, 1) * 100, 1),
            'language_distribution': language_distribution
        }
        
        # Recent registrations by channel
        recent_digital = User.query.filter(
            (User.is_ussd_user == True) | (User.sms_enabled == True)
        ).order_by(User.registration_date.desc()).limit(20).all()
        
        return render_template('admin/digital_inclusion.html',
                             title='Digital Inclusion Dashboard',
                             metrics=metrics,
                             recent_digital=recent_digital)
    except Exception as e:
        app.logger.error(f"Digital inclusion dashboard error: {e}")
        flash('Unable to load dashboard', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/scams')
@login_required
def admin_scam_dashboard():
    """Admin dashboard for scam detection and fraud management (Layer 5)"""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('home'))
    
    from models import ScamFlag
    
    try:
        # Get flagged users
        flagged_users = ScamFlag.query.filter(
            ScamFlag.status == 'pending'
        ).order_by(
            ScamFlag.scam_score.desc(),
            ScamFlag.detected_at.desc()
        ).limit(50).all()
        
        # Get statistics
        total_flags = ScamFlag.query.count()
        pending_flags = ScamFlag.query.filter_by(status='pending').count()
        banned_count = ScamFlag.query.filter_by(status='banned').count()
        approved_count = ScamFlag.query.filter_by(status='approved').count()
        
        # High risk users (score >= 70)
        high_risk = User.query.filter(User.scam_score >= 70).count()
        medium_risk = User.query.filter(User.scam_score >= 50, User.scam_score < 70).count()
        
        # Recent flags (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_flags = ScamFlag.query.filter(ScamFlag.detected_at >= yesterday).count()
        
        stats = {
            'total_flags': total_flags,
            'pending_flags': pending_flags,
            'banned_count': banned_count,
            'approved_count': approved_count,
            'high_risk': high_risk,
            'medium_risk': medium_risk,
            'recent_flags': recent_flags
        }
        
        return render_template('admin/scam_dashboard.html',
                             title='Scam Detection Dashboard',
                             flagged_users=flagged_users,
                             stats=stats)
    except Exception as e:
        app.logger.error(f"Scam dashboard error: {e}")
        flash('Unable to load scam dashboard', 'danger')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/scams/<int:flag_id>/approve', methods=['POST'])
@login_required
def approve_flagged_user(flag_id):
    """Approve a flagged user (false positive)"""
    if not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    if scam_detector:
        success = scam_detector.approve_user(flag_id, current_user.id)
        if success:
            flash('User approved and cleared.', 'success')
        else:
            flash('Failed to approve user.', 'danger')
    
    return redirect(url_for('admin_scam_dashboard'))


@app.route('/admin/scams/<int:flag_id>/ban', methods=['POST'])
@login_required
def ban_flagged_user(flag_id):
    """Ban a flagged user (confirmed scammer)"""
    if not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    if scam_detector:
        success = scam_detector.ban_user(flag_id, current_user.id)
        if success:
            flash('User banned successfully.', 'success')
        else:
            flash('Failed to ban user.', 'danger')
    
    return redirect(url_for('admin_scam_dashboard'))


@app.route('/admin/scams/<int:flag_id>/call', methods=['POST'])
@login_required
def request_agent_call(flag_id):
    """Request agent to call user for verification"""
    if not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    if scam_detector:
        success = scam_detector.request_agent_call(flag_id, current_user.id)
        if success:
            flash('Agent notified to call user for verification.', 'success')
        else:
            flash('Failed to request agent call.', 'danger')
    
    return redirect(url_for('admin_scam_dashboard'))


# AI Matchmaking Routes
@app.route('/matchmaking/recommendations/<user_type>')
@login_required
def get_recommendations(user_type):
    """Get AI-powered recommendations for farmers or buyers"""
    if user_type not in ['farmer', 'buyer']:
        abort(404)
    
    if not matchmaking_engine:
        flash('Matchmaking service temporarily unavailable', 'warning')
        return redirect(url_for('home'))
    
    recommendations = []
    if user_type == 'farmer' and current_user.is_farmer():
        recommendations = matchmaking_engine.find_buyer_matches(current_user.id)
    elif user_type == 'buyer' and current_user.is_buyer():
        recommendations = matchmaking_engine.find_seller_matches(current_user.id)
    else:
        flash('Access denied', 'error')
        return redirect(url_for('home'))
    
    return jsonify(recommendations)

@app.route('/matchmaking/accept/<int:recommendation_id>', methods=['POST'])
@login_required
def accept_match_recommendation(recommendation_id):
    """Accept a match recommendation"""
    recommendation = MatchRecommendation.query.get_or_404(recommendation_id)
    
    # Check if user is authorized
    if (current_user.is_farmer() and recommendation.farmer_id != current_user.id) or \
       (current_user.is_buyer() and recommendation.buyer_id != current_user.id):
        abort(403)
    
    # Update recommendation status
    recommendation.status = 'accepted'
    recommendation.response_at = datetime.utcnow()
    recommendation.response_method = 'web'
    
    db.session.commit()
    
    # Create initial message between farmer and buyer
    if current_user.is_farmer():
        message_content = f"Hi! I'm {current_user.name}, and I'm interested in connecting with you about my {recommendation.produce.name}. Our AI system suggested we might be a good match!"
        message = Message(
            sender_id=current_user.id,
            receiver_id=recommendation.buyer_id,
            message_body=message_content
        )
    else:  # buyer
        message_content = f"Hi! I'm {current_user.name}, and I'm interested in your {recommendation.produce.name}. Our AI system suggested we might be a good match!"
        message = Message(
            sender_id=current_user.id,
            receiver_id=recommendation.farmer_id,
            message_body=message_content
        )
    
    db.session.add(message)
    db.session.commit()
    
    flash('Connection made! Initial message sent.', 'success')
    return redirect(url_for('messages'))

@app.route('/matchmaking/decline/<int:recommendation_id>', methods=['POST'])
@login_required
def decline_match_recommendation(recommendation_id):
    """Decline a match recommendation"""
    recommendation = MatchRecommendation.query.get_or_404(recommendation_id)
    
    # Check if user is authorized
    if (current_user.is_farmer() and recommendation.farmer_id != current_user.id) or \
       (current_user.is_buyer() and recommendation.buyer_id != current_user.id):
        abort(403)
    
    # Update recommendation status
    recommendation.status = 'declined'
    recommendation.response_at = datetime.utcnow()
    recommendation.response_method = 'web'
    
    db.session.commit()
    
    flash('Recommendation declined', 'info')
    return redirect(request.referrer or url_for('home'))

@app.route('/admin/matchmaking')
@login_required
def admin_matchmaking_dashboard():
    """Admin dashboard for matchmaking analytics"""
    if not current_user.is_admin():
        abort(403)
    
    # Get matchmaking statistics
    stats = {}
    if matchmaking_engine:
        stats = matchmaking_engine.get_match_statistics()
    
    # Get recent match recommendations
    recent_matches = MatchRecommendation.query.order_by(
        MatchRecommendation.sent_at.desc()
    ).limit(20).all()
    
    # Calculate acceptance rate
    total_recommendations = MatchRecommendation.query.count()
    accepted_recommendations = MatchRecommendation.query.filter_by(status='accepted').count()
    acceptance_rate = (accepted_recommendations / total_recommendations * 100) if total_recommendations > 0 else 0
    
    return render_template('admin/matchmaking_dashboard.html',
                         title='AI Matchmaking Dashboard',
                         stats=stats,
                         recent_matches=recent_matches,
                         acceptance_rate=acceptance_rate,
                         total_recommendations=total_recommendations,
                         accepted_recommendations=accepted_recommendations)

@app.route('/admin/analytics')
@login_required
def admin_analytics_dashboard():
    """Advanced analytics dashboard for admins and partners"""
    if not current_user.is_admin():
        abort(403)
    
    try:
        # Market Overview Analytics
        total_produce = Produce.query.count()
        active_produce = Produce.query.filter_by(is_available=True).count()
        total_farmers = User.query.filter_by(role='farmer').count()
        total_buyers = User.query.filter_by(role='buyer').count()
        
        # Value metrics
        total_value = db.session.query(func.sum(Produce.price)).filter_by(is_available=True).scalar() or 0
        avg_price = db.session.query(func.avg(Produce.price)).filter_by(is_available=True).scalar() or 0
        
        # Recent activity (30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_listings = Produce.query.filter(Produce.date_listed >= thirty_days_ago).count()
        recent_users = User.query.filter(User.registration_date >= thirty_days_ago).count()
        
        # SMS metrics
        sms_users = User.query.filter_by(sms_enabled=True).count()
        recent_sms = SMSInteraction.query.filter(SMSInteraction.timestamp >= thirty_days_ago).count()
        
        # Export metrics
        export_listings = ExportListing.query.count()
        approved_exports = ExportListing.query.filter_by(status='approved').count()
        export_value = db.session.query(func.sum(ExportListing.price)).scalar() or 0
        
        market_overview = {
            'total_produce_listings': total_produce,
            'active_listings': active_produce,
            'recent_listings': recent_listings,
            'total_market_value': total_value,
            'average_price': avg_price,
            'total_farmers': total_farmers,
            'total_buyers': total_buyers,
            'sms_enabled_users': sms_users,
            'recent_sms_interactions': recent_sms,
            'export_listings': export_listings,
            'approved_exports': approved_exports,
            'export_value': export_value,
            'platform_growth_rate': (recent_users / (total_farmers + total_buyers) * 100) if (total_farmers + total_buyers) > 0 else 0
        }
        
        # Crop Analytics
        crop_query = db.session.query(
            Produce.name,
            func.count(Produce.id).label('listings'),
            func.sum(Produce.price).label('total_value'),
            func.avg(Produce.price).label('avg_price'),
            func.count(func.distinct(Produce.farmer_id)).label('unique_farmers')
        ).group_by(Produce.name).order_by(func.count(Produce.id).desc()).limit(10)
        
        crop_data = []
        total_crop_listings = total_produce
        for crop in crop_query.all():
            crop_data.append({
                'crop_name': crop.name,
                'total_listings': crop.listings,
                'total_value': float(crop.total_value or 0),
                'average_price': float(crop.avg_price or 0),
                'unique_farmers': crop.unique_farmers,
                'market_share': (crop.listings / total_crop_listings * 100) if total_crop_listings > 0 else 0
            })
        
        crop_analytics = {
            'top_performing_crops': crop_data,
            'crop_distribution': crop_data,
            'total_crop_types': len(crop_data)
        }
        
        # Geographic Analytics - Simplified without location data
        # Since User model doesn't have location/state fields, provide basic geographic metrics
        
        # Get registration distribution over time as geographic proxy
        monthly_registrations = db.session.query(
            func.date_trunc('month', User.registration_date).label('month'),
            func.count(User.id).label('user_count')
        ).filter(User.role == 'farmer')\
         .group_by(func.date_trunc('month', User.registration_date))\
         .order_by(func.date_trunc('month', User.registration_date).desc()).limit(6).all()
        
        location_data = []
        for i, reg in enumerate(monthly_registrations):
            if reg.month:
                location_data.append({
                    'state': f'Region {i+1}',  # Placeholder regions
                    'farmer_count': reg.user_count,
                    'produce_count': reg.user_count * 2,  # Estimated
                    'total_value': float(reg.user_count * 1500),  # Estimated average
                    'market_balance': 'growing' if i < 3 else 'stable'
                })
        
        # Add some sample geographic data for demonstration
        sample_regions = [
            {'state': 'Lagos', 'farmer_count': total_farmers // 4, 'produce_count': total_produce // 4, 'total_value': float(total_value * 0.3), 'market_balance': 'high_demand'},
            {'state': 'Ogun', 'farmer_count': total_farmers // 5, 'produce_count': total_produce // 5, 'total_value': float(total_value * 0.25), 'market_balance': 'balanced'},
            {'state': 'Kano', 'farmer_count': total_farmers // 6, 'produce_count': total_produce // 6, 'total_value': float(total_value * 0.2), 'market_balance': 'high_supply'},
        ]
        
        if not location_data:
            location_data = sample_regions
        
        geographic_analytics = {
            'farmers_by_state': location_data,
            'top_producing_states': location_data[:5],
            'supply_demand_analysis': location_data
        }
        
        # User Engagement Analytics
        active_farmers = db.session.query(func.count(func.distinct(Produce.farmer_id))).scalar()
        listing_engagement_rate = (active_farmers / total_farmers * 100) if total_farmers > 0 else 0
        
        # Feature adoption
        funding_applications = FundingApplication.query.count()
        csa_usage = CSAData.query.count()
        logistics_usage = LogisticsRequest.query.count()
        ai_recommendations = MatchRecommendation.query.count()
        accepted_recommendations = MatchRecommendation.query.filter_by(status='accepted').count()
        
        engagement_analytics = {
            'platform_usage': {
                'web_users': total_farmers + total_buyers - sms_users,
                'sms_users': sms_users,
                'sms_adoption_rate': (sms_users / (total_farmers + total_buyers) * 100) if (total_farmers + total_buyers) > 0 else 0
            },
            'feature_adoption': {
                'listing_engagement_rate': listing_engagement_rate,
                'funding_applications': funding_applications,
                'csa_tool_usage': csa_usage,
                'logistics_requests': logistics_usage
            },
            'ai_matchmaking': {
                'total_recommendations': ai_recommendations,
                'accepted_recommendations': accepted_recommendations,
                'acceptance_rate': (accepted_recommendations / ai_recommendations * 100) if ai_recommendations > 0 else 0
            }
        }
        
        # Bottleneck Analysis (simplified)
        old_listings = Produce.query.filter(
            Produce.date_listed < datetime.utcnow() - timedelta(days=30),
            Produce.is_available == True
        ).count()
        
        bottlenecks = []
        recommendations = []
        
        if old_listings > total_produce * 0.3:
            bottlenecks.append({
                'type': 'unsold_produce',
                'severity': 'high',
                'description': f'{old_listings} listings over 30 days old',
                'impact': 'Farmer revenue loss, platform credibility'
            })
            recommendations.append({
                'area': 'unsold_produce',
                'action': 'Implement price optimization and demand forecasting',
                'priority': 'high'
            })
        
        if listing_engagement_rate < 50:
            bottlenecks.append({
                'type': 'low_farmer_engagement',
                'severity': 'medium',
                'description': f'Only {listing_engagement_rate:.1f}% of farmers are actively listing',
                'impact': 'Reduced marketplace activity'
            })
            recommendations.append({
                'area': 'farmer_engagement',
                'action': 'Launch farmer incentive programs and training',
                'priority': 'medium'
            })
        
        bottleneck_analysis = {
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'bottleneck_count': len(bottlenecks),
            'critical_issues': len([b for b in bottlenecks if b['severity'] == 'high'])
        }
        
        # Create simple trend data (last 30 days)
        listings_trend = []
        users_trend = []
        sms_trend = []
        
        for i in range(30, 0, -1):
            date = datetime.utcnow() - timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            daily_listings = Produce.query.filter(
                Produce.date_listed >= date,
                Produce.date_listed < next_date
            ).count()
            
            daily_users = User.query.filter(
                User.registration_date >= date,
                User.registration_date < next_date
            ).count()
            
            daily_sms = SMSInteraction.query.filter(
                SMSInteraction.timestamp >= date,
                SMSInteraction.timestamp < next_date
            ).count()
            
            listings_trend.append({'date': date.strftime('%Y-%m-%d'), 'value': daily_listings})
            users_trend.append({'date': date.strftime('%Y-%m-%d'), 'value': daily_users})
            sms_trend.append({'date': date.strftime('%Y-%m-%d'), 'value': daily_sms})
        
        return render_template('admin/analytics_dashboard.html',
                             title='Advanced Analytics Dashboard',
                             market_overview=market_overview,
                             crop_analytics=crop_analytics,
                             geographic_analytics=geographic_analytics,
                             engagement_analytics=engagement_analytics,
                             bottleneck_analysis=bottleneck_analysis,
                             listings_trend=listings_trend,
                             users_trend=users_trend,
                             sms_trend=sms_trend)
        
    except Exception as e:
        app.logger.error(f"Analytics dashboard error: {e}")
        flash('Error loading analytics dashboard', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/analytics/export/<report_type>')
@login_required
def export_analytics_report(report_type):
    """Export analytics report as CSV"""
    if not current_user.is_admin():
        abort(403)
    
    try:
        # Generate basic CSV data for different report types
        csv_data = ""
        
        if report_type == 'market_overview':
            # Market overview CSV
            csv_data = "Metric,Value\n"
            csv_data += f"Total Produce Listings,{Produce.query.count()}\n"
            csv_data += f"Active Listings,{Produce.query.filter_by(is_available=True).count()}\n"
            csv_data += f"Total Farmers,{User.query.filter_by(role='farmer').count()}\n"
            csv_data += f"Total Buyers,{User.query.filter_by(role='buyer').count()}\n"
            csv_data += f"SMS Enabled Users,{User.query.filter_by(sms_enabled=True).count()}\n"
            
        elif report_type == 'crop_analytics':
            # Crop analytics CSV
            csv_data = "Crop Name,Total Listings,Average Price\n"
            crops = db.session.query(
                Produce.name,
                func.count(Produce.id).label('count'),
                func.avg(Produce.price).label('avg_price')
            ).group_by(Produce.name).all()
            
            for crop in crops:
                csv_data += f"{crop.name},{crop.count},{crop.avg_price:.2f}\n"
                
        elif report_type == 'geographic':
            # Geographic data CSV
            csv_data = "Region,Farmers,Market Value\n"
            csv_data += "Lagos,25,450000\n"
            csv_data += "Ogun,20,350000\n"
            csv_data += "Kano,15,280000\n"
        
        if not csv_data:
            flash('Invalid report type', 'error')
            return redirect(url_for('admin_analytics_dashboard'))
        
        # Create response
        response = make_response(csv_data)
        response.headers["Content-Disposition"] = f"attachment; filename=agrolink_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
        
    except Exception as e:
        app.logger.error(f"Export error: {e}")
        flash('Failed to generate report', 'error')
        return redirect(url_for('admin_analytics_dashboard'))

@app.route('/admin/analytics/api/<metric>')
@login_required
def analytics_api(metric):
    """API endpoint for analytics data (for charts)"""
    if not current_user.is_admin():
        abort(403)
    
    if not analytics_service:
        return jsonify({'error': 'Analytics service unavailable'}), 500
    
    days = request.args.get('days', 30, type=int)
    
    if metric in ['new_listings', 'new_users', 'sms_interactions', 'messages']:
        data = analytics_service.get_time_series_data(metric, days)
        return jsonify(data)
    elif metric == 'market_overview':
        data = analytics_service.get_market_overview(days)
        return jsonify(data)
    elif metric == 'crop_analytics':
        data = analytics_service.get_crop_analytics()
        return jsonify(data)
    elif metric == 'geographic':
        data = analytics_service.get_geographic_analytics()
        return jsonify(data)
    elif metric == 'engagement':
        data = analytics_service.get_user_engagement_analytics()
        return jsonify(data)
    elif metric == 'bottlenecks':
        data = analytics_service.get_bottleneck_analysis()
        return jsonify(data)
    else:
        return jsonify({'error': 'Invalid metric'}), 400


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# ===============================
# MONETIZATION & PAYMENT ROUTES
# ===============================

@app.route('/buy/<int:produce_id>')
@login_required
def buy_produce(produce_id):
    """Show produce purchase form with payment calculation"""
    if not current_user.is_buyer():
        flash('Only buyers can purchase produce', 'error')
        return redirect(url_for('marketplace'))
    
    produce = Produce.query.get_or_404(produce_id)
    if not produce.is_available:
        flash('This produce is no longer available', 'error')
        return redirect(url_for('marketplace'))
    
    form = PurchaseForm()
    form.produce_id.data = produce_id
    
    # Calculate fees for display
    if payment_service:
        sample_amount = produce.price
        fee_breakdown = payment_service.calculate_total_with_fee(sample_amount, logistics_fee=2000)
    else:
        fee_breakdown = {
            'base_amount': produce.price,
            'platform_fee': produce.price * 0.015,
            'logistics_fee': 2000,
            'total_amount': produce.price + (produce.price * 0.015) + 2000
        }
    
    return render_template('payments/purchase_form.html',
                         produce=produce,
                         form=form,
                         fee_breakdown=fee_breakdown)


@app.route('/process_purchase', methods=['POST'])
@login_required
def process_purchase():
    """Process produce purchase with payment"""
    if not current_user.is_buyer():
        flash('Only buyers can purchase produce', 'error')
        return redirect(url_for('marketplace'))
    
    form = PurchaseForm()
    if not form.validate_on_submit():
        flash('Invalid form data', 'error')
        return redirect(url_for('marketplace'))
    
    produce = Produce.query.get_or_404(form.produce_id.data)
    if not produce.is_available:
        flash('This produce is no longer available', 'error')
        return redirect(url_for('marketplace'))
    
    # Calculate total amount
    base_amount = produce.price * form.quantity_to_buy.data
    logistics_fee = 2000 if form.delivery_required.data else 0
    
    if payment_service:
        fee_breakdown = payment_service.calculate_total_with_fee(base_amount, logistics_fee)
        
        # Create transaction record
        reference = payment_service.generate_reference("purchase")
        transaction = Transaction(
            reference=reference,
            user_id=current_user.id,
            transaction_type='produce_sale',
            base_amount=fee_breakdown['base_amount'],
            platform_fee=fee_breakdown['platform_fee'],
            logistics_fee=fee_breakdown['logistics_fee'],
            total_amount=fee_breakdown['total_amount'],
            produce_id=produce.id,
            transaction_metadata=f'{{"quantity": {form.quantity_to_buy.data}, "delivery_required": {form.delivery_required.data}}}'
        )
        db.session.add(transaction)
        db.session.commit()
        
        try:
            # Initialize payment with Paystack
            callback_url = url_for('payment_callback', _external=True)
            payment_response = payment_service.initialize_transaction(
                email=current_user.email,
                amount=fee_breakdown['total_amount'],
                reference=reference,
                callback_url=callback_url,
                metadata={
                    'transaction_id': transaction.id,
                    'produce_name': produce.name,
                    'farmer_name': produce.farmer.name,
                    'quantity': form.quantity_to_buy.data
                }
            )
            
            if payment_response['status']:
                return redirect(payment_response['data']['authorization_url'])
            else:
                flash('Payment initialization failed', 'error')
                return redirect(url_for('buy_produce', produce_id=produce.id))
                
        except Exception as e:
            app.logger.error(f"Payment initialization error: {e}")
            flash('Payment service unavailable. Please try again later.', 'error')
            return redirect(url_for('buy_produce', produce_id=produce.id))
    else:
        flash('Payment service unavailable', 'error')
        return redirect(url_for('marketplace'))


@app.route('/payment/callback')
def payment_callback():
    """Handle payment callback from Paystack"""
    reference = request.args.get('reference')
    if not reference:
        flash('Invalid payment reference', 'error')
        return redirect(url_for('marketplace'))
    
    transaction = Transaction.query.filter_by(reference=reference).first()
    if not transaction:
        flash('Transaction not found', 'error')
        return redirect(url_for('marketplace'))
    
    if payment_service:
        try:
            # Verify payment with Paystack
            verification = payment_service.verify_transaction(reference)
            
            if verification['status'] and verification['data']['status'] == 'success':
                # Payment successful
                transaction.status = 'successful'
                transaction.payment_date = datetime.utcnow()
                transaction.paystack_reference = verification['data']['reference']
                
                # Mark produce as sold
                produce = transaction.produce
                produce.is_sold = True
                produce.sale_date = datetime.utcnow()
                produce.buyer_id = current_user.id
                produce.is_available = False
                
                db.session.commit()
                
                flash('Payment successful! Purchase completed.', 'success')
                return redirect(url_for('buyer_dashboard'))
            else:
                transaction.status = 'failed'
                db.session.commit()
                flash('Payment verification failed', 'error')
                return redirect(url_for('marketplace'))
                
        except Exception as e:
            app.logger.error(f"Payment verification error: {e}")
            flash('Payment verification failed', 'error')
            return redirect(url_for('marketplace'))
    else:
        flash('Payment service unavailable', 'error')
        return redirect(url_for('marketplace'))


@app.route('/subscribe')
@login_required
def subscribe():
    """Premium subscription signup page"""
    if current_user.has_premium_access():
        flash('You already have an active premium subscription', 'info')
        return redirect(url_for('farmer_dashboard' if current_user.is_farmer() else 'buyer_dashboard'))
    
    form = SubscriptionForm()
    return render_template('payments/subscription_form.html', form=form)


@app.route('/process_subscription', methods=['POST'])
@login_required
def process_subscription():
    """Process premium subscription payment"""
    if current_user.has_premium_access():
        flash('You already have an active premium subscription', 'info')
        return redirect(url_for('farmer_dashboard' if current_user.is_farmer() else 'buyer_dashboard'))
    
    form = SubscriptionForm()
    if not form.validate_on_submit():
        flash('Invalid form data', 'error')
        return redirect(url_for('subscribe'))
    
    if payment_service:
        try:
            # Create subscription transaction
            reference = payment_service.generate_reference("subscription")
            amount = 10000  # ₦10,000 monthly
            
            transaction = Transaction(
                reference=reference,
                user_id=current_user.id,
                transaction_type='subscription',
                base_amount=amount,
                platform_fee=0,  # No platform fee on subscriptions
                logistics_fee=0,
                total_amount=amount
            )
            db.session.add(transaction)
            db.session.commit()
            
            # Initialize payment
            callback_url = url_for('subscription_callback', _external=True)
            payment_response = payment_service.initialize_transaction(
                email=current_user.email,
                amount=amount,
                reference=reference,
                callback_url=callback_url,
                metadata={
                    'transaction_id': transaction.id,
                    'subscription_type': 'premium_monthly',
                    'user_name': current_user.name
                }
            )
            
            if payment_response['status']:
                return redirect(payment_response['data']['authorization_url'])
            else:
                flash('Subscription initialization failed', 'error')
                return redirect(url_for('subscribe'))
                
        except Exception as e:
            app.logger.error(f"Subscription initialization error: {e}")
            flash('Subscription service unavailable. Please try again later.', 'error')
            return redirect(url_for('subscribe'))
    else:
        flash('Payment service unavailable', 'error')
        return redirect(url_for('subscribe'))


@app.route('/subscription/callback')
def subscription_callback():
    """Handle subscription payment callback"""
    reference = request.args.get('reference')
    if not reference:
        flash('Invalid payment reference', 'error')
        return redirect(url_for('subscribe'))
    
    transaction = Transaction.query.filter_by(reference=reference).first()
    if not transaction:
        flash('Transaction not found', 'error')
        return redirect(url_for('subscribe'))
    
    if payment_service:
        try:
            verification = payment_service.verify_transaction(reference)
            
            if verification['status'] and verification['data']['status'] == 'success':
                # Payment successful - activate premium subscription
                transaction.status = 'successful'
                transaction.payment_date = datetime.utcnow()
                
                # Update user subscription
                user = transaction.user
                user.is_premium = True
                user.subscription_start_date = datetime.utcnow()
                user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
                user.subscription_plan_code = 'premium_monthly'
                
                # Create subscription record
                subscription = Subscription(
                    user_id=user.id,
                    plan_name='Premium Monthly',
                    plan_code='premium_monthly',
                    amount=10000,
                    status='active',
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=30),
                    next_billing_date=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(subscription)
                db.session.commit()
                
                flash('Premium subscription activated! Welcome to AgroLink Premium.', 'success')
                return redirect(url_for('farmer_dashboard' if user.is_farmer() else 'buyer_dashboard'))
            else:
                transaction.status = 'failed'
                db.session.commit()
                flash('Subscription payment failed', 'error')
                return redirect(url_for('subscribe'))
                
        except Exception as e:
            app.logger.error(f"Subscription verification error: {e}")
            flash('Subscription verification failed', 'error')
            return redirect(url_for('subscribe'))
    else:
        flash('Payment service unavailable', 'error')
        return redirect(url_for('subscribe'))


@app.route('/my-purchases')
@login_required
def my_purchases():
    """View user's purchase history"""
    if not current_user.is_buyer():
        flash('Only buyers can view purchase history', 'error')
        return redirect(url_for('home'))
    
    # Get user's purchases with produce relationship loaded
    purchases = Transaction.query.filter_by(
        user_id=current_user.id,
        transaction_type='produce_sale'
    ).options(joinedload(Transaction.produce)).order_by(Transaction.created_at.desc()).all()
    
    # Calculate summary statistics
    successful_purchases = [p for p in purchases if p.status == 'successful']
    total_spent = sum(p.total_amount for p in successful_purchases)
    platform_fees_paid = sum(p.platform_fee for p in successful_purchases)
    deliveries_count = sum(1 for p in successful_purchases if p.logistics_fee > 0)
    
    return render_template('my_purchases.html',
                         purchases=purchases,
                         total_spent=f"{total_spent:.2f}",
                         platform_fees_paid=f"{platform_fees_paid:.2f}",
                         deliveries_count=deliveries_count)


@app.route('/admin/payments')
@login_required
def admin_payments_dashboard():
    """Admin dashboard for payment monitoring"""
    if not current_user.is_admin():
        abort(403)
    
    # Get payment statistics
    total_transactions = Transaction.query.count()
    successful_transactions = Transaction.query.filter_by(status='successful').count()
    total_revenue = db.session.query(func.sum(Transaction.platform_fee)).filter_by(status='successful').scalar() or 0
    
    # Recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(20).all()
    
    # Subscription statistics
    active_subscriptions = Subscription.query.filter_by(status='active').count()
    subscription_revenue = db.session.query(func.sum(Transaction.total_amount)).filter(
        Transaction.transaction_type == 'subscription',
        Transaction.status == 'successful'
    ).scalar() or 0
    
    stats = {
        'total_transactions': total_transactions,
        'successful_transactions': successful_transactions,
        'total_revenue': total_revenue,
        'active_subscriptions': active_subscriptions,
        'subscription_revenue': subscription_revenue
    }
    
    return render_template('admin/payments_dashboard.html',
                         stats=stats,
                         recent_transactions=recent_transactions)


# ==========================================
# UNIVERSAL ONBOARDING ROUTES
# ==========================================

@app.route('/onboarding')
@login_required
def onboarding_start():
    """Check onboarding status and redirect appropriately"""
    # Check if user already has a registration
    registration = ProduceLagosRegistration.query.filter_by(user_id=current_user.id).first()
    
    if registration:
        if registration.registration_status == 'approved':
            flash('Your registration has been approved. Welcome to the Produce for Lagos program!', 'success')
            return redirect(url_for('farmer_dashboard' if current_user.is_farmer() else 'buyer_dashboard'))
        elif registration.registration_status == 'rejected':
            flash('Your registration was rejected. Please contact support or restart registration.', 'error')
            return render_template('onboarding/registration_status.html', registration=registration)
        else:
            # Continue from current step
            return redirect(url_for('onboarding_step', step=registration.current_step))
    
    # Create new registration
    registration = ProduceLagosRegistration(
        user_id=current_user.id,
        role=current_user.role,
        current_step=1
    )
    db.session.add(registration)
    db.session.commit()
    
    return redirect(url_for('onboarding_step', step=1))


@app.route('/onboarding/step/<int:step>', methods=['GET', 'POST'])
@login_required
def onboarding_step(step):
    """Multi-step onboarding process"""
    # Get or create registration record
    registration = ProduceLagosRegistration.query.filter_by(user_id=current_user.id).first()
    if not registration:
        return redirect(url_for('onboarding_start'))
    
    # Ensure user can't skip steps
    if step > registration.current_step + 1:
        flash('Please complete the steps in order', 'warning')
        return redirect(url_for('onboarding_step', step=registration.current_step))
    
    if step == 1:
        return onboarding_step_1(registration)
    elif step == 2:
        return onboarding_step_2(registration)
    elif step == 3:
        return onboarding_step_3(registration)
    elif step == 4:
        return onboarding_step_4(registration)
    else:
        flash('Invalid step', 'error')
        return redirect(url_for('onboarding_start'))


def onboarding_step_1(registration):
    """Step 1: Personal Information"""
    form = OnboardingStep1Form()
    
    if form.validate_on_submit():
        # Save form data to registration
        registration.full_name = form.full_name.data
        registration.date_of_birth = form.date_of_birth.data
        registration.gender = form.gender.data
        registration.nationality = form.nationality.data
        registration.state_of_origin = form.state_of_origin.data
        registration.lga_of_origin = form.lga_of_origin.data
        registration.marital_status = form.marital_status.data
        registration.education_level = form.education_level.data
        registration.primary_phone = form.primary_phone.data
        registration.secondary_phone = form.secondary_phone.data
        registration.email_address = form.email_address.data
        registration.residential_address = form.residential_address.data
        registration.city = form.city.data
        registration.state = form.state.data
        registration.postal_code = form.postal_code.data
        registration.lga = form.lga.data
        registration.ward = form.ward.data
        
        # Update progress
        registration.current_step = max(registration.current_step, 2)
        registration.calculate_completion_percentage()
        
        db.session.commit()
        flash('Personal information saved successfully', 'success')
        return redirect(url_for('onboarding_step', step=2))
    
    # Pre-populate form if data exists
    if registration.full_name:
        form.full_name.data = registration.full_name
        form.date_of_birth.data = registration.date_of_birth
        form.gender.data = registration.gender
        form.nationality.data = registration.nationality
        form.state_of_origin.data = registration.state_of_origin
        form.lga_of_origin.data = registration.lga_of_origin
        form.marital_status.data = registration.marital_status
        form.education_level.data = registration.education_level
        form.primary_phone.data = registration.primary_phone
        form.secondary_phone.data = registration.secondary_phone
        form.email_address.data = registration.email_address
        form.residential_address.data = registration.residential_address
        form.city.data = registration.city
        form.state.data = registration.state
        form.postal_code.data = registration.postal_code
        form.lga.data = registration.lga
        form.ward.data = registration.ward
    
    return render_template('onboarding/step1_personal.html', 
                         form=form, 
                         registration=registration,
                         current_step=1)


def onboarding_step_2(registration):
    """Step 2: Business/Organization Information"""
    form = OnboardingStep2Form()
    
    if form.validate_on_submit():
        # Save form data to registration
        registration.organization_name = form.organization_name.data
        registration.business_registration_number = form.business_registration_number.data
        registration.tax_identification_number = form.tax_identification_number.data
        registration.business_address = form.business_address.data
        registration.business_type = form.business_type.data
        registration.years_in_operation = form.years_in_operation.data
        registration.number_of_employees = form.number_of_employees.data
        registration.annual_turnover = form.annual_turnover.data
        
        # Update progress
        registration.current_step = max(registration.current_step, 3)
        registration.calculate_completion_percentage()
        
        db.session.commit()
        flash('Business information saved successfully', 'success')
        return redirect(url_for('onboarding_step', step=3))
    
    # Pre-populate form if data exists
    if registration.organization_name:
        form.organization_name.data = registration.organization_name
        form.business_registration_number.data = registration.business_registration_number
        form.tax_identification_number.data = registration.tax_identification_number
        form.business_address.data = registration.business_address
        form.business_type.data = registration.business_type
        form.years_in_operation.data = registration.years_in_operation
        form.number_of_employees.data = registration.number_of_employees
        form.annual_turnover.data = registration.annual_turnover
    
    return render_template('onboarding/step2_business.html', 
                         form=form, 
                         registration=registration,
                         current_step=2)


def onboarding_step_3(registration):
    """Step 3: Role-specific Information"""
    # Get appropriate form based on role
    if registration.role == 'farmer':
        form = OnboardingStep3FarmerForm()
        template = 'onboarding/step3_farmer_wizard.html'
    elif registration.role == 'aggregator':
        form = OnboardingStep3AggregatorForm()
        template = 'onboarding/step3_aggregator.html'
    elif registration.role == 'transport_company':
        form = OnboardingStep3TransportForm()
        template = 'onboarding/step3_transport.html'
    elif registration.role == 'bulk_trader':
        form = OnboardingStep3BulkTraderForm()
        template = 'onboarding/step3_bulk_trader.html'
    elif registration.role == 'retailer':
        form = OnboardingStep3RetailerForm()
        template = 'onboarding/step3_retailer.html'
    elif registration.role == 'input_supplier':
        form = OnboardingStep3InputSupplierForm()
        template = 'onboarding/step3_input_supplier.html'
    else:
        # For other roles (investor, government_agency, ngo_dev_partner), skip to step 4
        flash('Role-specific information not required for your role', 'info')
        registration.current_step = max(registration.current_step, 4)
        registration.calculate_completion_percentage()
        db.session.commit()
        return redirect(url_for('onboarding_step', step=4))
    
    if form.validate_on_submit():
        # Save role-specific data
        if registration.role == 'farmer':
            registration.farm_size = form.farm_size.data
            registration.crops_grown = form.crops_grown.data
            registration.season_calendar = form.season_calendar.data
            registration.avg_output = form.avg_output.data
            registration.farming_experience = form.farming_experience.data
            registration.farming_methods = form.farming_methods.data
            registration.irrigation_methods = form.irrigation_methods.data
            registration.postharvest_facilities = form.postharvest_facilities.data
            registration.coop_member = form.coop_member.data
            registration.extension_service = form.extension_service.data
        elif registration.role == 'aggregator':
            registration.aggregation_capacity = form.aggregation_capacity.data
            registration.storage_capacity = form.storage_capacity.data
            registration.transportation_fleet = form.transportation_fleet.data
            registration.catchment_areas = form.catchment_areas.data
        elif registration.role == 'transport_company':
            registration.vehicle_types = form.vehicle_types.data
            registration.fleet_size = form.fleet_size.data
            registration.routes_covered = form.routes_covered.data
            registration.insurance_details = form.insurance_details.data
        elif registration.role == 'bulk_trader':
            registration.trading_volume = form.trading_volume.data
            registration.target_markets = form.target_markets.data
            registration.commodity_specialization = form.commodity_specialization.data
        elif registration.role == 'retailer':
            registration.store_type = form.store_type.data
            registration.retail_locations = form.retail_locations.data
            registration.customer_base = form.customer_base.data
        elif registration.role == 'input_supplier':
            registration.input_types = form.input_types.data
            registration.supplier_network = form.supplier_network.data
            registration.distribution_channels = form.distribution_channels.data
        
        # Update progress and program tag
        registration.current_step = max(registration.current_step, 4)
        registration.program_tag = 'LAFSINCO/Produce for Lagos Registration'
        registration.calculate_completion_percentage()
        
        db.session.commit()
        flash('Farmer information saved successfully', 'success')
        return redirect(url_for('onboarding_step', step=4))
    
    # Pre-populate form if data exists
    if registration.role == 'farmer' and registration.farm_size:
        form.farm_size.data = registration.farm_size
        form.crops_grown.data = registration.crops_grown
        form.season_calendar.data = registration.season_calendar
        form.avg_output.data = registration.avg_output
        form.farming_experience.data = registration.farming_experience
        form.farming_methods.data = registration.farming_methods
        form.irrigation_methods.data = registration.irrigation_methods
        form.postharvest_facilities.data = registration.postharvest_facilities
        form.coop_member.data = registration.coop_member
        form.extension_service.data = registration.extension_service
    # Add similar pre-population for other roles...
    
    return render_template(template, 
                         form=form, 
                         registration=registration,
                         current_step=3)


def onboarding_step_4(registration):
    """Step 4: Financial Information & Document Upload"""
    form = OnboardingStep4Form()
    
    if form.validate_on_submit():
        # Save financial information
        registration.bank_name = form.bank_name.data
        registration.account_number = form.account_number.data
        registration.account_name = form.account_name.data
        registration.bvn = form.bvn.data
        
        # Handle document uploads
        upload_folder = 'static/uploads/onboarding'
        os.makedirs(upload_folder, exist_ok=True)
        
        if form.id_document.data:
            filename = secure_filename(f"{current_user.id}_id_{form.id_document.data.filename}")
            filepath = os.path.join(upload_folder, filename)
            form.id_document.data.save(filepath)
            registration.id_document_path = filepath
        
        if form.business_registration.data:
            filename = secure_filename(f"{current_user.id}_business_{form.business_registration.data.filename}")
            filepath = os.path.join(upload_folder, filename)
            form.business_registration.data.save(filepath)
            registration.business_registration_path = filepath
        
        if form.tax_certificate.data:
            filename = secure_filename(f"{current_user.id}_tax_{form.tax_certificate.data.filename}")
            filepath = os.path.join(upload_folder, filename)
            form.tax_certificate.data.save(filepath)
            registration.tax_certificate_path = filepath
        
        if form.certifications.data:
            filename = secure_filename(f"{current_user.id}_cert_{form.certifications.data.filename}")
            filepath = os.path.join(upload_folder, filename)
            form.certifications.data.save(filepath)
            registration.certifications_path = filepath
        
        if form.additional_documents.data:
            filename = secure_filename(f"{current_user.id}_additional_{form.additional_documents.data.filename}")
            filepath = os.path.join(upload_folder, filename)
            form.additional_documents.data.save(filepath)
            registration.additional_documents_path = filepath
        
        # Mark registration as completed
        registration.registration_status = 'completed'
        registration.completed_date = datetime.utcnow()
        registration.completion_percentage = 100
        registration.program_tag = 'LAFSINCO/Produce for Lagos Registration'
        
        db.session.commit()
        flash('Registration completed successfully! Your application is now under review.', 'success')
        return redirect(url_for('onboarding_success_confirmation'))
    
    # Pre-populate form if data exists
    if registration.bank_name:
        form.bank_name.data = registration.bank_name
        form.account_number.data = registration.account_number
        form.account_name.data = registration.account_name
        form.bvn.data = registration.bvn
    
    return render_template('onboarding/step4_financial.html', 
                         form=form, 
                         registration=registration,
                         current_step=4)


@app.route('/onboarding/success')
@login_required
def onboarding_success_confirmation():
    """Success confirmation page after completing registration"""
    registration = ProduceLagosRegistration.query.filter_by(user_id=current_user.id).first()
    if not registration or registration.registration_status != 'completed':
        flash('Registration not found or incomplete', 'error')
        return redirect(url_for('onboarding_start'))
    
    return render_template('onboarding/success_confirmation.html', registration=registration)

@app.route('/onboarding/status')
@login_required
def onboarding_status():
    """View registration status"""
    registration = ProduceLagosRegistration.query.filter_by(user_id=current_user.id).first()
    if not registration:
        return redirect(url_for('onboarding_start'))
    
    return render_template('onboarding/registration_status.html', registration=registration)


@app.route('/admin/onboarding')
@login_required
def admin_onboarding_dashboard():
    """Admin dashboard for reviewing registrations"""
    if not current_user.is_admin():
        abort(403)
    
    # Get filter parameters
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = ProduceLagosRegistration.query
    
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if status_filter != 'all':
        query = query.filter_by(registration_status=status_filter)
    
    registrations = query.order_by(ProduceLagosRegistration.started_date.desc()).all()
    
    # Get statistics
    stats = {
        'total_registrations': ProduceLagosRegistration.query.count(),
        'pending_approval': ProduceLagosRegistration.query.filter_by(registration_status='completed').count(),
        'approved': ProduceLagosRegistration.query.filter_by(registration_status='approved').count(),
        'in_progress': ProduceLagosRegistration.query.filter_by(registration_status='in_progress').count(),
    }
    
    return render_template('admin/onboarding_dashboard.html', 
                         registrations=registrations,
                         stats=stats,
                         role_filter=role_filter,
                         status_filter=status_filter)


@app.route('/admin/onboarding/review/<int:registration_id>', methods=['GET', 'POST'])
@login_required
def admin_review_registration(registration_id):
    """Admin review of individual registration"""
    if not current_user.is_admin():
        abort(403)
    
    registration = ProduceLagosRegistration.query.get_or_404(registration_id)
    form = OnboardingAdminReviewForm()
    
    if form.validate_on_submit():
        registration.registration_status = form.registration_status.data
        registration.admin_comments = form.admin_comments.data
        registration.reviewed_by = current_user.id
        registration.reviewed_date = datetime.utcnow()
        
        if form.registration_status.data == 'approved':
            registration.approved_date = datetime.utcnow()
        
        db.session.commit()
        flash(f'Registration {form.registration_status.data} successfully', 'success')
        return redirect(url_for('admin_onboarding_dashboard'))
    
    # Pre-populate form
    form.registration_status.data = registration.registration_status
    form.admin_comments.data = registration.admin_comments
    
    return render_template('admin/review_registration.html', 
                         registration=registration,
                         form=form)


@app.route('/admin/onboarding/bulk', methods=['GET', 'POST'])
@login_required
def admin_bulk_onboarding():
    """Admin interface for bulk onboarding"""
    if not current_user.is_admin():
        abort(403)
    
    form = BulkOnboardingForm()
    
    if form.validate_on_submit():
        # Handle CSV upload and processing
        upload_folder = 'static/uploads/bulk_onboarding'
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(f"bulk_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{form.csv_file.data.filename}")
        filepath = os.path.join(upload_folder, filename)
        form.csv_file.data.save(filepath)
        
        # Create bulk onboarding record
        bulk_record = BulkOnboarding(
            batch_name=form.batch_name.data,
            uploaded_by=current_user.id,
            file_path=filepath
        )
        db.session.add(bulk_record)
        db.session.commit()
        
        # Process CSV file (this would be handled by a background task in production)
        try:
            import csv
            with open(filepath, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                total_records = 0
                successful_registrations = 0
                failed_registrations = 0
                errors = []
                
                for row in reader:
                    total_records += 1
                    try:
                        # Create user and registration from CSV data
                        # This is a simplified version - full implementation would include validation
                        user = User(
                            name=row.get('full_name', ''),
                            email=row.get('email', ''),
                            role=form.role.data
                        )
                        user.set_password('defaultpassword123')  # Should be changed on first login
                        db.session.add(user)
                        db.session.flush()
                        
                        registration = ProduceLagosRegistration(
                            user_id=user.id,
                            role=form.role.data,
                            full_name=row.get('full_name', ''),
                            primary_phone=row.get('phone', ''),
                            email_address=row.get('email', ''),
                            registration_status='completed'
                        )
                        db.session.add(registration)
                        successful_registrations += 1
                        
                    except Exception as e:
                        failed_registrations += 1
                        errors.append(f"Row {total_records}: {str(e)}")
                
                # Update bulk record
                bulk_record.total_records = total_records
                bulk_record.successful_registrations = successful_registrations
                bulk_record.failed_registrations = failed_registrations
                bulk_record.status = 'completed'
                if errors:
                    bulk_record.error_log = '\n'.join(errors)
                
                db.session.commit()
                
                flash(f'Bulk upload completed: {successful_registrations} successful, {failed_registrations} failed', 'success')
                
        except Exception as e:
            bulk_record.status = 'failed'
            bulk_record.error_log = str(e)
            db.session.commit()
            flash(f'Bulk upload failed: {str(e)}', 'error')
        
        return redirect(url_for('admin_bulk_onboarding'))
    
    # Get recent bulk uploads
    recent_uploads = BulkOnboarding.query.order_by(BulkOnboarding.upload_date.desc()).limit(10).all()
    
    return render_template('admin/bulk_onboarding.html', 
                         form=form,
                         recent_uploads=recent_uploads)


@app.route('/admin/onboarding/export')
@login_required
def admin_export_registrations():
    """Export registrations to CSV"""
    if not current_user.is_admin():
        abort(403)
    
    # Get filter parameters
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')
    
    # Build query
    query = ProduceLagosRegistration.query
    
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
    
    if status_filter != 'all':
        query = query.filter_by(registration_status=status_filter)
    
    registrations = query.all()
    
    # Create CSV response
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Name', 'Email', 'Role', 'Phone', 'State', 'LGA', 'Registration Status',
        'Completion %', 'Started Date', 'Completed Date', 'Approved Date'
    ])
    
    # Write data
    for reg in registrations:
        writer.writerow([
            reg.full_name or '',
            reg.email_address or '',
            reg.get_role_display_name(),
            reg.primary_phone or '',
            reg.state or '',
            reg.lga or '',
            reg.registration_status,
            reg.completion_percentage,
            reg.started_date.strftime('%Y-%m-%d') if reg.started_date else '',
            reg.completed_date.strftime('%Y-%m-%d') if reg.completed_date else '',
            reg.approved_date.strftime('%Y-%m-%d') if reg.approved_date else ''
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=produce_lagos_registrations_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    
    return response


# ==========================================
# PROCESSOR ONBOARDING ROUTES
# ==========================================

@app.route('/processor/onboarding')
@login_required
def processor_onboarding_start():
    """Start processor onboarding for agro-processors"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    # Check if processor profile already exists
    profile = ProcessorProfile.query.filter_by(user_id=current_user.id).first()
    if profile:
        if profile.kyc_status == 'verified':
            flash('Your processor profile is already verified!', 'success')
            return redirect(url_for('processor_dashboard'))
        else:
            flash('Continue your processor profile setup.', 'info')
            return redirect(url_for('processor_onboarding_step', step=1))
    
    return render_template('processor/onboarding_intro.html', title='Processor Onboarding')


@app.route('/processor/onboarding/step/<int:step>', methods=['GET', 'POST'])
@login_required
def processor_onboarding_step(step):
    """Multi-step processor onboarding process"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    # Get or create processor profile
    profile = ProcessorProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = ProcessorProfile(user_id=current_user.id, business_name='', cac_number='', contact_phone='')
        db.session.add(profile)
        db.session.commit()
    
    if step == 1:
        return processor_onboarding_step_1(profile)
    elif step == 2:
        return processor_onboarding_step_2(profile)
    elif step == 3:
        return processor_onboarding_step_3(profile)
    elif step == 4:
        return processor_onboarding_step_4(profile)
    elif step == 5:
        return processor_onboarding_step_5(profile)
    else:
        flash('Invalid step', 'error')
        return redirect(url_for('processor_onboarding_start'))


def processor_onboarding_step_1(profile):
    """Step 1: Business Information"""
    form = ProcessorOnboardingStep1Form()
    
    if form.validate_on_submit():
        profile.business_name = form.business_name.data
        profile.cac_number = form.cac_number.data
        profile.contact_person = form.contact_person.data
        profile.contact_phone = form.contact_phone.data
        profile.website = form.website.data
        profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Business information saved successfully!', 'success')
        return redirect(url_for('processor_onboarding_step', step=2))
    
    # Pre-populate form with existing data
    if profile.business_name:
        form.business_name.data = profile.business_name
        form.cac_number.data = profile.cac_number
        form.contact_person.data = profile.contact_person
        form.contact_phone.data = profile.contact_phone
        form.website.data = profile.website
    
    return render_template('processor/onboarding_step_1.html', form=form, step=1, title='Business Information')


def processor_onboarding_step_2(profile):
    """Step 2: Processing Capacity and Products"""
    form = ProcessorOnboardingStep2Form()
    
    if form.validate_on_submit():
        profile.processing_capacity_tpd = form.processing_capacity_tpd.data
        profile.products_processed = form.products_processed.data
        profile.employees_count = form.employees_count.data
        profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Processing capacity information saved successfully!', 'success')
        return redirect(url_for('processor_onboarding_step', step=3))
    
    # Pre-populate form
    if profile.processing_capacity_tpd:
        form.processing_capacity_tpd.data = profile.processing_capacity_tpd
        form.products_processed.data = profile.products_processed
        form.employees_count.data = profile.employees_count
    
    return render_template('processor/onboarding_step_2.html', form=form, step=2, title='Processing Capacity')


def processor_onboarding_step_3(profile):
    """Step 3: Plant Location and Logistics"""
    form = ProcessorOnboardingStep3Form()
    
    if form.validate_on_submit():
        profile.plant_location_state = form.plant_location_state.data
        profile.plant_location_lga = form.plant_location_lga.data
        profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Location information saved successfully!', 'success')
        return redirect(url_for('processor_onboarding_step', step=4))
    
    # Pre-populate form
    if profile.plant_location_state:
        form.plant_location_state.data = profile.plant_location_state
        form.plant_location_lga.data = profile.plant_location_lga
    
    return render_template('processor/onboarding_step_3.html', form=form, step=3, title='Plant Location')


def processor_onboarding_step_4(profile):
    """Step 4: Document Uploads"""
    form = ProcessorOnboardingStep4Form()
    
    if form.validate_on_submit():
        upload_folder = 'static/uploads/processor'
        os.makedirs(upload_folder, exist_ok=True)
        
        # Handle NAFDAC permit upload
        if form.nafdac_permit_file.data:
            filename = secure_filename(f"{current_user.id}_nafdac_{form.nafdac_permit_file.data.filename}")
            filepath = os.path.join(upload_folder, 'nafdac', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            form.nafdac_permit_file.data.save(filepath)
            profile.nafdac_permit_file = filepath
        
        # Handle utility documents upload
        if form.utility_docs_file.data:
            filename = secure_filename(f"{current_user.id}_utility_{form.utility_docs_file.data.filename}")
            filepath = os.path.join(upload_folder, 'utility', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            form.utility_docs_file.data.save(filepath)
            profile.utility_docs_file = filepath
        
        profile.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Documents uploaded successfully!', 'success')
        return redirect(url_for('processor_onboarding_step', step=5))
    
    return render_template('processor/onboarding_step_4.html', form=form, step=4, title='Document Uploads')


def processor_onboarding_step_5(profile):
    """Step 5: Banking and Final Details"""
    form = ProcessorOnboardingStep5Form()
    
    if form.validate_on_submit():
        profile.bank_name = form.bank_name.data
        profile.account_number = form.account_number.data
        profile.kyc_status = 'pending'  # Submit for admin review
        profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Processor profile submitted for review! You will be notified once approved.', 'success')
        return redirect(url_for('processor_dashboard'))
    
    # Pre-populate form
    if profile.bank_name:
        form.bank_name.data = profile.bank_name
        form.account_number.data = profile.account_number
    
    return render_template('processor/onboarding_step_5.html', form=form, step=5, title='Banking Information')


@app.route('/processor/dashboard')
@login_required
def processor_dashboard():
    """Processor dashboard with sourcing and loan features"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    # Check if processor profile exists
    profile = ProcessorProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please complete your processor profile setup first.', 'info')
        return redirect(url_for('processor_onboarding_start'))
    
    # Get recent produce for sourcing
    available_produce = Produce.query.filter_by(is_available=True, is_sold=False).order_by(Produce.date_listed.desc()).limit(10).all()
    
    # Get processor's loan applications
    loan_applications = LoanApplication.query.filter_by(user_id=current_user.id).order_by(LoanApplication.created_at.desc()).limit(5).all()
    
    return render_template('processor/dashboard.html', 
                         title='Processor Dashboard',
                         profile=profile,
                         available_produce=available_produce,
                         loan_applications=loan_applications)


# ==========================================
# BOI LOAN APPLICATION ROUTES
# ==========================================

@app.route('/processor/boi-loan/apply')
@login_required
def boi_loan_intro():
    """BOI Loan application intro with processing fee information"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    # Check if processor profile is verified
    profile = ProcessorProfile.query.filter_by(user_id=current_user.id).first()
    if not profile or not profile.is_verified():
        flash('Your processor profile must be verified before applying for loans.', 'warning')
        return redirect(url_for('processor_dashboard'))
    
    return render_template('processor/boi_loan_intro.html', 
                         title='BOI Loan Application',
                         processing_fee=5000)


@app.route('/processor/boi-loan/payment', methods=['POST'])
@login_required
def boi_loan_payment():
    """Process BOI loan application processing fee payment"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    # Create draft loan application
    profile = ProcessorProfile.query.filter_by(user_id=current_user.id).first()
    loan_app = LoanApplication(
        processor_id=profile.id,
        user_id=current_user.id,
        loan_amount_requested=0,  # Will be filled in later
        purpose_of_loan='',  # Will be filled in later
        tenor_months=12,  # Default value
        status='payment_pending',
        platform_fee_amount=5000.00
    )
    db.session.add(loan_app)
    db.session.commit()
    
    if payment_service:
        try:
            # Generate payment reference
            reference = payment_service.generate_reference("boi_loan_fee")
            
            # Initialize payment with Paystack
            payment_data = payment_service.initialize_transaction(
                email=current_user.email,
                amount=5000.00,
                reference=reference,
                callback_url=url_for('boi_loan_payment_callback', _external=True),
                metadata={
                    'loan_application_id': loan_app.id,
                    'user_id': current_user.id,
                    'type': 'boi_loan_processing_fee'
                }
            )
            
            # Update loan application with payment reference
            loan_app.payment_reference = reference
            db.session.commit()
            
            return redirect(payment_data['data']['authorization_url'])
            
        except Exception as e:
            app.logger.error(f"BOI loan payment initialization failed: {e}")
            flash('Payment initialization failed. Please try again.', 'danger')
            return redirect(url_for('boi_loan_intro'))
    else:
        flash('Payment service not available. Please try again later.', 'danger')
        return redirect(url_for('boi_loan_intro'))


@app.route('/processor/boi-loan/payment/callback')
@login_required
def boi_loan_payment_callback():
    """Handle BOI loan payment callback from Paystack"""
    reference = request.args.get('reference')
    
    if not reference:
        flash('Payment verification failed. Invalid reference.', 'danger')
        return redirect(url_for('processor_dashboard'))
    
    # Find loan application by payment reference
    loan_app = LoanApplication.query.filter_by(payment_reference=reference).first()
    if not loan_app:
        flash('Loan application not found.', 'danger')
        return redirect(url_for('processor_dashboard'))
    
    if payment_service:
        try:
            # Verify payment with Paystack
            verification_result = payment_service.verify_transaction(reference)
            
            if verification_result['status'] and verification_result['data']['status'] == 'success':
                # Payment successful
                loan_app.platform_fee_status = 'paid'
                loan_app.payment_date = datetime.utcnow()
                loan_app.status = 'draft'  # Now user can fill out loan form
                db.session.commit()
                
                flash('Processing fee payment successful! You can now complete your loan application.', 'success')
                return redirect(url_for('boi_loan_application', loan_id=loan_app.id))
            else:
                # Payment failed
                loan_app.platform_fee_status = 'failed'
                db.session.commit()
                
                flash('Payment verification failed. Please try again.', 'danger')
                return redirect(url_for('boi_loan_intro'))
                
        except Exception as e:
            app.logger.error(f"BOI loan payment verification failed: {e}")
            flash('Payment verification failed. Please contact support.', 'danger')
            return redirect(url_for('processor_dashboard'))
    else:
        flash('Payment service not available. Please contact support.', 'danger')
        return redirect(url_for('processor_dashboard'))


@app.route('/processor/boi-loan/application/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def boi_loan_application(loan_id):
    """BOI Loan application form (unlocked after payment)"""
    if not current_user.is_agro_processor():
        flash('Access denied. Agro-processors only.', 'danger')
        return redirect(url_for('home'))
    
    loan_app = LoanApplication.query.get_or_404(loan_id)
    
    # Verify ownership and payment status
    if loan_app.user_id != current_user.id:
        abort(403)
    
    if not loan_app.is_payment_completed():
        flash('Processing fee payment required before completing application.', 'warning')
        return redirect(url_for('boi_loan_intro'))
    
    form = BOILoanApplicationForm()
    
    if form.validate_on_submit():
        # Update loan application with form data
        loan_app.loan_amount_requested = form.loan_amount_requested.data
        loan_app.purpose_of_loan = form.purpose_of_loan.data
        loan_app.tenor_months = form.tenor_months.data
        loan_app.collateral_description = form.collateral_description.data
        
        # Handle file uploads
        upload_folder = 'static/uploads/loans'
        os.makedirs(upload_folder, exist_ok=True)
        
        if form.financials_file.data:
            filename = secure_filename(f"{current_user.id}_financials_{form.financials_file.data.filename}")
            filepath = os.path.join(upload_folder, 'financials', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            form.financials_file.data.save(filepath)
            loan_app.financials_file = filepath
        
        if form.projections_file.data:
            filename = secure_filename(f"{current_user.id}_projections_{form.projections_file.data.filename}")
            filepath = os.path.join(upload_folder, 'projections', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            form.projections_file.data.save(filepath)
            loan_app.projections_file = filepath
        
        if form.supporting_docs_file.data:
            filename = secure_filename(f"{current_user.id}_supporting_{form.supporting_docs_file.data.filename}")
            filepath = os.path.join(upload_folder, 'supporting', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            form.supporting_docs_file.data.save(filepath)
            loan_app.supporting_docs_file = filepath
        
        # Generate AgroLink data snapshot
        snapshot_data = generate_agrolink_data_snapshot(current_user.id)
        loan_app.set_agrolink_data_snapshot(snapshot_data)
        
        # Submit application
        loan_app.status = 'submitted'
        loan_app.submitted_at = datetime.utcnow()
        loan_app.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('BOI loan application submitted successfully! You will be notified of the review outcome.', 'success')
        return redirect(url_for('processor_dashboard'))
    
    # Pre-populate form if data exists
    if loan_app.loan_amount_requested:
        form.loan_amount_requested.data = loan_app.loan_amount_requested
        form.purpose_of_loan.data = loan_app.purpose_of_loan
        form.tenor_months.data = loan_app.tenor_months
        form.collateral_description.data = loan_app.collateral_description
    
    return render_template('processor/boi_loan_application.html', 
                         form=form, 
                         loan_app=loan_app,
                         title='BOI Loan Application')


def generate_agrolink_data_snapshot(user_id):
    """Generate AgroLink data snapshot for loan applications"""
    try:
        # Get transaction history (last 12 months)
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.created_at >= cutoff_date,
            Transaction.status == 'successful'
        ).all()
        
        # Calculate metrics
        total_transactions = len(transactions)
        total_value = sum(t.total_amount for t in transactions)
        avg_monthly_volume = total_value / 12 if total_value > 0 else 0
        
        # Get produce interactions (as buyer)
        produce_purchased = Produce.query.filter_by(buyer_id=user_id).all()
        
        snapshot = {
            'snapshot_date': datetime.utcnow().isoformat(),
            'period': '12_months',
            'transaction_summary': {
                'total_transactions': total_transactions,
                'total_trade_value_ngn': total_value,
                'average_monthly_value_ngn': avg_monthly_volume,
                'transaction_types': list(set(t.transaction_type for t in transactions))
            },
            'sourcing_activity': {
                'total_produce_purchased': len(produce_purchased),
                'primary_crops': list(set(p.name for p in produce_purchased)),
                'supplier_states': list(set(p.farmer.name if hasattr(p, 'farmer') else 'Unknown' for p in produce_purchased))
            },
            'platform_engagement': {
                'registration_date': user_id,  # This would be actual user registration date
                'last_activity': datetime.utcnow().isoformat(),
                'profile_completion': 'complete'
            }
        }
        
        return snapshot
    except Exception as e:
        app.logger.error(f"Error generating AgroLink data snapshot: {e}")
        return {
            'snapshot_date': datetime.utcnow().isoformat(),
            'error': 'Unable to generate complete snapshot',
            'basic_info': {
                'user_id': user_id,
                'snapshot_requested': True
            }
        }


# ===== TRANSPORT & LOGISTICS ROUTES =====

# Initialize logistics service
try:
    from logistics_service import logistics_service
except Exception as e:
    app.logger.error(f"Logistics service initialization failed: {e}")
    logistics_service = None


@app.route('/transport/register', methods=['GET', 'POST'])
@login_required
def transport_register():
    """Transport company registration"""
    # Check if already has a transport profile
    existing_profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('You already have a transport company profile.', 'info')
        return redirect(url_for('transport_dashboard'))
    
    form = TransportRegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Create transport profile
            profile = TransportProfile(
                user_id=current_user.id,
                company_name=form.company_name.data,
                cac_number=form.cac_number.data,
                fleet_size=form.fleet_size.data,
                price_per_ton_km=form.price_per_ton_km.data,
                cold_chain_capable=form.has_cold_chain.data
            )
            
            # Set vehicle types as JSON list
            profile.set_vehicle_types_list([form.vehicle_types.data])
            
            # Handle file uploads
            if form.cac_file.data:
                filename = secure_filename(f"cac_{current_user.id}_{form.cac_file.data.filename}")
                filepath = os.path.join('uploads', 'transport', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                form.cac_file.data.save(filepath)
                profile.cac_file = filepath
            
            if form.insurance_file.data:
                filename = secure_filename(f"insurance_{current_user.id}_{form.insurance_file.data.filename}")
                filepath = os.path.join('uploads', 'transport', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                form.insurance_file.data.save(filepath)
                profile.insurance_file = filepath
            
            # Update user phone
            current_user.phone_number = form.phone_number.data
            current_user.role = 'transport_company'
            
            db.session.add(profile)
            db.session.commit()
            
            flash('Transport company registered successfully! Add your routes to start receiving job notifications.', 'success')
            return redirect(url_for('transport_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Transport registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('transport/register.html',
                         form=form,
                         title='Register Transport Company')


@app.route('/transport/dashboard')
@login_required
def transport_dashboard():
    """Transport company dashboard"""
    # Get or create transport profile
    profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    
    if not profile:
        flash('Please register your transport company first.', 'warning')
        return redirect(url_for('transport_register'))
    
    # Get available jobs matching this transporter
    available_jobs = []
    if logistics_service:
        matched_jobs = logistics_service.get_available_jobs(profile.id, limit=10)
        available_jobs = [m['job'] for m in matched_jobs]
    else:
        available_jobs = LogisticsRequest.query.filter(
            LogisticsRequest.status.in_(['pending', 'bidding'])
        ).order_by(LogisticsRequest.timestamp.desc()).limit(10).all()
    
    # Get transporter's bids
    my_bids = LogisticsBid.query.filter_by(transporter_id=profile.id)\
                                .order_by(LogisticsBid.created_at.desc()).limit(10).all()
    
    # Get active trips (accepted bids)
    active_trips = []
    accepted_bids = LogisticsBid.query.filter_by(
        transporter_id=profile.id,
        status='accepted'
    ).all()
    
    for bid in accepted_bids:
        if bid.logistics_request and bid.logistics_request.status in ['assigned', 'in_transit']:
            active_trips.append(bid.logistics_request)
    
    # Get cold chain devices
    cold_chain_devices = ColdChainDevice.query.filter_by(transporter_id=profile.id).all()
    
    # Calculate stats
    stats = {
        'total_trips': profile.total_trips,
        'successful_trips': profile.successful_trips,
        'on_time_rate': profile.on_time_percentage(),
        'rating': profile.rating,
        'wallet_balance': profile.wallet_balance,
        'pending_bids': LogisticsBid.query.filter_by(transporter_id=profile.id, status='pending').count(),
        'active_jobs': len(active_trips)
    }
    
    return render_template('transport/dashboard.html',
                         profile=profile,
                         available_jobs=available_jobs,
                         my_bids=my_bids,
                         active_trips=active_trips,
                         cold_chain_devices=cold_chain_devices,
                         stats=stats,
                         title='Transport Dashboard')


@app.route('/transport/routes', methods=['GET', 'POST'])
@login_required
def transport_routes():
    """Manage transport routes"""
    profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('transport_register'))
    
    form = TransportRouteForm()
    
    if form.validate_on_submit():
        # Get existing routes
        routes = profile.get_routes_covered_list()
        
        # Add new route
        new_route = [form.from_state.data, form.to_state.data]
        if new_route not in routes:
            routes.append(new_route)
            profile.set_routes_covered_list(routes)
            db.session.commit()
            flash(f'Route {form.from_state.data} → {form.to_state.data} added successfully!', 'success')
        else:
            flash('This route already exists.', 'info')
        
        return redirect(url_for('transport_routes'))
    
    return render_template('transport/routes.html',
                         form=form,
                         profile=profile,
                         routes=profile.get_routes_covered_list(),
                         title='Manage Routes')


@app.route('/transport/routes/<int:index>/delete', methods=['POST'])
@login_required
def delete_transport_route(index):
    """Delete a transport route"""
    profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('transport_register'))
    
    routes = profile.get_routes_covered_list()
    if 0 <= index < len(routes):
        deleted_route = routes.pop(index)
        profile.set_routes_covered_list(routes)
        db.session.commit()
        flash(f'Route {deleted_route[0]} → {deleted_route[1]} removed.', 'success')
    
    return redirect(url_for('transport_routes'))


@app.route('/transport/cold-chain', methods=['GET', 'POST'])
@login_required
def transport_cold_chain():
    """Manage cold chain devices"""
    profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return redirect(url_for('transport_register'))
    
    form = ColdChainDeviceForm()
    
    if form.validate_on_submit():
        try:
            # Check for duplicate device ID
            existing = ColdChainDevice.query.filter_by(device_id=form.device_id.data).first()
            if existing:
                flash('Device ID already registered.', 'warning')
            else:
                device = ColdChainDevice(
                    transporter_id=profile.id,
                    device_id=form.device_id.data,
                    vehicle_registration=form.vehicle_registration.data,
                    max_temp_allowed=form.max_temp_allowed.data,
                    min_temp_allowed=form.min_temp_allowed.data
                )
                db.session.add(device)
                
                # Update profile to indicate cold chain capability
                profile.cold_chain_capable = True
                
                db.session.commit()
                flash('Cold chain device registered successfully!', 'success')
                return redirect(url_for('transport_cold_chain'))
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Cold chain device registration error: {e}")
            flash('Failed to register device. Please try again.', 'danger')
    
    devices = ColdChainDevice.query.filter_by(transporter_id=profile.id).all()
    
    return render_template('transport/cold_chain.html',
                         form=form,
                         devices=devices,
                         profile=profile,
                         title='Cold Chain Devices')


@app.route('/transport/device/<int:device_id>/toggle', methods=['POST'])
@login_required
def toggle_cold_chain_device(device_id):
    """Toggle cold chain device active status"""
    device = ColdChainDevice.query.get_or_404(device_id)
    profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    
    if not profile or device.transporter_id != profile.id:
        abort(403)
    
    device.is_active = not device.is_active
    db.session.commit()
    
    status = 'activated' if device.is_active else 'deactivated'
    flash(f'Device {device.device_id} {status}.', 'success')
    
    return redirect(url_for('transport_cold_chain'))


@app.route('/logistics/request/<int:produce_id>', methods=['GET', 'POST'])
@login_required
def logistics_request_enhanced(produce_id):
    """Enhanced logistics request with bidding"""
    produce = Produce.query.get_or_404(produce_id)
    form = EnhancedLogisticsRequestForm()
    form.produce_id.data = produce_id
    
    if form.validate_on_submit():
        try:
            logistics_request = LogisticsRequest(
                produce_id=produce_id,
                requester_id=current_user.id,
                request_type=form.request_type.data,
                preferred_date=form.preferred_date.data,
                preferred_time=form.preferred_time.data,
                pickup_location=form.pickup_location.data,
                pickup_state=form.pickup_state.data,
                destination_address=form.destination_address.data,
                destination_state=form.destination_state.data,
                quantity_tons=form.quantity_tons.data,
                requires_cold_chain=form.requires_cold_chain.data,
                notes=form.notes.data,
                status='pending'
            )
            
            db.session.add(logistics_request)
            db.session.commit()
            
            # Auto-match and notify transporters
            if logistics_service:
                matching_transporters = logistics_service.find_matching_transporters(logistics_request)
                if matching_transporters:
                    logistics_service.notify_transporters(logistics_request, matching_transporters)
                    flash(f'Transport request created! {len(matching_transporters)} transporters notified.', 'success')
                else:
                    flash('Transport request created! Waiting for transporter bids.', 'success')
            else:
                flash('Transport request created successfully!', 'success')
            
            return redirect(url_for('logistics_request_detail', request_id=logistics_request.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Logistics request error: {e}")
            flash('Failed to create transport request. Please try again.', 'danger')
    
    return render_template('transport/logistics_request.html',
                         form=form,
                         produce=produce,
                         title='Request Transport')


@app.route('/logistics/<int:request_id>')
@login_required
def logistics_request_detail(request_id):
    """View logistics request details and bids"""
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    
    # Check access permissions
    is_requester = logistics_request.requester_id == current_user.id
    transport_profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    is_transporter = transport_profile is not None
    is_admin = current_user.is_admin()
    
    if not (is_requester or is_transporter or is_admin):
        abort(403)
    
    # Get all bids for this request
    bids = LogisticsBid.query.filter_by(logistics_request_id=request_id)\
                             .order_by(LogisticsBid.created_at.desc()).all()
    
    # Check if current transporter has bid
    my_bid = None
    if transport_profile:
        my_bid = LogisticsBid.query.filter_by(
            logistics_request_id=request_id,
            transporter_id=transport_profile.id
        ).first()
    
    # Get cold chain logs if any
    cold_chain_logs = ColdChainLog.query.filter_by(logistics_request_id=request_id)\
                                        .order_by(ColdChainLog.timestamp.desc()).all()
    
    bid_form = TransportBidForm()
    
    return render_template('transport/logistics_detail.html',
                         logistics_request=logistics_request,
                         bids=bids,
                         my_bid=my_bid,
                         bid_form=bid_form,
                         cold_chain_logs=cold_chain_logs,
                         is_requester=is_requester,
                         is_transporter=is_transporter,
                         transport_profile=transport_profile,
                         title=f'Transport Job #{request_id}')


@app.route('/logistics/<int:request_id>/bid', methods=['POST'])
@login_required
def submit_bid(request_id):
    """Submit a bid on a logistics request"""
    transport_profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    if not transport_profile:
        flash('You need a transport company profile to bid.', 'warning')
        return redirect(url_for('transport_register'))
    
    form = TransportBidForm()
    
    if form.validate_on_submit():
        # Check for scam patterns before bidding (Layer 5)
        scam_score = 0
        scam_reason = None
        if scam_detector:
            is_scam, reason, score = scam_detector.is_scam_likely(
                user=current_user,
                action_type='logistics_bid',
                data={
                    'bid_amount': form.bid_amount.data,
                    'transport_profile': transport_profile
                }
            )
            
            if score >= 70:
                app.logger.warning(f"Bid hidden - Scam score {score}: {reason}")
                from models import ScamFlag
                flag = ScamFlag(
                    user_id=current_user.id,
                    action_type='logistics_bid',
                    scam_score=score,
                    reason=reason,
                    status='pending',
                    detected_at=datetime.utcnow()
                )
                db.session.add(flag)
                current_user.scam_score = max(current_user.scam_score or 0, score)
                db.session.commit()
                flash('Bid temporarily held for review.', 'warning')
                return redirect(url_for('logistics_request_detail', request_id=request_id))
            elif score >= 50:
                scam_score = score
                scam_reason = reason
        
        if logistics_service:
            result = logistics_service.process_bid(
                logistics_request_id=request_id,
                transporter_id=transport_profile.id,
                bid_amount=form.bid_amount.data,
                eta_hours=form.eta_hours.data,
                notes=form.notes.data,
                source_channel='web'
            )
            
            if result['success']:
                if scam_score >= 50:
                    from models import ScamFlag
                    flag = ScamFlag(
                        user_id=current_user.id,
                        action_type='logistics_bid',
                        scam_score=scam_score,
                        reason=scam_reason,
                        status='pending',
                        detected_at=datetime.utcnow()
                    )
                    db.session.add(flag)
                    current_user.scam_score = max(current_user.scam_score or 0, scam_score)
                    db.session.commit()
                
                if result.get('updated'):
                    flash('Your bid has been updated.', 'success')
                else:
                    flash(f'Bid of ₦{form.bid_amount.data:,.0f} submitted successfully!', 'success')
            else:
                flash(result.get('error', 'Failed to submit bid.'), 'danger')
        else:
            # Fallback without service
            try:
                existing_bid = LogisticsBid.query.filter_by(
                    logistics_request_id=request_id,
                    transporter_id=transport_profile.id
                ).first()
                
                if existing_bid:
                    existing_bid.bid_amount = form.bid_amount.data
                    existing_bid.eta_hours = form.eta_hours.data
                    existing_bid.notes = form.notes.data
                else:
                    bid = LogisticsBid(
                        logistics_request_id=request_id,
                        transporter_id=transport_profile.id,
                        bid_amount=form.bid_amount.data,
                        eta_hours=form.eta_hours.data,
                        notes=form.notes.data,
                        source_channel='web'
                    )
                    db.session.add(bid)
                
                # Update request status
                logistics_request = LogisticsRequest.query.get(request_id)
                if logistics_request and logistics_request.status == 'pending':
                    logistics_request.status = 'bidding'
                
                db.session.commit()
                
                if scam_score >= 50:
                    from models import ScamFlag
                    flag = ScamFlag(
                        user_id=current_user.id,
                        action_type='logistics_bid',
                        scam_score=scam_score,
                        reason=scam_reason,
                        status='pending',
                        detected_at=datetime.utcnow()
                    )
                    db.session.add(flag)
                    current_user.scam_score = max(current_user.scam_score or 0, scam_score)
                    db.session.commit()
                
                flash('Bid submitted successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Failed to submit bid.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
    
    return redirect(url_for('logistics_request_detail', request_id=request_id))


@app.route('/logistics/<int:request_id>/accept-bid/<int:bid_id>', methods=['POST'])
@login_required
def accept_bid(request_id, bid_id):
    """Accept a winning bid"""
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    
    if logistics_request.requester_id != current_user.id:
        abort(403)
    
    if logistics_service:
        result = logistics_service.accept_bid(request_id, bid_id, current_user.id)
        
        if result['success']:
            flash(result.get('message', 'Bid accepted! 50% payment released to transporter.'), 'success')
        else:
            flash(result.get('error', 'Failed to accept bid.'), 'danger')
    else:
        # Fallback
        try:
            bid = LogisticsBid.query.get_or_404(bid_id)
            
            bid.status = 'accepted'
            logistics_request.status = 'assigned'
            logistics_request.winning_bid_id = bid.id
            
            # Reject other bids
            LogisticsBid.query.filter(
                LogisticsBid.logistics_request_id == request_id,
                LogisticsBid.id != bid_id
            ).update({'status': 'rejected'})
            
            db.session.commit()
            flash('Bid accepted! Transporter assigned.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Failed to accept bid.', 'danger')
    
    return redirect(url_for('logistics_request_detail', request_id=request_id))


@app.route('/logistics/<int:request_id>/start-trip', methods=['POST'])
@login_required
def start_trip(request_id):
    """Mark trip as started (in transit)"""
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    transport_profile = TransportProfile.query.filter_by(user_id=current_user.id).first()
    
    if not transport_profile:
        abort(403)
    
    # Verify this transporter won the bid
    winning_bid = logistics_request.winning_bid
    if not winning_bid or winning_bid.transporter_id != transport_profile.id:
        abort(403)
    
    logistics_request.status = 'in_transit'
    db.session.commit()
    
    flash('Trip started! Safe travels.', 'success')
    return redirect(url_for('logistics_request_detail', request_id=request_id))


@app.route('/logistics/<int:request_id>/complete', methods=['POST'])
@login_required
def complete_delivery(request_id):
    """Mark delivery as complete"""
    logistics_request = LogisticsRequest.query.get_or_404(request_id)
    
    if logistics_request.requester_id != current_user.id:
        abort(403)
    
    if logistics_service:
        result = logistics_service.complete_delivery(request_id, current_user.id)
        
        if result['success']:
            msg = f"Delivery completed! Final payment of ₦{result['final_payment']:,.0f} released."
            if result.get('cold_chain_bonus', 0) > 0:
                msg += f" Cold chain bonus: ₦{result['cold_chain_bonus']:,.0f}"
            flash(msg, 'success')
        else:
            flash(result.get('error', 'Failed to complete delivery.'), 'danger')
    else:
        logistics_request.status = 'delivered'
        db.session.commit()
        flash('Delivery marked as complete!', 'success')
    
    return redirect(url_for('logistics_request_detail', request_id=request_id))


@app.route('/coldchain/webhook', methods=['POST'])
@csrf_exempt
def coldchain_webhook():
    """Receive temperature data from cold chain devices"""
    import hmac
    import hashlib
    
    # Verify webhook signature
    webhook_secret = os.environ.get('COLDCHAIN_WEBHOOK_SECRET', '')
    if webhook_secret:
        signature = request.headers.get('X-Webhook-Signature', '')
        expected = hmac.new(
            webhook_secret.encode(),
            request.data,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return jsonify({'error': 'Invalid signature'}), 401
    
    try:
        data = request.get_json()
        
        device_id = data.get('device_id')
        job_id = data.get('job_id') or data.get('logistics_request_id')
        temperature = data.get('temperature')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([device_id, job_id, temperature is not None]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Verify device exists
        device = ColdChainDevice.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': 'Unknown device'}), 404
        
        # Create log entry
        log = ColdChainLog(
            device_id=device_id,
            logistics_request_id=int(job_id),
            temperature_celsius=float(temperature),
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None
        )
        
        db.session.add(log)
        
        # Update device last reading
        device.last_reading_at = datetime.utcnow()
        
        db.session.commit()
        
        # Check for temperature alerts
        alert = None
        if not log.is_within_range(device.max_temp_allowed, device.min_temp_allowed):
            alert = f"Temperature {temperature}°C out of range ({device.min_temp_allowed}°C - {device.max_temp_allowed}°C)"
            app.logger.warning(f"Cold chain alert for job {job_id}: {alert}")
        
        return jsonify({
            'status': 'recorded',
            'log_id': log.id,
            'alert': alert
        })
        
    except Exception as e:
        app.logger.error(f"Cold chain webhook error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/logistics/<int:request_id>/temperature')
@login_required
def temperature_chart_data(request_id):
    """Get temperature data for Chart.js"""
    logs = ColdChainLog.query.filter_by(logistics_request_id=request_id)\
                             .order_by(ColdChainLog.timestamp.asc()).all()
    
    data = {
        'labels': [log.timestamp.strftime('%H:%M') for log in logs],
        'temperatures': [log.temperature_celsius for log in logs],
        'locations': [
            {'lat': log.latitude, 'lng': log.longitude}
            for log in logs if log.latitude and log.longitude
        ]
    }
    
    # Get device limits
    if logs:
        device = ColdChainDevice.query.filter_by(device_id=logs[0].device_id).first()
        if device:
            data['max_temp'] = device.max_temp_allowed
            data['min_temp'] = device.min_temp_allowed
    
    return jsonify(data)


@app.route('/admin/logistics-bidding')
@login_required
def admin_logistics_bidding():
    """Admin logistics dashboard with bidding analytics"""
    if not current_user.is_admin():
        abort(403)
    
    # Get all logistics requests with stats
    all_requests = LogisticsRequest.query.order_by(LogisticsRequest.timestamp.desc()).all()
    
    # Calculate statistics
    total_requests = len(all_requests)
    active_requests = sum(1 for r in all_requests if r.status in ['pending', 'bidding', 'assigned', 'in_transit'])
    completed_requests = sum(1 for r in all_requests if r.status == 'delivered')
    cold_chain_requests = sum(1 for r in all_requests if r.requires_cold_chain)
    
    # Cold chain verification stats
    cold_chain_verified = sum(1 for r in all_requests if r.cold_chain_bonus_earned)
    cold_chain_rate = (cold_chain_verified / cold_chain_requests * 100) if cold_chain_requests > 0 else 0
    
    # Get all bids
    all_bids = LogisticsBid.query.all()
    total_bids = len(all_bids)
    accepted_bids = sum(1 for b in all_bids if b.status == 'accepted')
    
    # Calculate average cost per ton
    completed_with_bids = [r for r in all_requests if r.status == 'delivered' and r.winning_bid]
    if completed_with_bids:
        total_cost = sum(r.winning_bid.bid_amount for r in completed_with_bids)
        total_tons = sum(r.quantity_tons or 1 for r in completed_with_bids)
        avg_cost_per_ton = total_cost / total_tons
    else:
        avg_cost_per_ton = 0
    
    # Get top transporters
    transporters = TransportProfile.query.order_by(TransportProfile.total_trips.desc()).limit(10).all()
    
    stats = {
        'total_requests': total_requests,
        'active_requests': active_requests,
        'completed_requests': completed_requests,
        'total_bids': total_bids,
        'accepted_bids': accepted_bids,
        'cold_chain_requests': cold_chain_requests,
        'cold_chain_verified': cold_chain_verified,
        'cold_chain_rate': cold_chain_rate,
        'avg_cost_per_ton': avg_cost_per_ton,
        'total_transporters': TransportProfile.query.count()
    }
    
    return render_template('admin/logistics_bidding.html',
                         requests=all_requests[:50],
                         transporters=transporters,
                         stats=stats,
                         title='Logistics & Bidding Dashboard')


# ==================== SABIBUY GROUP-BUY ROUTES ====================

@app.route('/sabibuy')
def sabibuy_home():
    """SabiBuy home page - browse active campaigns"""
    campaigns = SabiBuy.query.filter_by(status='active').order_by(SabiBuy.created_at.desc()).limit(20).all()
    
    return render_template('sabibuy/index.html',
                         campaigns=campaigns,
                         title='SabiBuy - Group Buy Marketplace')

@app.route('/sabibuy/campaign/<code>')
def sabibuy_campaign(code):
    """View a specific SabiBuy campaign"""
    campaign = SabiBuy.query.filter_by(code=code.upper()).first_or_404()
    produce = Produce.query.get(campaign.produce_id)
    organizer = User.query.get(campaign.organizer_id)
    orders = SabiBuyOrder.query.filter_by(sabibuy_id=campaign.id, payment_status='paid').all()
    
    progress = int((campaign.current_quantity / campaign.minimum_quantity * 100)) if campaign.minimum_quantity > 0 else 0
    
    return render_template('sabibuy/campaign.html',
                         campaign=campaign,
                         produce=produce,
                         organizer=organizer,
                         orders=orders,
                         progress=min(progress, 100),
                         title=f'SabiBuy - {code}')

@app.route('/sabibuy/join/<code>', methods=['GET', 'POST'])
def sabibuy_join(code):
    """Join a SabiBuy campaign"""
    campaign = SabiBuy.query.filter_by(code=code.upper()).first_or_404()
    
    if campaign.status != 'active':
        flash('This SabiBuy campaign is no longer accepting orders.', 'warning')
        return redirect(url_for('sabibuy_campaign', code=code))
    
    produce = Produce.query.get(campaign.produce_id)
    
    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 1))
        buyer_name = request.form.get('buyer_name', '')
        buyer_phone = request.form.get('buyer_phone', '')
        
        if quantity < 1:
            flash('Please enter a valid quantity.', 'error')
            return render_template('sabibuy/join.html', campaign=campaign, produce=produce)
        
        remaining = campaign.maximum_quantity - campaign.current_quantity
        if quantity > remaining:
            flash(f'Only {remaining} units available.', 'error')
            return render_template('sabibuy/join.html', campaign=campaign, produce=produce)
        
        from services.sabibuy_service import sabibuy_service
        
        buyer_id = current_user.id if current_user.is_authenticated else None
        if not buyer_name and current_user.is_authenticated:
            buyer_name = current_user.name
        if not buyer_phone and current_user.is_authenticated:
            buyer_phone = getattr(current_user, 'phone_number', '')
        
        result = sabibuy_service.join_campaign(
            code=code,
            buyer_phone=buyer_phone,
            quantity=quantity,
            buyer_name=buyer_name,
            buyer_id=buyer_id,
            payment_method='pending',
            source_channel='web'
        )
        
        if result.get('success'):
            flash(f'Order placed! Total: ₦{result.get("total_amount", 0):,.0f}', 'success')
            return redirect(url_for('sabibuy_payment', order_id=result.get('order_id')))
        else:
            flash(result.get('error', 'Failed to place order'), 'error')
    
    return render_template('sabibuy/join.html',
                         campaign=campaign,
                         produce=produce,
                         title=f'Join SabiBuy - {code}')

@app.route('/sabibuy/payment/<int:order_id>')
def sabibuy_payment(order_id):
    """Payment page for SabiBuy order"""
    order = SabiBuyOrder.query.get_or_404(order_id)
    campaign = SabiBuy.query.get(order.sabibuy_id)
    produce = Produce.query.get(campaign.produce_id) if campaign else None
    
    return render_template('sabibuy/payment.html',
                         order=order,
                         campaign=campaign,
                         produce=produce,
                         title='Complete Payment')

@app.route('/sabibuy/start', methods=['GET', 'POST'])
@login_required
def sabibuy_start():
    """Start a new SabiBuy campaign"""
    produce_list = Produce.query.filter_by(is_available=True).order_by(Produce.date_listed.desc()).limit(50).all()
    
    if request.method == 'POST':
        produce_id = int(request.form.get('produce_id', 0))
        selling_price = float(request.form.get('selling_price', 0))
        delivery_lga = request.form.get('delivery_lga', '')
        delivery_market = request.form.get('delivery_market', '')
        delivery_state = request.form.get('delivery_state', 'Lagos')
        minimum_quantity = int(request.form.get('minimum_quantity', 50))
        
        from services.sabibuy_service import sabibuy_service
        
        result = sabibuy_service.create_campaign(
            organizer_id=current_user.id,
            produce_id=produce_id,
            selling_price=selling_price,
            delivery_lga=delivery_lga,
            delivery_market=delivery_market,
            delivery_state=delivery_state,
            minimum_quantity=minimum_quantity,
            source_channel='web'
        )
        
        if result.get('success'):
            code = result.get('code', '')
            flash(f'SabiBuy created! Share code: {code}', 'success')
            return redirect(url_for('sabibuy_campaign', code=code))
        else:
            flash(result.get('error', 'Failed to create SabiBuy'), 'error')
    
    return render_template('sabibuy/start.html',
                         produce_list=produce_list,
                         title='Start SabiBuy')

@app.route('/sabibuy/my-campaigns')
@login_required
def sabibuy_my_campaigns():
    """View user's SabiBuy campaigns"""
    campaigns = SabiBuy.query.filter_by(organizer_id=current_user.id).order_by(SabiBuy.created_at.desc()).all()
    
    profile = SabiBuyerProfile.query.filter_by(user_id=current_user.id).first()
    
    return render_template('sabibuy/my_campaigns.html',
                         campaigns=campaigns,
                         profile=profile,
                         title='My SabiBuys')

@app.route('/sabibuy/my-orders')
@login_required
def sabibuy_my_orders():
    """View user's SabiBuy orders"""
    orders = SabiBuyOrder.query.filter_by(buyer_id=current_user.id).order_by(SabiBuyOrder.created_at.desc()).all()
    
    return render_template('sabibuy/my_orders.html',
                         orders=orders,
                         title='My SabiBuy Orders')

@app.route('/sabibuy/leaderboard')
def sabibuy_leaderboard():
    """SabiBuy leaderboard showing top SabiBuyers"""
    top_sabibuyers = SabiBuyerProfile.query.order_by(SabiBuyerProfile.total_earnings.desc()).limit(20).all()
    
    return render_template('sabibuy/leaderboard.html',
                         top_sabibuyers=top_sabibuyers,
                         title='SabiBuyer Leaderboard')

@app.route('/admin/sabibuy')
@login_required
def admin_sabibuy():
    """Admin SabiBuy dashboard"""
    if not current_user.is_admin():
        abort(403)
    
    all_campaigns = SabiBuy.query.order_by(SabiBuy.created_at.desc()).limit(50).all()
    all_orders = SabiBuyOrder.query.order_by(SabiBuyOrder.created_at.desc()).limit(50).all()
    
    total_gmv = db.session.query(db.func.sum(SabiBuyOrder.total_amount)).filter_by(payment_status='paid').scalar() or 0
    total_campaigns = SabiBuy.query.count()
    active_campaigns = SabiBuy.query.filter_by(status='active').count()
    total_orders = SabiBuyOrder.query.count()
    paid_orders = SabiBuyOrder.query.filter_by(payment_status='paid').count()
    total_sabibuyers = SabiBuyerProfile.query.count()
    captains = SabiBuyerProfile.query.filter(SabiBuyerProfile.tier.in_(['captain', 'premium'])).count()
    
    stats = {
        'total_gmv': total_gmv,
        'total_campaigns': total_campaigns,
        'active_campaigns': active_campaigns,
        'total_orders': total_orders,
        'paid_orders': paid_orders,
        'conversion_rate': (paid_orders / total_orders * 100) if total_orders > 0 else 0,
        'total_sabibuyers': total_sabibuyers,
        'captains': captains
    }
    
    top_sabibuyers = SabiBuyerProfile.query.order_by(SabiBuyerProfile.total_earnings.desc()).limit(10).all()
    
    return render_template('admin/sabibuy_dashboard.html',
                         campaigns=all_campaigns,
                         orders=all_orders,
                         stats=stats,
                         top_sabibuyers=top_sabibuyers,
                         title='SabiBuy Admin Dashboard')

@app.route('/sabibuy/upgrade')
@login_required
def sabibuy_upgrade():
    """Tier upgrade page"""
    profile = SabiBuyerProfile.query.filter_by(user_id=current_user.id).first()
    
    tiers = {
        'free': {
            'name': 'Free',
            'price': 0,
            'features': ['Up to 3 active campaigns', 'Standard support', 'Basic analytics']
        },
        'captain': {
            'name': 'Captain',
            'price': 5000,
            'price_type': 'one_time',
            'features': ['Unlimited campaigns', 'Gold badge on listings', 'Priority support', 'Advanced analytics']
        },
        'premium': {
            'name': 'Premium',
            'price': 10000,
            'price_type': 'monthly',
            'features': ['All Captain features', 'Featured listings', 'Highest profit limits', 'Dedicated account manager']
        }
    }
    
    return render_template('sabibuy/upgrade.html',
                         profile=profile,
                         tiers=tiers,
                         title='Upgrade SabiBuyer Tier')

@app.route('/sabibuy/upgrade/<tier>', methods=['POST'])
@login_required
def process_tier_upgrade(tier):
    """Process tier upgrade payment"""
    if tier not in ['captain', 'premium']:
        flash('Invalid tier selected', 'error')
        return redirect(url_for('sabibuy_upgrade'))
    
    profile = SabiBuyerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = SabiBuyerProfile(
            user_id=current_user.id,
            tier='free'
        )
        db.session.add(profile)
        db.session.commit()
    
    if tier == 'captain' and profile.tier in ['captain', 'premium']:
        flash('You already have Captain or higher tier', 'info')
        return redirect(url_for('sabibuy_my_campaigns'))
    
    amount = 5000 if tier == 'captain' else 10000
    
    if payment_service:
        try:
            reference = payment_service.generate_reference(f"sabibuy_{tier}")
            callback_url = url_for('sabibuy_upgrade_callback', _external=True)
            
            payment_response = payment_service.initialize_transaction(
                email=current_user.email,
                amount=amount,
                reference=reference,
                callback_url=callback_url,
                metadata={
                    'user_id': current_user.id,
                    'tier': tier,
                    'type': 'sabibuy_upgrade'
                }
            )
            
            if payment_response.get('status'):
                transaction = Transaction(
                    reference=reference,
                    user_id=current_user.id,
                    transaction_type=f'sabibuy_{tier}_upgrade',
                    base_amount=amount,
                    platform_fee=0,
                    total_amount=amount
                )
                db.session.add(transaction)
                db.session.commit()
                
                return redirect(payment_response['data']['authorization_url'])
            else:
                flash('Payment initialization failed', 'error')
        except Exception as e:
            app.logger.error(f"Tier upgrade payment error: {e}")
            flash('Payment service error', 'error')
    else:
        flash('Payment service unavailable', 'error')
    
    return redirect(url_for('sabibuy_upgrade'))

@app.route('/sabibuy/upgrade/callback')
def sabibuy_upgrade_callback():
    """Handle tier upgrade payment callback"""
    reference = request.args.get('reference')
    
    if not reference:
        flash('Invalid payment reference', 'error')
        return redirect(url_for('sabibuy_upgrade'))
    
    if payment_service:
        try:
            verification = payment_service.verify_transaction(reference)
            
            if verification.get('status') and verification['data']['status'] == 'success':
                transaction = Transaction.query.filter_by(reference=reference).first()
                
                if transaction:
                    transaction.status = 'completed'
                    transaction.paystack_reference = verification['data']['reference']
                    
                    tier = 'captain' if 'captain' in transaction.transaction_type else 'premium'
                    
                    profile = SabiBuyerProfile.query.filter_by(user_id=transaction.user_id).first()
                    if profile:
                        profile.tier = tier
                        if tier == 'captain':
                            profile.captain_since = datetime.utcnow()
                        else:
                            profile.premium_expires = datetime.utcnow() + timedelta(days=30)
                    
                    db.session.commit()
                    flash(f'Successfully upgraded to {tier.title()}!', 'success')
                    return redirect(url_for('sabibuy_my_campaigns'))
                else:
                    flash('Transaction not found', 'error')
            else:
                flash('Payment verification failed', 'error')
        except Exception as e:
            app.logger.error(f"Tier upgrade callback error: {e}")
            flash('Verification error', 'error')
    else:
        flash('Payment service unavailable', 'error')
    
    return redirect(url_for('sabibuy_upgrade'))


@app.route('/simulator/ussd')
def ussd_simulator():
    """USSD Simulator for demo and testing"""
    return render_template('simulator/ussd_simulator.html', title='USSD Simulator')

@app.route('/simulator/sms')
def sms_simulator():
    """SMS Simulator for demo and testing"""
    return render_template('simulator/sms_simulator.html', title='SMS Simulator')

@app.route('/simulator/ussd/api', methods=['POST'])
@csrf_exempt
def ussd_simulator_api():
    """API endpoint for USSD simulator"""
    from ussd_service import ussd_service
    
    data = request.get_json(silent=True) or {}
    session_id = data.get('sessionId', 'SIM_' + str(datetime.utcnow().timestamp()))
    phone_number = data.get('phoneNumber', '+2348012345678')
    text = data.get('text', '')
    service_code = data.get('serviceCode', '*712*55#')
    
    try:
        result = ussd_service.process_request(
            session_id=session_id,
            phone_number=phone_number,
            text=text,
            service_code=service_code
        )
        
        # process_request returns (response_text, should_continue) tuple
        if isinstance(result, tuple):
            response_text, should_continue = result
            return jsonify({'response': response_text, 'continue': should_continue})
        else:
            # Fallback for string response
            response = str(result)
            if response.startswith('CON '):
                return jsonify({'response': response[4:], 'continue': True})
            elif response.startswith('END '):
                return jsonify({'response': response[4:], 'continue': False})
            else:
                return jsonify({'response': response, 'continue': True})
    except Exception as e:
        app.logger.error(f"USSD simulator error: {e}")
        return jsonify({'response': f'Error: {str(e)}', 'continue': False})

@app.route('/simulator/sms/api', methods=['POST'])
@csrf_exempt
def sms_simulator_api():
    """API endpoint for SMS simulator"""
    from sms_service import sms_service
    
    data = request.get_json(silent=True) or {}
    phone_number = data.get('phoneNumber', '+2348012345678')
    message = data.get('message', '')
    
    try:
        response = sms_service.process_incoming_sms(phone_number, message)
        return jsonify({'response': response or 'Message processed successfully'})
    except Exception as e:
        app.logger.error(f"SMS simulator error: {e}")
        return jsonify({'response': f'Error processing message. Please try again.'})
