# Tradoja

## Overview

Tradoja (Trade + Oja, meaning "market" in Yoruba) is a digital agricultural marketplace connecting farmers and buyers across Africa, with an initial focus on Lagos to address food security. The platform enables farmers to list produce, buyers to browse products, and administrators to manage operations. It is a Flask web application featuring role-based access for farmers, buyers, and admins. The project aims to enhance food security, empower farmers, and streamline agricultural supply chains through advanced features like AI-powered scam detection, comprehensive logistics, digital inclusion for rural farmers, and climate-smart agriculture tools.

**Contact**: askme@tradoja.com

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
- **Proposal Model**: Proposal (partnership proposals with JSON sections, slug-based URLs, draft/published status).
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
- **Anti-Reseller Controls (Farmer-First)**: Protects farmers from pure resellers who markup prices without adding value. Features include:
  - Trader verification system requiring value-add proof (transport, aggregation, processing, storage, working capital, quality grading)
  - Reseller Detection Service with 6 rules scoring: no value declaration, no logistics usage, no farmer relationships, high markup ratios, quick buy-relist patterns, unverified status
  - Farmer listing preferences (all buyers, verified traders only, direct buyers only, SabiBuy only)
  - Marketplace source transparency badges (Farmer/Aggregator/Trader) with farmers listed first
  - Admin trader verification dashboard for reviewing applications and flagged accounts
  - Automatic integration into buyer dashboard with verification notices
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
- **Enhanced Anti-Reseller Protections**:
  - Continuous trader verification with 90-day expiry and monthly activity checks
  - Device fingerprinting (IP/user agent/device ID) to detect multi-account collusion
  - Farmer feedback system - traders rated after each transaction, poor ratings trigger re-verification
  - Captain bond system - ₦10,000 refundable deposit required for SabiBuy campaigns
  - Buyer escrow - payments held until delivery confirmed, auto-refund on cancellation
  - Tiered transaction fees: farmer-direct 2%, verified trader 3.5%, unverified trader 5%
- **Dispute & Rating System**:
  - Dispute service with SLA tracking (24h farmer/buyer response, 48h trader response)
  - Auto-escalation on SLA breach with priority flags
  - Star rating system (1-5) with leaderboards and trust scores
  - Re-verification triggers when trader rating drops below 3 stars
- **Extended SMS Commands for Digital Inclusion**:
  - COMPLAINT/REPORT/DISPUTE - file complaints via SMS
  - TRACK [code/MYORDERS/LOGISTICS] - order and logistics tracking
  - RATE [code] [1-5] [comment] - rate transactions
  - STATUS [ticket] - check account and dispute status

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

## Demo Credentials

For investor/partner demos, use these pre-seeded accounts:

| Role | Email | Password | Purpose |
|------|-------|----------|---------|
| Admin | admin@tradoja.com | admin123 | Full admin dashboard access |
| Farmer | farmer@demo.com | farmer123 | Farmer with produce listings |
| Buyer | buyer@demo.com | buyer123 | Verified bulk trader |
| Agent | agent@demo.com | agent123 | Field agent for onboarding |
| Farmer | amina@demo.com | demo123 | Additional farmer (Kano) |
| Farmer | emeka@demo.com | demo123 | Additional farmer (Enugu) |

**To re-seed demo data**: Run `python seed_demo_data.py`

**USSD/SMS Status**: Pending telco activation. Use simulators at `/simulator/ussd` and `/simulator/sms` for demos.

## Pending Integrations

### Twilio WhatsApp Integration (Planned)
- **Status**: Awaiting credentials
- **Required Secrets**:
  - `TWILIO_ACCOUNT_SID` - From Twilio Console dashboard
  - `TWILIO_AUTH_TOKEN` - From Twilio Console dashboard  
  - `TWILIO_WHATSAPP_NUMBER` - WhatsApp-enabled Twilio number
- **Purpose**: Unified SMS + WhatsApp messaging via Twilio API
- **Implementation**: Create `whatsapp_service.py` using `twilio` Python package
- **Features Planned**: 
  - WhatsApp messaging for farmers (text + voice notes)
  - Same commands as SMS (REG, SELL, JOIN, SABIBUY, HELP)
  - Rich media support (produce images)
  - Integration with existing SabiBuy, logistics, and scam detection
