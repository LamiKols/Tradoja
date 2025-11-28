# AgroLink

## Overview

AgroLink is a comprehensive digital agricultural marketplace platform that connects farmers and buyers across Africa, starting with Lagos' food security initiative and expanding continent-wide. The platform enables farmers to list their produce, buyers to browse and search for fresh products, and administrators to oversee platform operations. Built as a Flask web application, it provides role-based access control with distinct user experiences for farmers, buyers, and admins.

## Recent Changes (November 2025)

- **Digital Inclusion Layer**: Comprehensive multi-channel access system enabling 90% of rural Nigerian farmers with feature phones to use the platform:
  - **USSD Access (*712*55#)**: 5-option menu system (List Produce, Check Prices, My Listings, Balance, Register) with Africa's Talking and T2 (9mobile) integration
  - **Enhanced SMS Commands**: Extended LIST command supporting location (LIST RICE 50BAGS 45000 ONITSHA), match acceptance/decline via SMS
  - **Multilingual Support**: Full message templates in English, Yoruba, Hausa, Pidgin, and Igbo languages
  - **Agent-Assisted Onboarding**: Field agent dashboard for registering farmers, single and bulk registration capabilities
  - **Digital Inclusion Dashboard**: Admin analytics showing channel distribution, language preferences, and registration metrics
- **USSD Session Management**: USSDSession model with session state tracking, menu navigation, and 5-minute timeout handling
- **WhatsApp Integration Foundation**: WhatsAppInteraction model ready for Meta WhatsApp Cloud API with voice note transcription support
- **T2 Wallet Integration Foundation**: User fields for T2/9mobile wallet (t2_customer_code, t2_wallet_balance) for unbanked farmer payments

## Previous Changes (August 2025)

- **Dashboard Navigation**: Home button correctly redirects authenticated users to their appropriate dashboards (farmer/buyer/admin) instead of landing page. Navigation logic ensures role-based redirection for seamless user experience. Buyer dashboard completely redesigned with proper overview layout instead of marketplace view
- **UI Improvements**: Fixed text and container fitting issues in marketplace cards with proper text truncation, consistent card heights, and improved responsive layout
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
- **Universal Onboarding Workflow**: Comprehensive Produce for Lagos program registration system supporting 9 role types (farmer, aggregator, transport company, bulk trader, retailer, input supplier, investor, government agency, NGO/dev partner) with multi-step forms, document uploads, progress tracking, admin review workflow, and bulk onboarding capabilities for government compliance

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
- **Enhanced User Model**: Added SMS integration fields (phone_number, sms_enabled, sms_registration_date) plus digital inclusion fields (whatsapp_id, t2_customer_code, preferred_language, is_ussd_user, t2_wallet_balance, source_channel, registered_by_agent_id) for comprehensive multi-channel accessibility
- **SMSInteraction Model**: Complete SMS communication logging and metrics tracking system
- **USSDSession Model**: USSD session tracking with menu state, step progression, session data JSON storage, and automatic expiry handling
- **WhatsAppInteraction Model**: WhatsApp message tracking with voice note transcription support and language detection
- **ProduceLagosRegistration Model**: Comprehensive universal onboarding system with multi-step registration, role-specific fields, document upload paths, progress tracking, and admin review workflow
- **BulkOnboarding Model**: Bulk registration processing system for admin management of large-scale onboarding operations
- **Database relationships**: Complex relationships supporting comprehensive agricultural marketplace operations including SMS, USSD, WhatsApp integration and universal onboarding workflow

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
- **Africa's Talking USSD API**: USSD gateway for feature phone access with session management and menu navigation
- **Multilingual Service**: Language detection and message templating for English, Yoruba, Hausa, Pidgin, and Igbo
- **Environment Variables**: Secure API key management through Replit Secrets

### Infrastructure
- **PostgreSQL Database**: Scalable production-ready database storage
- **Environment Variables**: Configuration management for secrets and database URLs
- **Replit Hosting**: Cloud-based development and deployment platform

### Digital Inclusion Channels
- **USSD Shortcode**: *712*55# for feature phone access
- **SMS Commands**: JOIN, LIST, PRICE, HELP, ACCEPT, DECLINE, STOP
- **Agent Portal**: /agent/dashboard for field registration
- **Admin Dashboards**: /admin/ussd-dashboard, /admin/digital-inclusion for metrics