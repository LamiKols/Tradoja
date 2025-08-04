# AgroLink

## Overview

AgroLink is a comprehensive digital agricultural marketplace platform that connects farmers and buyers across Africa, starting with Lagos' food security initiative and expanding continent-wide. The platform enables farmers to list their produce, buyers to browse and search for fresh products, and administrators to oversee platform operations. Built as a Flask web application, it provides role-based access control with distinct user experiences for farmers, buyers, and admins.

## Recent Changes (August 2025)

- **Dashboard Navigation**: Fixed home button to redirect authenticated users to their appropriate dashboards (farmer/buyer/admin) instead of landing page
- **Funding Portal**: Implemented comprehensive Offtake Guarantee Fund system with application forms, document uploads, and admin approval workflow
- **Logistics System**: Added delivery/pickup request system with status tracking and admin management
- **User Experience**: Enhanced role-based redirects for seamless navigation after login/registration
- **Climate-Smart Agriculture (CSA) Tool**: Added comprehensive weather integration with OpenWeatherMap API, soil analysis forms, crop recommendations engine, and carbon footprint calculator for sustainable farming practices
- **Cross-Border Trade Module**: Implemented comprehensive export listings system with phytosanitary certification uploads, international standards compliance tracking, trade data integration, and admin approval workflow for global market access

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask**: Core web framework providing routing, templating, and request handling
- **SQLAlchemy**: Object-relational mapping for database operations with model-based data access
- **Flask-Login**: Session management and user authentication with secure login/logout functionality
- **Flask-WTF**: Form handling with CSRF protection and input validation

### Database Design
- **PostgreSQL**: Scalable database for production-ready deployment
- **User Model**: Stores user information with role-based access (farmer, buyer, admin)
- **Produce Model**: Manages product listings with farmer relationships via foreign keys
- **Message Model**: In-platform messaging system between farmers and buyers
- **LogisticsRequest Model**: Delivery/pickup coordination system
- **FundingApplication Model**: Offtake Guarantee Fund application management
- **CSAData Model**: Climate-Smart Agriculture data storage for weather, soil, and carbon footprint analysis
- **ExportListing Model**: Cross-border trade listings with certification tracking, compliance standards, and international market targeting
- **Database relationships**: Complex relationships supporting comprehensive agricultural marketplace operations

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
- **Requests**: HTTP library for API integration
- **Psycopg2**: PostgreSQL adapter for Python
- **Trafilatura**: Web scraping capabilities

### API Integrations
- **OpenWeatherMap API**: Real-time weather data for climate-smart agriculture
- **Trade Data Service**: Mock trade data service providing Nigerian agricultural export market trends and pricing information
- **Environment Variables**: Secure API key management through Replit Secrets

### Infrastructure
- **SQLite Database**: File-based database storage
- **Environment Variables**: Configuration management for secrets and database URLs
- **Replit Hosting**: Cloud-based development and deployment platform