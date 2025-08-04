# AgroLink Lagos

AgroLink Lagos is a digital platform that connects farmers and buyers to support the "Produce for Lagos" food security initiative. Built with Flask and designed to strengthen local agricultural supply chains.

## Features

### 🌱 For Farmers
- **Produce Management**: Add, edit, and manage produce listings
- **Dashboard**: Track all your listings and their status
- **Direct Contact**: Connect directly with interested buyers
- **Real-time Updates**: Update quantity and availability instantly

### 🛒 For Buyers
- **Marketplace**: Browse fresh produce from verified farmers
- **Search & Filter**: Find specific produce quickly
- **Farmer Profiles**: View farmer details and other listings
- **Direct Communication**: Contact farmers via email

### 👨‍💼 For Admins
- **User Management**: Oversee all registered users
- **Platform Oversight**: Monitor produce listings and activity
- **Statistics**: View platform usage and growth metrics
- **Read-only Access**: Safe oversight without modification rights

## Tech Stack

- **Backend**: Flask, SQLAlchemy, SQLite
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Authentication**: Flask-Login with secure password hashing
- **Security**: CSRF protection, role-based access control
- **Database**: SQLite for easy deployment and setup

## Quick Start

### Prerequisites
- Python 3.7+
- Flask and dependencies (see requirements in code)

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install flask flask-sqlalchemy flask-login flask-wtf werkzeug
   ```

3. **Set environment variables**:
   ```bash
   export SESSION_SECRET="your-secret-key-here"
   export DATABASE_URL="sqlite:///agrolink.db"
   ```

4. **Initialize the database**:
   ```bash
   python init_db.py
   ```

5. **Run the application**:
   ```bash
   python main.py
   ```

6. **Access the application**:
   Open your browser and go to `http://localhost:5000`

### For Replit Deployment

1. **Upload all files to your Replit project**

2. **Set Environment Variables in Replit**:
   - Go to the "Secrets" tab in Replit
   - Add `SESSION_SECRET` with a secure random string
   - Add `DATABASE_URL` with value `sqlite:///agrolink.db`

3. **Run the initialization**:
   ```bash
   python init_db.py
   