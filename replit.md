# AgroLink

## Overview

AgroLink is a digital agricultural marketplace connecting farmers and buyers across Africa, with an initial focus on Lagos to address food security. The platform enables farmers to list produce, buyers to browse products, and administrators to manage operations. It is a Flask web application featuring role-based access for farmers, buyers, and admins. The project aims to enhance food security, empower farmers, and streamline agricultural supply chains through advanced features like AI-powered scam detection, comprehensive logistics, digital inclusion for rural farmers, and climate-smart agriculture tools.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask**: Core web framework for routing, templating, and request handling.
- **SQLAlchemy**: ORM for database operations and model-based data access.
- **Flask-Login**: User authentication and session management.
- **Flask-WTF**: Form handling, CSRF protection, and input validation.

### Database Design
- **PostgreSQL**: Scalable production database.
- **Core Models**: User (role-based), Produce (listings), Message (in-platform communication), LogisticsRequest (delivery/pickup), FundingApplication (Offtake Guarantee), CSAData (climate-smart agriculture), ExportListing (cross-border trade), SMSInteraction, USSDSession, WhatsAppInteraction.
- **Enhanced Models**: Produce (Geographical Indication fields), User (digital inclusion fields for SMS, USSD, WhatsApp, and T2 Wallet).
- **Logistics Models**: TransportProfile, ColdChainDevice, ColdChainLog, LogisticsBid.
- **Onboarding Models**: ProduceLagosRegistration (universal onboarding), BulkOnboarding.
- **Scam Detection Model**: ScamFlag (tracks detections with status).
- **Complex Relationships**: Supports comprehensive marketplace operations, multi-channel integration, and universal onboarding.

### Authentication & Security
- **Password Security**: Werkzeug-based password hashing.
- **CSRF Protection**: Prevents cross-site request forgery.
- **Role-based Access**: Three-tier system (farmer, buyer, admin) with distinct permissions.
- **Session Management**: Secure session handling.

### Frontend Architecture
- **Bootstrap 5**: Responsive UI framework with dark theme support.
- **Jinja2 Templates**: Server-side rendering with template inheritance.
- **Font Awesome**: Icon library.
- **Responsive Design**: Mobile-first approach.

### Application Structure
- **Modular Design**: Separation of concerns for models, forms, routes, and templates.
- **Blueprint Pattern**: Organized route handling.
- **Template Inheritance**: Consistent layout and styling.

### Feature Specifications
- **AI Scam Detector**: Rules-based fraud detection (8 rules targeting registration, listings, payments, and transport) with an admin dashboard for review and action (ban/approve/agent call). Includes automatic integration into user flows and SMS admin alerts for high-score detections.
- **Full Logistics & Transport Layer**: Transport company registration (fleet, cold chain), intelligent matching algorithm (weighted scoring), multi-channel bidding (web, USSD, SMS), real-time cold chain IoT tracking (Chart.js, webhooks, alerts), payment escrow, and an admin logistics dashboard.
- **Digital Inclusion Layer**: Multi-channel access via USSD (*712*55#) and extended SMS commands for rural farmers. Features USSD session management, buyer/transporter LITE registration, multilingual support (English, Yoruba, Hausa, Pidgin, Igbo), agent-assisted onboarding, and a digital inclusion analytics dashboard. WhatsApp integration foundation is also included.
- **Funding Portal**: Offtake Guarantee Fund system with application forms and admin approval.
- **Climate-Smart Agriculture (CSA) Tool**: Weather integration (OpenWeatherMap), soil analysis, crop recommendations, and carbon footprint calculator.
- **Cross-Border Trade Module**: Export listings, phytosanitary certification, international standards compliance, and admin approval.
- **Geographical Indications (GI) Module**: GI certification registry, farmer claims, admin verification, and marketplace filtering.
- **AI-Powered Matchmaking Engine**: Buyer-seller recommendations based on crop type, location, quantity, price, and reliability.
- **Advanced Analytics Dashboard**: Market insights, crop performance, geographic analysis, user engagement, and export capabilities.
- **Monetization Features**: Paystack integration for transaction fees, logistics fees, subscriptions, and payment analytics.
- **Universal Onboarding Workflow**: Multi-role registration (farmer, aggregator, transport, etc.) with document uploads, progress tracking, and bulk onboarding.
- **SabiBuy Group-Buy Engine**: Zero-stock middleman trading system with unique campaign codes, automatic batch management, multi-tier system (Free/Captain/Premium), Paystack subscription integration, and multi-channel support (web, SMS, USSD). Enables anyone to earn ₦4k-₦15k profit per batch with zero inventory risk.

## External Dependencies

### Frontend Libraries
- **Bootstrap 5**: Styling framework.
- **Font Awesome 6**: Icon library.

### Python Packages
- **Flask**: Web framework.
- **Flask-SQLAlchemy**: Database ORM.
- **Flask-Login**: User session management.
- **Flask-WTF**: Form handling.
- **Werkzeug**: Password hashing.
- **WTForms**: Form validation.
- **Requests**: HTTP library.
- **Psycopg2**: PostgreSQL adapter.
- **Trafilatura**: Web scraping.

### API Integrations
- **OpenWeatherMap API**: Real-time weather data.
- **Trade Data Service**: Mock service for market trends.
- **GI Service**: Geographical indications management.
- **Africa's Talking SMS API**: SMS gateway for rural farmers.
- **Africa's Talking USSD API**: USSD gateway for feature phone access.
- **Paystack**: Payment gateway.
- **Meta WhatsApp Cloud API**: Foundation for WhatsApp integration.
- **T2 (9mobile) integration**: For USSD and wallet features.
- **Multilingual Service**: Language detection and message templating.

### Infrastructure
- **PostgreSQL Database**: Scalable database.
- **Environment Variables**: Configuration management.
- **Replit Hosting**: Cloud-based development and deployment.