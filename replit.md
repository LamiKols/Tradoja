# AgroLink

## Overview

AgroLink is a comprehensive digital agricultural marketplace platform that connects farmers and buyers across Africa, starting with Lagos' food security initiative and expanding continent-wide. The platform enables farmers to list their produce, buyers to browse and search for fresh products, and administrators to oversee platform operations. Built as a Flask web application, it provides role-based access control with distinct user experiences for farmers, buyers, and admins.

## Recent Changes (August 2025)

- **Dashboard Navigation**: Fixed home button to redirect authenticated users to their appropriate dashboards (farmer/buyer/admin) instead of landing page
- **Funding Portal**: Implemented comprehensive Offtake Guarantee Fund system with application forms, document uploads, and admin approval workflow
- **Logistics System**: Added delivery/pickup request system with status tracking and admin management
- **User Experience**: Enhanced role-based redirects for seamless navigation after login/registration

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask**: Core web framework providing routing, templating, and request handling
- **SQLAlchemy**: Object-relational mapping for database operations with model-based data access
- **Flask-Login**: Session management and user authentication with secure login/logout functionality
- **Flask-WTF**: Form handling with CSRF protection and input validation

### Database Design
- **SQLite**: Lightweight database for development and easy deployment
- **User Model**: Stores user information with role-based access (farmer, buyer, admin)
- **Produce Model**: Manages product listings with farmer relationships via foreign keys
- **Database relationships**: One-to-many between users and produce listings

### Authentication & Security
- **Password Security**: Werkzeug-based password hashing with secure storage
- **CSRF Protection**: Cross-site request forgery prevention on all forms
- **Role-based Access**: Three-tier user system with distinct permissions and dashboard views
- **Session Management**: Secure session handling with configurable secret keys

### Frontend Architecture
- **Bootstrap 5**: Responsive UI framework with dark theme support
- **Jinja2 Templates**: Server-side rendering with template inheritance
- **Font Awesome**: Icon library for consistent visual elements
- **Responsive Design**: Mobile-first approach with adaptive layouts

### Application Structure
- **Modular Design**: Separation of concerns with distinct files for models, forms, routes, and templates
- **Blueprint Pattern**: Organized route handling with clear separation of functionality
- **Template Inheritance**: Base template system for consistent layout and styling

## External Dependencies

### Frontend Libraries
- **Bootstrap 5**: Styling framework loaded via CDN
- **Font Awesome 6**: Icon library for UI elements
- **Custom CSS**: Dark theme implementation with Bootstrap variables

### Python Packages
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: User session management
- **Flask-WTF**: Form handling and validation
- **Werkzeug**: Password hashing and security utilities
- **WTForms**: Form validation and rendering

### Infrastructure
- **SQLite Database**: File-based database storage
- **Environment Variables**: Configuration management for secrets and database URLs
- **Replit Hosting**: Cloud-based development and deployment platform