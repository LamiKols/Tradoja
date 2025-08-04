# AgroLink

## Overview

AgroLink is a comprehensive digital agricultural marketplace platform that connects farmers and buyers across Africa, starting with Lagos' food security initiative and expanding continent-wide. The platform enables farmers to list their produce, buyers to browse and search for fresh products, and administrators to oversee platform operations. Built as a Flask web application, it provides role-based access control with distinct user experiences for farmers, buyers, and admins.

## Recent Changes (August 2025)

- **Dashboard Navigation**: Home button correctly redirects authenticated users to their appropriate dashboards (farmer/buyer/admin) instead of landing page. Navigation logic ensures role-based redirection for seamless user experience
- **Funding Portal**: Implemented comprehensive Offtake Guarantee Fund system with application forms, document uploads, and admin approval workflow
- **Logistics System**: Added delivery/pickup request system with status tracking and admin management
- **User Experience**: Enhanced role-based redirects for seamless navigation after login/registration
- **Climate-Smart Agriculture (CSA) Tool**: Added comprehensive weather integration with OpenWeatherMap API, soil analysis forms, crop recommendations engine, and carbon footprint calculator for sustainable farming practices
- **Cross-Border Trade Module**: Implemented comprehensive export listings system with phytosanitary certification uploads, international standards compliance tracking, trade data integration, and admin approval workflow for global market access
- **Geographical Indications (GI) Module**: Added complete GI certification system with Nigerian GI registry, farmer GI claims, admin verification workflow, marketplace GI filtering, and premium product designation for authentic regional agricultural products
- **SMS Gateway Integration**: Complete Africa's Talking SMS service integration with webhook processing, command system (JOIN, LIST, PRICE, HELP), admin dashboard with metrics and testing interface, and rural farmer accessibility via text messages
- **AI-Powered Matchmaking Engine**: Implemented intelligent buyer-seller recommendations using rule-based algorithms with crop type, location, quantity, price range, and reliability scoring. Includes web dashboard recommendations, SMS match alerts, accept/decline tracking, and admin analytics for ML training data collection
- **Advanced Analytics Dashboard**: Comprehensive analytics platform providing market insights, crop performance data, geographic distribution analysis, user engagement metrics, bottleneck identification with intervention recommendations, and CSV/PDF export capabilities for government and partner reporting
- **Monetization Features**: Complete payment infrastructure with Paystack integration including transaction fees on marketplace trades, logistics service fees, premium user subscriptions, purchase history tracking, and comprehensive payment analytics dashboard

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
- **Enhanced Produce Model**: Extended with comprehensive GI fields (gi_label, gi_certified, gi_status, gi_certificate_number, gi_admin_comment) for geographical indication certification management
- **Enhanced User Model**: Added SMS integration fields (phone_number, sms_enabled, sms_registration_date) for rural farmer accessibility
- **SMSInteraction Model**: Complete SMS communication logging and metrics tracking system
- **Database relationships**: Complex relationships supporting comprehensive agricultural marketplace operations including SMS integration

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
- **GI Service**: Comprehensive geographical indications service managing Nigerian GI registry, validation, search functionality, and certification requirements for premium agricultural products
- **Africa's Talking SMS API**: SMS gateway integration for rural farmer accessibility with webhook processing, command system, and admin management tools
- **Environment Variables**: Secure API key management through Replit Secrets

### Infrastructure
- **SQLite Database**: File-based database storage
- **Environment Variables**: Configuration management for secrets and database URLs
- **Replit Hosting**: Cloud-based development and deployment platform