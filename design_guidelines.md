# AgroLink Design Guidelines

## Design Approach
**Framework**: Bootstrap 5 Dark Theme with agricultural marketplace customization
**Inspiration**: Airbnb marketplace trust + Shopify dashboard efficiency + logistics platform robustness
**Principles**: High contrast for visibility, simplified UI for rural accessibility, data-first dashboard design

## Typography
- **Primary Font**: Inter (Google Fonts) - modern, highly legible at small sizes
- **Hierarchy**:
  - Display: 48px/bold (hero headlines)
  - H1: 32px/semibold (page titles)
  - H2: 24px/semibold (section headers)
  - H3: 18px/medium (card titles)
  - Body: 16px/regular (primary text)
  - Small: 14px/regular (metadata, labels)
  - Caption: 12px/regular (timestamps, helper text)

## Layout System
**Spacing Scale**: Bootstrap's spacing utilities (1=4px, 2=8px, 3=16px, 4=24px, 5=48px)
**Common Units**: Use 2, 3, 4 for consistency (p-3, mb-4, gap-2)
**Container Strategy**:
- Landing: container-fluid with max-width-xxl inner containers
- Dashboards: container-fluid with sidebar navigation
- Forms: max-width-lg centered for focus

## Component Library

### Navigation
- **Top Navbar**: Dark bg, green accent brand, sticky-top, user profile dropdown, notification badge
- **Dashboard Sidebar**: Fixed left (desktop), collapsible (mobile), icon+label navigation, role-based menu items

### Cards
- **Product Cards**: Image top, title, price (large/green), location pin, "Contact Farmer" button
- **Dashboard Stats**: Icon left, metric center, trend indicator, subtle border-start accent
- **Order Cards**: Timeline status, expandable details, action buttons footer

### Forms
- **Input Groups**: Label, input with icon prefix, helper text, validation states
- **Action Buttons**: Primary (green), Secondary (outline-light), Danger (for cancellations)
- **File Upload**: Drag-drop zone for product images, thumbnail preview grid

### Data Displays
- **Tables**: Responsive, striped, hover states, action column with dropdowns
- **Charts**: Chart.js integration - line charts (temperature tracking), bar charts (sales), donut charts (order status)
- **Status Badges**: Pill-shaped, color-coded (success/warning/danger), uppercase text

### Logistics Components
- **Map Integration**: Full-width container with overlay controls, marker clustering for deliveries
- **Cold Chain Tracker**: Temperature gauge, timeline with checkpoints, alert banners
- **Route Visualizer**: Interactive map with route polylines, ETA countdown, driver contact card

## Images

### Hero Section
**Large Hero Image**: Yes - Full-width agricultural scene
- **Description**: Nigerian farmers in green fields with fresh produce, sunrise/golden hour lighting, authentic local setting
- **Placement**: Landing page top, height 70vh (desktop), 50vh (mobile)
- **Overlay**: Dark gradient (bottom to top, 80% to 20% opacity) for text legibility
- **Content**: Centered headline "Connecting Nigerian Farmers to Markets", subheadline, two CTAs (Register as Farmer/Register as Buyer) with backdrop-blur backgrounds

### Dashboard Images
- **Empty States**: Illustrations of farmers, trucks, produce baskets for zero-data states
- **Product Listings**: Square crop 300x300px, show actual produce quality
- **Profile Avatars**: Circular, default to initials on colored background
- **Success States**: Checkmark illustrations for completed transactions

### Marketing Sections
- **Features**: Icons from Font Awesome (fa-tractor, fa-truck, fa-mobile-alt, fa-chart-line)
- **Testimonials**: Farmer/buyer photos (authentic, not stock), quote cards with location tags
- **Partners**: Transport company logos in grayscale filter, grid layout

## Landing Page Structure

1. **Hero**: Full-width image, centered CTAs, trust indicator ("10,000+ farmers connected")
2. **Features Grid**: 3-column (desktop), icon-title-description, green icon backgrounds
3. **How It Works**: 3-step timeline with illustrations, alternating left/right layout
4. **Live Statistics**: 4-column counter animation (total farmers, active orders, deliveries today, tons transported)
5. **Product Showcase**: Carousel of featured produce listings, 4 cards visible (desktop)
6. **Testimonials**: 2-column quote cards with farmer photos
7. **CTA Section**: Green background, centered form "Start Selling Today" with email signup
8. **Footer**: 4-column (About, Quick Links, For Farmers, Contact), social icons, newsletter signup

## Dashboard Layouts

### Farmer Dashboard
- **Top Row**: Revenue card, Active listings, Pending orders, Rating (4 stats cards)
- **Middle**: Recent orders table (expandable rows), Quick actions (Add Product, View Analytics)
- **Bottom**: Sales chart (7-day trend), Top products list

### Buyer Dashboard
- **Search Bar**: Prominent top position, filter chips (location, category, price range)
- **Results Grid**: 3-column product cards, infinite scroll
- **Sidebar**: Active orders summary, saved farmers, recent searches

### Transport Portal
- **Map View**: Primary focus (60% width), active deliveries with clustered markers
- **Side Panel**: Delivery queue list, temperature alerts, driver assignment
- **Bottom Bar**: Fleet status overview (available/in-transit/maintenance)

## Accessibility & Rural Optimization
- High contrast ratios (WCAG AAA where possible)
- Large touch targets (min 44x44px)
- Simplified navigation (max 2 levels deep)
- Offline indicators and sync status
- SMS confirmation snippets for feature phone users
- Progressive enhancement (core functionality without JavaScript)

## Visual Polish
- Subtle shadows on cards (box-shadow-sm)
- Smooth transitions (150ms ease-in-out)
- Green accent (#28a745 primary, lighter/darker variants for states)
- Dark backgrounds (#1a1d20 base, #2d3338 elevated surfaces)
- Minimalist animations: Loading spinners, slide-in modals, fade transitions only