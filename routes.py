from flask import render_template, url_for, flash, redirect, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app import app, db
from models import User, Produce
from forms import RegistrationForm, LoginForm, ProduceForm, SearchForm
from config import PRODUCE_IMAGE_MAP, DEFAULT_PRODUCE_IMAGE, FEATURED_PRODUCE

@app.route('/')
def home():
    """Homepage route with featured produce data"""
    # Build featured produce data with images from mapping
    featured_produce_data = {}
    for produce_name, produce_info in FEATURED_PRODUCE.items():
        featured_produce_data[produce_name] = {
            'image': PRODUCE_IMAGE_MAP.get(produce_name, DEFAULT_PRODUCE_IMAGE),
            'description': produce_info['description']
        }
    
    return render_template('home.html', 
                         title='Welcome to AgroLink',
                         featured_produce=featured_produce_data, 
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
    
    return render_template('farmer_dashboard.html', 
                         title='Farmer Dashboard', 
                         produce_listings=produce_listings)

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
        'available_produce': Produce.query.filter_by(is_available=True).count()
    }
    
    return render_template('admin_dashboard.html', 
                         title='Admin Dashboard', 
                         users=users, 
                         produce_listings=produce_listings,
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
