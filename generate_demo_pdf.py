import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF


BRAND_GREEN = colors.HexColor('#28a745')
BRAND_DARK = colors.HexColor('#1a1a2e')
BRAND_ACCENT = colors.HexColor('#16213e')
HIGHLIGHT_YELLOW = colors.HexColor('#ffc107')
SOFT_BG = colors.HexColor('#f8f9fa')
WHITE = colors.white
BLACK = colors.black
GREY = colors.HexColor('#6c757d')
LINK_BLUE = colors.HexColor('#0d6efd')
TELCO_ORANGE = colors.HexColor('#ff6b35')


def get_base_url():
    replit_slug = os.environ.get('REPL_SLUG', 'tradoja')
    replit_owner = os.environ.get('REPL_OWNER', '')
    replit_dev_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
    if replit_dev_domain:
        return f"https://{replit_dev_domain}"
    return "https://YOUR-APP-URL.replit.app"


def build_pdf(filename='static/tradoja_demo_guide.pdf'):
    os.makedirs('static', exist_ok=True)
    base_url = get_base_url()

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title="Tradoja Platform Demo Guide - Telco Partnership",
        author="Tradoja Team"
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'CoverTitle',
        parent=styles['Title'],
        fontSize=36,
        textColor=BRAND_GREEN,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        leading=42
    ))

    styles.add(ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=GREY,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=BRAND_GREEN,
        spaceBefore=20,
        spaceAfter=12,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
        leading=28
    ))

    styles.add(ParagraphStyle(
        'SubHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=BRAND_ACCENT,
        spaceBefore=14,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        leading=20
    ))

    styles.add(ParagraphStyle(
        'BodyText2',
        parent=styles['Normal'],
        fontSize=11,
        textColor=BLACK,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=15,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        'Highlight',
        parent=styles['Normal'],
        fontSize=11,
        textColor=BRAND_DARK,
        backColor=colors.HexColor('#e8f5e9'),
        borderWidth=1,
        borderColor=BRAND_GREEN,
        borderPadding=8,
        spaceAfter=8,
        leading=15,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        'TelcoHighlight',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#7b2d00'),
        backColor=colors.HexColor('#fff3e0'),
        borderWidth=1,
        borderColor=TELCO_ORANGE,
        borderPadding=8,
        spaceAfter=8,
        leading=15,
        fontName='Helvetica-Bold'
    ))

    styles.add(ParagraphStyle(
        'URLStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=LINK_BLUE,
        fontName='Courier',
        spaceAfter=4,
        leading=14
    ))

    styles.add(ParagraphStyle(
        'StepStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=BLACK,
        leftIndent=20,
        spaceAfter=4,
        leading=15,
        fontName='Helvetica'
    ))

    styles.add(ParagraphStyle(
        'CommandStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=WHITE,
        backColor=BRAND_DARK,
        borderPadding=6,
        spaceAfter=6,
        leading=14,
        fontName='Courier-Bold'
    ))

    styles.add(ParagraphStyle(
        'TOCItem',
        parent=styles['Normal'],
        fontSize=12,
        textColor=BRAND_ACCENT,
        spaceBefore=4,
        spaceAfter=4,
        leftIndent=10,
        fontName='Helvetica',
        leading=18
    ))

    styles.add(ParagraphStyle(
        'CenterBold',
        parent=styles['Normal'],
        fontSize=12,
        textColor=BLACK,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=4
    ))

    styles.add(ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GREY,
        alignment=TA_CENTER,
    ))

    elements = []

    # ==================== COVER PAGE ====================
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("TRADOJA", styles['CoverTitle']))
    elements.append(Paragraph("Trade + Oja (Market)", styles['CoverSubtitle']))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(HRFlowable(width="60%", thickness=3, color=BRAND_GREEN, spaceAfter=20, spaceBefore=10, hAlign='CENTER'))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Platform Demo Guide", ParagraphStyle(
        'CoverDemo', parent=styles['Normal'], fontSize=24, textColor=BRAND_ACCENT,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=8
    )))
    elements.append(Paragraph("Telco Partnership Edition", ParagraphStyle(
        'CoverEdition', parent=styles['Normal'], fontSize=16, textColor=TELCO_ORANGE,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=30
    )))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(
        "Africa's First Farmer-First Digital Marketplace<br/>"
        "Powered by SMS, USSD, and Intelligent Escrow",
        ParagraphStyle('CoverDesc', parent=styles['Normal'], fontSize=13,
                       textColor=GREY, alignment=TA_CENTER, leading=20)
    ))
    elements.append(Spacer(1, 0.5 * inch))

    cover_data = [
        ['Prepared For', 'Telco Partnership Demo'],
        ['Contact', 'askme@tradoja.com'],
        ['Platform URL', base_url],
        ['Document', 'Comprehensive Feature Guide & Test Script'],
    ]
    cover_table = Table(cover_data, colWidths=[2 * inch, 3.5 * inch])
    cover_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), BRAND_GREEN),
        ('TEXTCOLOR', (1, 0), (1, -1), BRAND_DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(cover_table)
    elements.append(PageBreak())

    # ==================== TABLE OF CONTENTS ====================
    elements.append(Paragraph("TABLE OF CONTENTS", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    toc_items = [
        ("1.", "Executive Summary & Value Proposition"),
        ("2.", "Quick Start: Demo Credentials & Access"),
        ("3.", "USSD Access (*712*55#) - Feature Phone Trading"),
        ("4.", "SMS Trading Engine - 15+ Commands"),
        ("5.", "WhatsApp Trading Channel - Rich Media Trading [NEW]"),
        ("6.", "TradojaIQ AI Market Intelligence Engine [NEW]"),
        ("7.", "AI-Powered Escrow & Transaction Intelligence"),
        ("8.", "Blockchain-Style Traceability"),
        ("9.", "SabiBuy Group-Buy Engine"),
        ("10.", "Anti-Reseller & Farmer Protection"),
        ("11.", "Web Platform & Dashboards"),
        ("12.", "Payment Infrastructure (Paystack + Telco Wallet)"),
        ("13.", "Digital Inclusion & Multi-Channel Analytics"),
        ("14.", "Complete Test Script: Step-by-Step Demo Flow"),
        ("15.", "Revenue Model & Telco Partnership Opportunities"),
        ("16.", "Technical Architecture Summary"),
    ]
    for num, title in toc_items:
        elements.append(Paragraph(f"<b>{num}</b>  {title}", styles['TOCItem']))
    elements.append(PageBreak())

    # ==================== SECTION 1: EXECUTIVE SUMMARY ====================
    elements.append(Paragraph("1. EXECUTIVE SUMMARY", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "Tradoja is Africa's first farmer-first agricultural marketplace designed to work on <b>any device</b> - "
        "from basic feature phones (via SMS and USSD) to WhatsApp and web browsers. The platform connects "
        "smallholder farmers directly with buyers, eliminates exploitative middlemen, and ensures safe "
        "transactions through AI-powered escrow.",
        styles['BodyText2']
    ))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "<b>TradojaIQ</b> is the AI brain powering the entire marketplace - providing smart price discovery, "
        "dynamic trust scores, demand forecasting, and farmer alerts across every channel.",
        styles['BodyText2']
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("WHY THIS MATTERS FOR TELCO PARTNERS", styles['SubHeader']))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO REVENUE OPPORTUNITY:</b></font> Every SMS command, USSD session, and payment '
        'transaction generates telco revenue. Tradoja transforms agricultural trade into a recurring '
        'telco revenue stream across Nigeria\'s 38M+ farming households.',
        styles['TelcoHighlight']
    ))

    kpi_data = [
        ['Metric', 'Value', 'Telco Impact'],
        ['Target Users', '38M+ farming households', 'New USSD/SMS subscribers'],
        ['SMS Commands', '15+ trading commands', 'Per-message revenue'],
        ['USSD Sessions', 'Full trading via *712*55#', 'Session-based billing'],
        ['Transaction Volume', 'N4k-N15k per batch trade', '1.5-5% platform fees'],
        ['Channels', 'SMS + USSD + WhatsApp + Web (all live)', 'Multi-channel engagement'],
        ['Escrow Payments', 'AI-verified release', 'Payment float revenue'],
        ['AI Intelligence', 'TradojaIQ Engine', 'Price guidance, trust scores, demand insights'],
    ]
    kpi_table = Table(kpi_data, colWidths=[1.8 * inch, 2 * inch, 2.2 * inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(PageBreak())

    # ==================== SECTION 2: QUICK START ====================
    elements.append(Paragraph("2. QUICK START: DEMO CREDENTIALS & ACCESS", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(f"<b>Platform URL:</b>", styles['BodyText2']))
    elements.append(Paragraph(f"{base_url}", styles['URLStyle']))
    elements.append(Spacer(1, 8))

    cred_data = [
        ['Role', 'Email', 'Password', 'What You Can Test'],
        ['Admin', 'admin@tradoja.com', 'admin123', 'Full admin dashboard, analytics, SMS/USSD dashboards'],
        ['Farmer', 'farmer@demo.com', 'farmer123', 'Produce listings, farmer dashboard, escrow'],
        ['Buyer', 'buyer@demo.com', 'buyer123', 'Marketplace, purchasing, buyer dashboard'],
        ['Agent', 'agent@demo.com', 'agent123', 'Field agent onboarding, bulk registration'],
    ]
    cred_table = Table(cred_data, colWidths=[0.8 * inch, 1.8 * inch, 1 * inch, 2.8 * inch])
    cred_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(cred_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("KEY DEMO LINKS", styles['SubHeader']))

    links_data = [
        ['Feature', 'URL Path', 'Login Required'],
        ['Home Page', '/', 'No'],
        ['SMS Simulator', '/simulator/sms', 'No'],
        ['USSD Simulator', '/simulator/ussd', 'No'],
        ['Marketplace', '/marketplace', 'No'],
        ['SabiBuy Group-Buy', '/sabibuy', 'No'],
        ['Traceability Viewer', '/trace/<code>', 'No'],
        ['WhatsApp Simulator', '/simulator/whatsapp', 'No'],
        ['TradojaIQ Intelligence', '/intelligence', 'No'],
        ['Admin Dashboard', '/admin/dashboard', 'Admin'],
        ['SMS Dashboard', '/admin/sms-dashboard', 'Admin'],
        ['USSD Dashboard', '/admin/ussd-dashboard', 'Admin'],
        ['Digital Inclusion Analytics', '/admin/digital-inclusion', 'Admin'],
        ['Scam Detection Dashboard', '/admin/scams', 'Admin'],
        ['Farmer Dashboard', '/farmer/dashboard', 'Farmer'],
        ['Buyer Dashboard', '/buyer/dashboard', 'Buyer'],
        ['Payment Analytics', '/admin/payments', 'Admin'],
        ['TradojaIQ Dashboard', '/intelligence', 'No'],
        ['Advanced Analytics', '/admin/analytics', 'Admin'],
    ]
    links_table = Table(links_data, colWidths=[2 * inch, 2.2 * inch, 1.3 * inch])
    links_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTNAME', (1, 1), (1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(links_table)
    elements.append(PageBreak())

    # ==================== SECTION 3: USSD ====================
    elements.append(Paragraph("3. USSD ACCESS (*712*55#)", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO PRIORITY FEATURE</b></font> - This is the primary revenue channel for telco '
        'partners. Every USSD session generates session-based billing revenue. The USSD gateway enables '
        '100% of Nigeria\'s 200M+ mobile subscribers to trade - including the 60%+ without smartphones.',
        styles['TelcoHighlight']
    ))

    elements.append(Paragraph("HOW TO TEST: USSD SIMULATOR", styles['SubHeader']))
    elements.append(Paragraph(f"Open: {base_url}/simulator/ussd", styles['URLStyle']))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("<b>Step-by-Step USSD Demo:</b>", styles['BodyText2']))

    ussd_steps = [
        "<b>1.</b> Navigate to the USSD Simulator page",
        "<b>2.</b> Enter any phone number (e.g., 08012345678)",
        "<b>3.</b> Dial <b>*712*55#</b> to start a session",
        "<b>4.</b> You will see the main menu with options:",
        "    <b>1</b> - Register (new farmer/buyer/transporter)",
        "    <b>2</b> - Sell Produce (list crops for sale)",
        "    <b>3</b> - Buy Produce (browse and purchase)",
        "    <b>4</b> - Check Prices (market intelligence)",
        "    <b>5</b> - My Orders (track purchases/sales)",
        "    <b>6</b> - Check Balance (T2 wallet balance)",
        "    <b>7</b> - SabiBuy (group-buy campaigns)",
        "    <b>8</b> - Get Help",
        "    <b>9</b> - Transport Jobs",
        "    <b>10</b> - Start Campaign (SabiBuy)",
        "<b>5.</b> Select option <b>1</b> to register as a farmer",
        "<b>6.</b> Follow prompts: enter name, select state, enter crop type",
        "<b>7.</b> After registration, go back and test <b>option 2</b> (Sell) and <b>option 4</b> (Prices)",
    ]
    for step in ussd_steps:
        elements.append(Paragraph(step, styles['StepStyle']))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO REVENUE MODEL:</b></font> Each USSD session generates N4-N7 in telco revenue. '
        'With 10,000 daily active farmers, this equals <b>N40,000 - N70,000 daily USSD revenue</b> for the telco partner, '
        'growing to millions as adoption scales across Nigeria\'s 36 states.',
        styles['TelcoHighlight']
    ))

    elements.append(Paragraph("USSD MENU STRUCTURE", styles['SubHeader']))
    ussd_menu_data = [
        ['Option', 'Function', 'Sub-menus', 'Revenue per Session'],
        ['1', 'Register', 'Farmer/Buyer/Transport/Agent', 'N4-N7'],
        ['2', 'Sell Produce', 'Crop > Qty > Price > Location', 'N4-N7'],
        ['3', 'Buy Produce', 'Browse > Select > Order', 'N4-N7'],
        ['4', 'Check Prices', 'Crop > Region > Live Prices', 'N4-N7'],
        ['5', 'My Orders', 'Active > History > Track', 'N4-N7'],
        ['6', 'Check Balance', 'T2 Wallet Balance', 'N4-N7'],
        ['7', 'SabiBuy', 'Join Campaign > Pay', 'N4-N7'],
        ['9', 'Transport Jobs', 'Available > Claim > Track', 'N4-N7'],
        ['10', 'Start Campaign', 'Create SabiBuy Campaign', 'N4-N7'],
    ]
    ussd_table = Table(ussd_menu_data, colWidths=[0.6 * inch, 1.3 * inch, 2.2 * inch, 1.3 * inch])
    ussd_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TELCO_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#fff8f0')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
    ]))
    elements.append(ussd_table)
    elements.append(PageBreak())

    # ==================== SECTION 4: SMS ENGINE ====================
    elements.append(Paragraph("4. SMS TRADING ENGINE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO PRIORITY FEATURE</b></font> - Every SMS command generates N4-N5 in telco '
        'revenue per message. The platform absorbs SMS costs within the 1.5% transaction fee, making it '
        'free for farmers while generating telco revenue. <b>15+ SMS commands</b> cover the entire '
        'trading lifecycle.',
        styles['TelcoHighlight']
    ))

    elements.append(Paragraph("HOW TO TEST: SMS SIMULATOR", styles['SubHeader']))
    elements.append(Paragraph(f"Open: {base_url}/simulator/sms", styles['URLStyle']))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("<b>Simulator Features:</b>", styles['BodyText2']))
    sim_features = [
        "Editable phone number with random generation button",
        "Demo account quick-switcher (Farmer/Buyer/Transport)",
        "New Session button for fresh testing",
        "Real-time response display",
    ]
    for feat in sim_features:
        elements.append(Paragraph(f"  * {feat}", styles['StepStyle']))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("COMPLETE SMS COMMAND REFERENCE", styles['SubHeader']))

    sms_data = [
        ['Command', 'Format', 'Description', 'Example'],
        ['REG', 'REG [name] [loc] [crop]', 'Register as farmer', 'REG Tunde Lagos Tomatoes'],
        ['SELL', 'SELL [crop] [qty] [price]', 'List produce for sale', 'SELL Tomatoes 50KG 800'],
        ['PRICE', 'PRICE [crop]', 'Check market prices', 'PRICE Yam'],
        ['ACCEPT', 'ACCEPT [order-code]', 'Accept an order', 'ACCEPT ORD-A1B2'],
        ['PICKUP', 'PICKUP [order-code]', 'Confirm pickup', 'PICKUP ORD-A1B2'],
        ['DELIVER', 'DELIVER [code] [OTP]', 'Confirm delivery with OTP', 'DELIVER ORD-A1B2 4821'],
        ['TRACK', 'TRACK [code/MYORDERS]', 'Track orders', 'TRACK ORD-A1B2'],
        ['CANCEL', 'CANCEL [code] [reason]', 'Cancel order with reason', 'CANCEL ORD-A1B2 bad quality'],
        ['STATUS', 'STATUS', 'Account status summary', 'STATUS'],
        ['BAL', 'BAL', 'Check wallet balance', 'BAL'],
        ['JOBS', 'JOBS', 'View transport jobs', 'JOBS'],
        ['VOUCH', 'VOUCH [phone]', 'Vouch for another farmer', 'VOUCH 08012345678'],
        ['CAMPAIGNS', 'CAMPAIGNS', 'View SabiBuy campaigns', 'CAMPAIGNS'],
        ['SABIBUY', 'SABIBUY [code] [qty]', 'Join group-buy', 'SABIBUY OBI-SB-48K 10'],
        ['HELP', 'HELP', 'Show all commands', 'HELP'],
    ]
    sms_table = Table(sms_data, colWidths=[0.8 * inch, 1.6 * inch, 1.5 * inch, 1.6 * inch])
    sms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Courier-Bold'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sms_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("AI-POWERED SMS COMMANDS", styles['SubHeader']))

    ai_sms_data = [
        ['Command', 'Format', 'Description', 'AI Feature'],
        ['AI', 'AI [natural language]', 'Smart assistant', 'Parses natural language into commands'],
        ['ADVICE', 'ADVICE [crop]', 'Price intelligence', 'AI analyzes market data for recommendations'],
        ['RISK', 'RISK [order-code]', 'Transaction safety', 'AI scores buyer/seller risk factors'],
        ['TRACE', 'TRACE [code]', 'Produce journey', 'Blockchain-style supply chain tracking'],
        ['QUALITY', 'QUALITY [code] [A/B/C]', 'Quality grading', 'Records quality at each supply chain stage'],
    ]
    ai_table = Table(ai_sms_data, colWidths=[0.8 * inch, 1.5 * inch, 1.3 * inch, 2 * inch])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6f42c1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Courier-Bold'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#f3f0ff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(ai_table)

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>SMS REVENUE PROJECTION:</b></font> With 15+ commands per trade cycle and an average '
        'of 3 trades per farmer per month, each active farmer generates <b>45+ SMS messages monthly</b>. '
        'At N4-5/message, 100,000 active farmers = <b>N18M-N22.5M monthly SMS revenue</b> for the telco.',
        styles['TelcoHighlight']
    ))
    elements.append(PageBreak())

    # ==================== SECTION 5: WHATSAPP ====================
    elements.append(Paragraph("5. WHATSAPP TRADING CHANNEL", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "WhatsApp is the game-changer channel for Tradoja. With 90M+ WhatsApp users in Nigeria, "
        "this channel provides rich media trading with photos, payment links, interactive messages, "
        "and the same full trading experience as SMS - but with a richer, more intuitive interface. "
        "All WhatsApp transactions sync with SMS, USSD, and Web in real-time.",
        styles['BodyText2']
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("HOW TO TEST: WHATSAPP SIMULATOR", styles['SubHeader']))
    elements.append(Paragraph(f"Open: {base_url}/simulator/whatsapp", styles['URLStyle']))
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("<b>Step-by-Step WhatsApp Demo:</b>", styles['BodyText2']))

    wa_steps = [
        "<b>1.</b> Navigate to the WhatsApp Simulator page",
        "<b>2.</b> The simulator shows an authentic WhatsApp-style phone interface",
        "<b>3.</b> Enter any phone number (e.g., +2348012345678)",
        "<b>4.</b> Type <font face='Courier' color='#0d6efd'>HI</font> or <font face='Courier' color='#0d6efd'>HELLO</font> - Get a welcome message with your trust badge",
        "<b>5.</b> Type <font face='Courier' color='#0d6efd'>HELP</font> - See all available commands",
        "<b>6.</b> Try: <font face='Courier' color='#0d6efd'>MARKET</font> - Browse produce with trust badges and price guidance",
        "<b>7.</b> Try: <font face='Courier' color='#0d6efd'>PRICE Tomatoes</font> - Get TradojaIQ market intelligence",
        "<b>8.</b> Try: <font face='Courier' color='#0d6efd'>SELL Tomatoes 50KG 8000 Lagos</font> - List produce with AI price guidance",
        "<b>9.</b> Try: <font face='Courier' color='#0d6efd'>BUY [listing_id]</font> - Purchase with escrow protection",
        "<b>10.</b> Try: <font face='Courier' color='#0d6efd'>SABIBUY LIST</font> - Browse group-buy campaigns",
    ]
    for step in wa_steps:
        elements.append(Paragraph(step, styles['StepStyle']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("COMPLETE WHATSAPP COMMAND REFERENCE", styles['SubHeader']))

    wa_commands = [
        ['Command', 'Format', 'Description'],
        ['Register', 'REG [name] [state] [crop]', 'Create LITE account instantly'],
        ['Sell', 'SELL [crop] [qty] [price] [location]', 'List produce with AI price guidance'],
        ['Market', 'MARKET or MARKET [crop]', 'Browse listings with trust badges'],
        ['Buy', 'BUY [listing_id]', 'Purchase with escrow protection'],
        ['My Listings', 'MYLIST', 'View your active produce listings'],
        ['Orders', 'ORDERS', 'View all buy/sell orders'],
        ['Track', 'TRACK [order_code]', 'Track order status and delivery'],
        ['Accept', 'ACCEPT [order_code]', 'Farmer accepts an order (generates OTP)'],
        ['Price Check', 'PRICE [crop]', 'TradojaIQ market intelligence'],
        ['Balance', 'BAL', 'Check wallet balance'],
        ['SabiBuy List', 'SABIBUY LIST', 'View active group-buy campaigns'],
        ['SabiBuy Join', 'SABIBUY JOIN [code] [qty]', 'Join a campaign'],
        ['SabiBuy Create', 'SABIBUY CREATE [id] [price] [qty] [loc]', 'Start a campaign'],
        ['Rate', 'RATE [order_code] [1-5] [comment]', 'Rate a transaction'],
        ['Verify', 'VERIFY', 'Start identity verification (LITE to VERIFIED)'],
        ['Status', 'STATUS', 'Account summary and trust score'],
        ['Complaint', 'COMPLAINT [text]', 'File a complaint or dispute'],
        ['Help', 'HELP', 'Show all available commands'],
    ]
    wa_cmd_table = Table(wa_commands, colWidths=[1.1 * inch, 2.2 * inch, 2.5 * inch])
    wa_cmd_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#25D366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTNAME', (1, 1), (1, -1), 'Courier'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(wa_cmd_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("CROSS-CHANNEL SYNC", styles['SubHeader']))
    elements.append(Paragraph(
        "All WhatsApp transactions are fully synchronized with SMS, USSD, and Web channels. "
        "A farmer can list produce via WhatsApp, a buyer can purchase via SMS, and the admin can "
        "track everything on the web dashboard. The same wallet, escrow, and order system powers all channels.",
        styles['BodyText2']
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "<b>Production Readiness:</b> The WhatsApp service uses an abstraction layer - currently running "
        "in simulation mode for demos. When Twilio WhatsApp credentials are added, it activates as a "
        "production channel with zero code changes. The webhook endpoint is ready at /webhook/whatsapp.",
        styles['Highlight']
    ))
    elements.append(PageBreak())

    # ==================== SECTION 6: TRADOJAIQ ====================
    elements.append(Paragraph("6. TRADOJAIQ AI MARKET INTELLIGENCE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "TradojaIQ is the AI brain of the Tradoja marketplace. It analyzes every transaction, listing, "
        "and user interaction to provide real-time market intelligence that empowers farmers to get fair "
        "prices and helps buyers find quality produce. TradojaIQ works across all channels - Web, SMS, "
        "USSD, and WhatsApp.",
        styles['BodyText2']
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("FOUR PILLARS OF TRADOJAIQ", styles['SubHeader']))

    iq_pillars = [
        "<b>1. Smart Price Discovery</b> - Analyzes transaction history to calculate fair market prices "
        "per crop, per region. Tells farmers if their price is above, below, or at market rate. "
        "Shows price trends (rising/falling/stable).",
        "<b>2. Dynamic Trust Scores</b> - Every user gets a 0-100 trust score with tiers: "
        "Bronze (0+), Silver (40+), Gold (70+), Platinum (90+). Scores are based on verification status, "
        "completed transactions, ratings, dispute history, account age, and verification extras.",
        "<b>3. Demand Forecasting</b> - Identifies which crops are most in-demand based on buyer search "
        "patterns and purchase history. Shows demand trends to help farmers plan what to grow.",
        "<b>4. Farmer Alerts</b> - Proactive notifications when crops are in high demand, when prices "
        "spike in a region, or when a farmer's listing is priced significantly below market value.",
    ]
    for pillar in iq_pillars:
        elements.append(Paragraph(pillar, styles['StepStyle']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("HOW TO TEST TRADOJAIQ", styles['SubHeader']))

    iq_test_steps = [
        f"<b>Web Dashboard:</b> Open <font face='Courier'>{base_url}/intelligence</font> - Full intelligence dashboard",
        f"<b>Price API:</b> Visit <font face='Courier'>{base_url}/api/tradojaiq/price/Tomatoes</font> - Price intelligence for any crop",
        f"<b>Trust API:</b> Visit <font face='Courier'>{base_url}/api/tradojaiq/trust/1</font> - Trust score for any user",
        f"<b>Demand API:</b> Visit <font face='Courier'>{base_url}/api/tradojaiq/demand</font> - Top demanded crops",
        f"<b>Summary API:</b> Visit <font face='Courier'>{base_url}/api/tradojaiq/summary</font> - Full marketplace intelligence",
        "<b>WhatsApp:</b> Send <font face='Courier' color='#0d6efd'>PRICE Tomatoes</font> in WhatsApp simulator",
        "<b>SMS:</b> Send <font face='Courier' color='#0d6efd'>PRICE Tomatoes</font> in SMS simulator",
        "<b>During Listing:</b> When a farmer lists produce (SELL), TradojaIQ automatically shows price guidance",
    ]
    for step in iq_test_steps:
        elements.append(Paragraph(step, styles['StepStyle']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("TRUST SCORE BREAKDOWN", styles['SubHeader']))

    trust_data = [
        ['Component', 'Max Points', 'How It Works'],
        ['Verification Status', '20', 'LITE=5, Pending=10, Verified=20'],
        ['Completed Transactions', '25', '3 points per completed order (max 25)'],
        ['User Ratings', '20', 'Based on average star rating (1-5)'],
        ['Dispute Record', '+15/-15', '+15 if clean, -5 per unresolved dispute'],
        ['Account Tenure', '10', '1 point per month (max 10)'],
        ['Verification Extras', '10', 'Phone verified +3, Agent verified +4, ID verified +3'],
    ]
    trust_table = Table(trust_data, colWidths=[1.5 * inch, 1 * inch, 3.3 * inch])
    trust_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(trust_table)
    elements.append(PageBreak())

    # ==================== SECTION 7: ESCROW ====================
    elements.append(Paragraph("7. AI-POWERED ESCROW & TRANSACTION INTELLIGENCE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO PRIORITY FEATURE</b></font> - The escrow system holds buyer payments until '
        'delivery is confirmed via OTP + AI verification + location matching. This builds trust in the '
        'ecosystem and enables higher transaction volumes - directly increasing telco revenue through '
        'more SMS/USSD sessions per trade.',
        styles['TelcoHighlight']
    ))

    elements.append(Paragraph("ESCROW FLOW: HOW IT WORKS", styles['SubHeader']))

    escrow_steps = [
        "<b>1. BUYER PLACES ORDER</b> - Payment is held in escrow (not released to farmer)",
        "<b>2. FARMER ACCEPTS</b> - Sends SMS: <font face='Courier'>ACCEPT ORD-XXXX</font> (auto-generates delivery OTP)",
        "<b>3. TRANSPORTER CLAIMS</b> - Sends SMS: <font face='Courier'>JOBS</font> then <font face='Courier'>CLAIM ORD-XXXX</font>",
        "<b>4. LOCATION TRACKING</b> - Sends SMS: <font face='Courier'>LOCATION ORD-XXXX 6.5244,3.3792</font>",
        "<b>5. DELIVERY + OTP</b> - Transporter sends: <font face='Courier'>DELIVER ORD-XXXX [4-digit OTP]</font>",
        "<b>6. AI VERIFICATION</b> - System checks: OTP valid? Location near destination? Time window OK?",
        "<b>7. ESCROW RELEASE</b> - If all checks pass, payment auto-releases to farmer's wallet",
        "<b>8. DISPUTE PATH</b> - If checks fail, escrow is held and dispute is auto-created",
    ]
    for step in escrow_steps:
        elements.append(Paragraph(step, styles['StepStyle']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("AI VERIFICATION SIGNALS", styles['SubHeader']))
    elements.append(Paragraph(
        "Before releasing escrow, the AI evaluates multiple signals to prevent fraud:",
        styles['BodyText2']
    ))

    ai_signals = [
        ['Signal', 'What It Checks', 'Weight'],
        ['OTP Verification', 'Correct 4-digit code (3 attempts max, 24hr expiry)', 'Critical'],
        ['Location Match', 'GPS coordinates near delivery destination', 'High'],
        ['Time Window', 'Delivery within expected time frame', 'Medium'],
        ['Buyer History', 'Past transaction patterns and dispute rate', 'Medium'],
        ['Seller History', 'Farmer reliability score and past deliveries', 'Medium'],
        ['Amount Analysis', 'Transaction amount vs. typical market prices', 'Low'],
    ]
    ai_sig_table = Table(ai_signals, colWidths=[1.5 * inch, 2.8 * inch, 1 * inch])
    ai_sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(ai_sig_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("SCAM DETECTION ENGINE", styles['SubHeader']))
    elements.append(Paragraph(
        "8-rule scoring system protects farmers and buyers from fraud. Triggers include: "
        "suspicious registration patterns, unrealistic prices, quick buy-relist behavior, "
        "device fingerprint collisions, and unverified trader activity. High-score detections "
        "auto-alert admin via SMS.",
        styles['BodyText2']
    ))
    elements.append(Paragraph(f"Admin Scam Dashboard: {base_url}/admin/scams", styles['URLStyle']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("TELCO PARTNERSHIP FOR LICENSED ESCROW", styles['SubHeader']))
    elements.append(Paragraph(
        "Holding customer funds in escrow requires a CBN (Central Bank of Nigeria) Payment Service Provider "
        "license. Nigerian telcos like MTN (MoMo), Airtel (Smartcash), and 9mobile (T2) already hold these licenses "
        "through their fintech subsidiaries. A telco partnership provides: (1) Licensed escrow infrastructure - "
        "they legally hold the funds, (2) Free or subsidized SMS/USSD channels, (3) Mobile money integration for "
        "unbanked farmers, (4) Access to their subscriber base. Tradoja provides the marketplace, farmer network, "
        "and technology. The current escrow system demonstrates the complete flow and is ready to integrate with "
        "a licensed telco partner's payment infrastructure.",
        styles['BodyText2']
    ))
    elements.append(PageBreak())

    # ==================== SECTION 8: TRACEABILITY ====================
    elements.append(Paragraph("8. BLOCKCHAIN-STYLE TRACEABILITY", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "Every produce item gets a cryptographic SHA256 hash chain - providing immutable, "
        "verifiable tracking from farm to buyer without the cost of actual blockchain infrastructure.",
        styles['BodyText2']
    ))

    elements.append(Paragraph("HOW TO TEST", styles['SubHeader']))
    trace_steps = [
        f"<b>1.</b> Open SMS Simulator: {base_url}/simulator/sms",
        "<b>2.</b> Send: <font face='Courier'>TRACE</font> to see help",
        "<b>3.</b> When an order is created and accepted, trace events are automatically recorded",
        "<b>4.</b> Each event (packaging, pickup, in-transit, delivery) creates a hash-chained record",
        f"<b>5.</b> View web trace at: {base_url}/trace/CHN-XXXXXX",
        "<b>6.</b> The web viewer shows: journey timeline, integrity verification, quality grades",
    ]
    for step in trace_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("TRACE CHAIN DATA MODEL", styles['SubHeader']))
    trace_model = [
        ['Field', 'Description'],
        ['chain_code', 'Unique identifier (CHN-XXXXXX)'],
        ['crop_type', 'Type of produce being tracked'],
        ['origin_farm', 'Source farmer name/ID'],
        ['origin_state', 'Farm location/state'],
        ['hash_chain', 'SHA256 cryptographic hash linking events'],
        ['integrity_verified', 'Whether chain integrity is intact'],
        ['Events', 'packaging > pickup > in_transit > location_update > delivery > quality_check'],
    ]
    trace_table = Table(trace_model, colWidths=[1.5 * inch, 4 * inch])
    trace_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Courier'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(trace_table)
    elements.append(PageBreak())

    # ==================== SECTION 9: SABIBUY ====================
    elements.append(Paragraph("9. SABIBUY GROUP-BUY ENGINE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "SabiBuy is a zero-stock middleman trading system. Anyone can earn N4,000-N15,000 profit per batch "
        "by organizing group purchases. Campaign captains create deals, share unique codes via SMS/USSD/Web, "
        "and earn when batches fill up - all with zero inventory risk.",
        styles['BodyText2']
    ))

    elements.append(Paragraph("HOW TO TEST", styles['SubHeader']))
    elements.append(Paragraph(f"Web: {base_url}/sabibuy", styles['URLStyle']))
    elements.append(Paragraph(f"SMS: Send <font face='Courier'>SABIBUY</font> or <font face='Courier'>CAMPAIGNS</font>", styles['BodyText2']))
    elements.append(Paragraph(f"USSD: Dial *712*55# > Option 7 (SabiBuy) or Option 10 (Start Campaign)", styles['BodyText2']))
    elements.append(Spacer(1, 8))

    sabibuy_data = [
        ['Tier', 'Cost', 'Max Campaigns', 'Profit Range'],
        ['Free', 'N0', '2 active', 'N4,000/batch'],
        ['Captain', 'N2,500/month', '10 active', 'N8,000/batch'],
        ['Premium', 'N5,000/month', 'Unlimited', 'N15,000/batch'],
    ]
    sb_table = Table(sabibuy_data, colWidths=[1.2 * inch, 1.2 * inch, 1.5 * inch, 1.5 * inch])
    sb_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(sb_table)
    elements.append(PageBreak())

    # ==================== SECTION 10: ANTI-RESELLER ====================
    elements.append(Paragraph("10. ANTI-RESELLER & FARMER PROTECTION", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "Tradoja is <b>farmer-first</b>. The platform actively protects farmers from exploitative middlemen through:",
        styles['BodyText2']
    ))

    protection_items = [
        "<b>Trader Verification</b> - Traders must prove value-add (transport, processing, storage, etc.)",
        "<b>Reseller Detection</b> - 10-rule scoring: no logistics, high markup, quick relist, device collision, etc.",
        "<b>Tiered Fees</b> - Farmer-direct: 2%, Verified trader: 3.5%, Unverified: 5%",
        "<b>Farmer Listing Preferences</b> - Farmers choose: all buyers, verified traders only, or direct buyers only",
        "<b>Community Vouching</b> - 3 verified farmers must vouch for new farmers (SMS: VOUCH [phone])",
        "<b>Continuous Verification</b> - 90-day expiry, monthly activity checks, rating triggers",
        "<b>Captain Bond</b> - N10,000 refundable deposit for SabiBuy campaigns",
        "<b>Device Fingerprinting</b> - Detects multi-account collusion via IP/user-agent/device ID",
    ]
    for item in protection_items:
        elements.append(Paragraph(f"  {item}", styles['StepStyle']))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Admin Trader Verification: {base_url}/admin/trader-verification", styles['URLStyle']))
    elements.append(Paragraph(f"Buyer Dashboard (shows verification): {base_url}/buyer/dashboard", styles['URLStyle']))
    elements.append(PageBreak())

    # ==================== SECTION 11: WEB PLATFORM ====================
    elements.append(Paragraph("11. WEB PLATFORM & DASHBOARDS", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph("ADMIN DASHBOARD", styles['SubHeader']))
    elements.append(Paragraph(f"Login as: admin@tradoja.com / admin123", styles['Highlight']))
    admin_pages = [
        f"Main Dashboard: {base_url}/admin/dashboard - Overview of all platform metrics",
        f"SMS Dashboard: {base_url}/admin/sms-dashboard - SMS interaction logs and analytics",
        f"USSD Dashboard: {base_url}/admin/ussd-dashboard - USSD session monitoring",
        f"Scam Detection: {base_url}/admin/scams - Review flagged users, approve/ban/call",
        f"Digital Inclusion: {base_url}/admin/digital-inclusion - Multi-channel analytics",
        f"Analytics: {base_url}/admin/analytics - Market insights, crop performance, exports",
        f"Payments: {base_url}/admin/payments - Transaction and revenue analytics",
        f"Logistics: {base_url}/admin/logistics-bidding - Transport management",
        f"Onboarding: {base_url}/admin/onboarding - Registration review and bulk onboarding",
    ]
    for page in admin_pages:
        elements.append(Paragraph(f"  * {page}", styles['StepStyle']))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("FARMER DASHBOARD", styles['SubHeader']))
    elements.append(Paragraph(f"Login as: farmer@demo.com / farmer123", styles['Highlight']))
    elements.append(Paragraph(f"URL: {base_url}/farmer/dashboard", styles['URLStyle']))
    elements.append(Paragraph(
        "Shows: active listings, recent orders, earnings summary, buyer preferences, "
        "produce management, and listing controls.",
        styles['BodyText2']
    ))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("BUYER DASHBOARD", styles['SubHeader']))
    elements.append(Paragraph(f"Login as: buyer@demo.com / buyer123", styles['Highlight']))
    elements.append(Paragraph(f"URL: {base_url}/buyer/dashboard", styles['URLStyle']))
    elements.append(Paragraph(
        "Shows: trader verification status, available produce, purchase history, "
        "marketplace browsing with source transparency badges (Farmer/Aggregator/Trader).",
        styles['BodyText2']
    ))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("PUBLIC PAGES (No Login Required)", styles['SubHeader']))
    public_pages = [
        f"Home: {base_url}/ - Platform overview with key stats",
        f"Marketplace: {base_url}/marketplace - Browse all produce listings",
        f"SabiBuy: {base_url}/sabibuy - Group-buy campaigns and leaderboard",
        f"Climate-Smart Agriculture: {base_url}/csa - Weather, soil, crop tools",
        f"Onboarding: {base_url}/onboarding - Multi-role registration wizard",
    ]
    for page in public_pages:
        elements.append(Paragraph(f"  * {page}", styles['StepStyle']))
    elements.append(PageBreak())

    # ==================== SECTION 12: PAYMENTS ====================
    elements.append(Paragraph("12. PAYMENT INFRASTRUCTURE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "Dual payment system: <b>Paystack</b> for web/card payments and <b>T2 Wallet</b> (9mobile integration) "
        "for USSD-based payments. Both integrate with the escrow system.",
        styles['BodyText2']
    ))

    payment_data = [
        ['Channel', 'Method', 'Use Case', 'Telco Integration'],
        ['Web', 'Paystack (Card/Bank)', 'Online purchases, subscriptions', 'Standard'],
        ['USSD', 'T2 Wallet (*712*55#)', 'Feature phone payments', 'Direct telco billing'],
        ['SMS', 'Paystack USSD', 'SMS-initiated payment', 'USSD pop-up trigger'],
        ['SabiBuy', 'Paystack Subscription', 'Captain tier upgrades', 'Recurring billing'],
        ['Escrow', 'Platform Hold', 'Transaction protection', 'Float revenue opportunity'],
    ]
    pay_table = Table(payment_data, colWidths=[0.8 * inch, 1.4 * inch, 1.5 * inch, 1.8 * inch])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("FEE STRUCTURE", styles['SubHeader']))
    fee_data = [
        ['Transaction Type', 'Fee', 'Who Pays'],
        ['Farmer-direct sale', '2%', 'Split buyer/farmer'],
        ['Verified trader purchase', '3.5%', 'Trader'],
        ['Unverified trader purchase', '5%', 'Trader'],
        ['Logistics booking', '3%', 'Requester'],
        ['SabiBuy Captain (Free tier)', '0%', 'N/A'],
        ['SabiBuy Captain upgrade', 'N2,500-N5,000/mo', 'Captain'],
    ]
    fee_table = Table(fee_data, colWidths=[2.2 * inch, 1.5 * inch, 1.8 * inch])
    fee_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(fee_table)
    elements.append(PageBreak())

    # ==================== SECTION 13: DIGITAL INCLUSION ====================
    elements.append(Paragraph("13. DIGITAL INCLUSION & MULTI-CHANNEL ANALYTICS", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO ALIGNMENT:</b></font> Tradoja is designed for digital inclusion - reaching '
        'the 60%+ of Nigerian mobile subscribers who use feature phones. Every channel generates telco revenue.',
        styles['TelcoHighlight']
    ))

    channels = [
        ['Channel', 'Device Required', 'Registration', 'Trading', 'Status'],
        ['USSD (*712*55#)', 'Any phone', 'Full', 'Full', 'Simulator Ready'],
        ['SMS', 'Any phone', 'Full (REG)', 'Full (15+ cmds)', 'Simulator Ready'],
        ['Web', 'Smartphone/PC', 'Full', 'Full', 'Live'],
        ['WhatsApp', 'Smartphone', 'Full (REG)', 'Full (15+ cmds)', 'Simulator Ready'],
        ['Agent-Assisted', 'Agent phone', 'Full', 'Via agent', 'Live'],
    ]
    ch_table = Table(channels, colWidths=[1.3 * inch, 1 * inch, 0.9 * inch, 0.9 * inch, 1.2 * inch])
    ch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TELCO_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#fff8f0')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(ch_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("MULTILINGUAL SUPPORT", styles['SubHeader']))
    elements.append(Paragraph(
        "SMS and USSD support 5 languages: <b>English, Yoruba, Hausa, Pidgin, Igbo</b>. "
        "Language is auto-detected or user-selected. This ensures accessibility across Nigeria's diverse population.",
        styles['BodyText2']
    ))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Digital Inclusion Dashboard: {base_url}/admin/digital-inclusion", styles['URLStyle']))
    elements.append(PageBreak())

    # ==================== SECTION 14: TEST SCRIPT ====================
    elements.append(Paragraph("14. COMPLETE TEST SCRIPT: STEP-BY-STEP DEMO", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph(
        "Follow this script for a compelling 20-25 minute demo. Each section includes the exact "
        "steps, commands, and expected results.",
        styles['BodyText2']
    ))

    # Demo Script Part 1
    elements.append(Paragraph("DEMO PART 1: SMS FARMER JOURNEY (5 min)", styles['SubHeader']))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO TALKING POINT:</b></font> "Every one of these SMS messages generates '
        'N4-5 in telco revenue. Watch how a farmer with a basic phone can trade."',
        styles['TelcoHighlight']
    ))

    demo1_steps = [
        f"<b>1.</b> Open SMS Simulator: <font face='Courier'>{base_url}/simulator/sms</font>",
        "<b>2.</b> Click 'New Session' for a fresh phone number",
        "<b>3.</b> Send: <font face='Courier' color='#0d6efd'>HELP</font> - Shows all 15+ available commands",
        "<b>4.</b> Send: <font face='Courier' color='#0d6efd'>REG Amina Lagos Tomatoes</font> - Registers a farmer instantly",
        "<b>5.</b> Send: <font face='Courier' color='#0d6efd'>SELL Tomatoes 100KG 5000</font> - Lists produce for sale",
        "<b>6.</b> Send: <font face='Courier' color='#0d6efd'>PRICE Tomatoes</font> - Gets current market prices",
        "<b>7.</b> Send: <font face='Courier' color='#0d6efd'>STATUS</font> - Shows account summary",
        "<b>8.</b> Send: <font face='Courier' color='#0d6efd'>ADVICE Tomatoes</font> - AI recommends pricing strategy",
        "<b>9.</b> Point out: That was 6 SMS messages = N24-30 telco revenue from ONE farmer session",
    ]
    for step in demo1_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))

    # Demo Script Part 2
    elements.append(Paragraph("DEMO PART 2: USSD BUYER JOURNEY (3 min)", styles['SubHeader']))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO TALKING POINT:</b></font> "USSD sessions generate N4-7 per session. '
        'This works on ANY phone - even a N2,000 feature phone."',
        styles['TelcoHighlight']
    ))

    demo2_steps = [
        f"<b>1.</b> Open USSD Simulator: <font face='Courier'>{base_url}/simulator/ussd</font>",
        "<b>2.</b> Enter phone number and dial <font face='Courier' color='#0d6efd'>*712*55#</font>",
        "<b>3.</b> Select <b>1</b> (Register) > Choose Buyer > Enter name > Select state",
        "<b>4.</b> Back to main menu > Select <b>3</b> (Buy Produce) > Browse listings",
        "<b>5.</b> Select <b>4</b> (Check Prices) > Enter crop name > See live prices",
        "<b>6.</b> Select <b>6</b> (Check Balance) > Show T2 wallet integration",
        "<b>7.</b> Point out: The USSD shortcode *712*55# is ready for telco activation",
    ]
    for step in demo2_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))

    # Demo Script Part 3
    elements.append(Paragraph("DEMO PART 3: ESCROW + AI INTELLIGENCE (4 min)", styles['SubHeader']))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>TELCO TALKING POINT:</b></font> "Escrow builds trust. More trust = more transactions = '
        'more SMS/USSD sessions = more telco revenue. The AI catches fraud before it happens."',
        styles['TelcoHighlight']
    ))

    demo3_steps = [
        "<b>1.</b> In SMS Simulator, explain the escrow flow:",
        "    Buyer pays > Money held in escrow > Farmer accepts > Transporter delivers",
        "    > OTP verified > AI checks signals > Escrow releases to farmer",
        "<b>2.</b> Show AI features:",
        "    Send: <font face='Courier' color='#0d6efd'>AI I want to sell 50kg of yam for 15000</font>",
        "    (AI parses natural language into structured SELL command)",
        "<b>3.</b> Show scam detection:",
        f"    Open: <font face='Courier'>{base_url}/admin/scams</font> (login as admin first)",
        "    Show the 8-rule scoring system and admin actions (approve/ban/call)",
        "<b>4.</b> Show traceability:",
        "    Send: <font face='Courier' color='#0d6efd'>TRACE</font> - Explains blockchain-style tracking",
        "    Show the web viewer with cryptographic hash chain verification",
    ]
    for step in demo3_steps:
        elements.append(Paragraph(step, styles['StepStyle']))
    elements.append(PageBreak())

    # Demo Script Part 4
    elements.append(Paragraph("DEMO PART 4: ADMIN & ANALYTICS (3 min)", styles['SubHeader']))

    demo4_steps = [
        f"<b>1.</b> Login as admin: <font face='Courier'>{base_url}/login</font>",
        "    Email: <font face='Courier'>admin@tradoja.com</font> / Password: <font face='Courier'>admin123</font>",
        f"<b>2.</b> Admin Dashboard: <font face='Courier'>{base_url}/admin/dashboard</font>",
        "    Show: total users, produce listings, orders, logistics requests",
        f"<b>3.</b> SMS Dashboard: <font face='Courier'>{base_url}/admin/sms-dashboard</font>",
        "    Show: SMS interaction logs, command usage analytics, user activity",
        f"<b>4.</b> USSD Dashboard: <font face='Courier'>{base_url}/admin/ussd-dashboard</font>",
        "    Show: USSD session data, menu navigation patterns",
        f"<b>5.</b> Digital Inclusion: <font face='Courier'>{base_url}/admin/digital-inclusion</font>",
        "    Show: channel breakdown (SMS vs USSD vs Web), language analytics",
        f"<b>6.</b> Payment Analytics: <font face='Courier'>{base_url}/admin/payments</font>",
        "    Show: transaction fees, escrow status, revenue breakdown",
    ]
    for step in demo4_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))

    # Demo Script Part 5
    elements.append(Paragraph("DEMO PART 5: SABIBUY GROUP-BUY (2 min)", styles['SubHeader']))
    demo5_steps = [
        f"<b>1.</b> Open SabiBuy: <font face='Courier'>{base_url}/sabibuy</font>",
        "<b>2.</b> Show the campaign listing and leaderboard",
        "<b>3.</b> In SMS Simulator, send: <font face='Courier' color='#0d6efd'>CAMPAIGNS</font>",
        "<b>4.</b> Explain: Anyone can become a campaign captain, earn N4k-N15k per batch",
        "<b>5.</b> Show multi-channel access: Web + SMS + USSD option 7",
        "<b>6.</b> Point out subscription tiers: Free > Captain > Premium",
    ]
    for step in demo5_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))

    elements.append(Paragraph("DEMO PART 6: WHATSAPP TRADING (3 min)", styles['SubHeader']))
    demo6_steps = [
        f"<b>1.</b> Open WhatsApp Simulator: <font face='Courier'>{base_url}/simulator/whatsapp</font>",
        "<b>2.</b> Type <font face='Courier' color='#0d6efd'>HI</font> - Shows welcome with trust badge",
        "<b>3.</b> Type <font face='Courier' color='#0d6efd'>MARKET</font> - Browse produce with trust badges and prices",
        "<b>4.</b> Type <font face='Courier' color='#0d6efd'>PRICE Tomatoes</font> - TradojaIQ market intelligence",
        "<b>5.</b> Type <font face='Courier' color='#0d6efd'>SELL Rice 100KG 25000 Lagos</font> - List with price guidance",
        "<b>6.</b> Type <font face='Courier' color='#0d6efd'>SABIBUY LIST</font> - Show cross-channel SabiBuy access",
        "<b>7.</b> Point out: Same database, same escrow, same wallet as SMS/USSD/Web",
    ]
    for step in demo6_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))

    elements.append(Paragraph("DEMO PART 7: TRADOJAIQ INTELLIGENCE (2 min)", styles['SubHeader']))
    demo7_steps = [
        f"<b>1.</b> Open TradojaIQ Dashboard: <font face='Courier'>{base_url}/intelligence</font>",
        "<b>2.</b> Show marketplace summary: total users, listings, transactions, avg trust score",
        "<b>3.</b> Show demand insights: which crops are most in-demand",
        "<b>4.</b> Show trust score breakdown: Bronze/Silver/Gold/Platinum distribution",
        "<b>5.</b> Show top crops: most active crops on the platform",
        "<b>6.</b> Point out: This intelligence powers price guidance on ALL channels automatically",
    ]
    for step in demo7_steps:
        elements.append(Paragraph(step, styles['StepStyle']))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("DEMO CLOSING STATEMENT", styles['SubHeader']))
    elements.append(Paragraph(
        '<font color="#ff6b35"><b>KEY MESSAGE:</b></font> "Tradoja transforms every agricultural trade into telco revenue. '
        'With SMS, USSD, WhatsApp, and AI-powered TradojaIQ intelligence, we\'re building the infrastructure for Africa\'s food security - '
        'and your shortcode activation is the key to unlocking this for 38 million farming households."',
        styles['TelcoHighlight']
    ))
    elements.append(PageBreak())

    # ==================== SECTION 15: REVENUE MODEL ====================
    elements.append(Paragraph("15. REVENUE MODEL & TELCO PARTNERSHIP", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    elements.append(Paragraph("JOINT REVENUE STREAMS", styles['SubHeader']))

    rev_data = [
        ['Revenue Stream', 'Tradoja Share', 'Telco Share', 'Scale Potential'],
        ['SMS Messages (N4-5 each)', 'Transaction fees', 'Per-message revenue', '45+ msgs/farmer/month'],
        ['USSD Sessions (N4-7 each)', 'Transaction fees', 'Session billing', '10+ sessions/farmer/month'],
        ['Transaction Fees (1.5-5%)', 'Platform revenue', 'Payment processing', 'N4k-N500k per trade'],
        ['Escrow Float', 'Interest earned', 'Banking partnership', 'Millions in float daily'],
        ['SabiBuy Subscriptions', 'Subscription revenue', 'Billing partnership', 'N2.5k-N5k/captain/month'],
        ['Data & Analytics', 'Market intelligence', 'Subscriber insights', 'Agricultural market data'],
    ]
    rev_table = Table(rev_data, colWidths=[1.5 * inch, 1.2 * inch, 1.3 * inch, 1.5 * inch])
    rev_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TELCO_ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, colors.HexColor('#fff8f0')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(rev_table)

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("WHAT WE NEED FROM THE TELCO", styles['SubHeader']))

    needs = [
        "<b>1. Shortcode Activation</b> - *712*55# for USSD access (or alternative shortcode)",
        "<b>2. SMS Shortcode</b> - Dedicated SMS shortcode for trading commands",
        "<b>3. Bulk SMS Pricing</b> - Competitive rates for platform-initiated notifications",
        "<b>4. T2 Wallet API Access</b> - For USSD-based payments (9mobile)",
        "<b>5. Revenue Share Agreement</b> - Fair split on SMS/USSD revenue generated",
        "<b>6. Go-to-Market Support</b> - Joint farmer outreach in pilot states (Lagos, Oyo, Kano)",
        "<b>7. Escrow License Partnership</b> - Telco's PSP/MMO license for legal fund holding in escrow",
    ]
    for need in needs:
        elements.append(Paragraph(need, styles['StepStyle']))
    elements.append(PageBreak())

    # ==================== SECTION 16: TECHNICAL ARCHITECTURE ====================
    elements.append(Paragraph("16. TECHNICAL ARCHITECTURE", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))

    arch_data = [
        ['Component', 'Technology', 'Purpose'],
        ['Web Framework', 'Flask (Python)', 'Core application server'],
        ['Database', 'PostgreSQL (Neon)', 'Scalable data storage'],
        ['Authentication', 'Flask-Login + OTP', 'Web login + SMS verification'],
        ['Payments', 'Paystack + T2 Wallet', 'Card + USSD payments'],
        ['AI Engine', 'OpenAI GPT', 'Natural language, risk scoring, escrow verification'],
        ['SMS Gateway', 'Africa\'s Talking API', 'SMS command processing'],
        ['USSD Gateway', 'Africa\'s Talking API', 'Feature phone menus'],
        ['Traceability', 'SHA256 Hash Chain', 'Blockchain-style supply chain tracking'],
        ['Escrow', 'Platform-managed + AI', 'Secure payment holding and release'],
        ['Scam Detection', '8-rule scoring engine', 'Fraud prevention'],
        ['Frontend', 'Bootstrap 5 + Jinja2', 'Responsive dark theme UI'],
        ['WhatsApp Gateway', 'Twilio (simulator mode)', 'Rich media trading channel'],
        ['Market Intelligence', 'TradojaIQ Engine', 'Price discovery, trust scores, demand insights'],
        ['Hosting', 'Replit Cloud', 'Auto-scaling deployment'],
    ]
    arch_table = Table(arch_data, colWidths=[1.5 * inch, 1.8 * inch, 2.5 * inch])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, SOFT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(arch_table)

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("DATA MODELS OVERVIEW", styles['SubHeader']))
    elements.append(Paragraph(
        "40+ database tables covering: Users (role-based), Produce (with GI certification), "
        "Orders (with OTP escrow), Transactions (Paystack + T2), Transport (cold chain IoT), "
        "SabiBuy (campaigns + orders), TraceChain (hash-linked events), ScamFlags (8-rule scoring), "
        "SMS/USSD Interactions (full audit trail), Device Fingerprints (collusion detection), "
        "Disputes (SLA-tracked), and more.",
        styles['BodyText2']
    ))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_GREEN, spaceAfter=15))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Contact: askme@tradoja.com", styles['CenterBold']))
    elements.append(Paragraph(f"Live Platform: {base_url}", styles['CenterBold']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "TRADOJA - Trade + Oja (Market) - Building Africa's Food Security Infrastructure",
        ParagraphStyle('FinalTag', parent=styles['Normal'], fontSize=11,
                       textColor=BRAND_GREEN, alignment=TA_CENTER, fontName='Helvetica-Bold')
    ))

    doc.build(elements)
    return filename


if __name__ == '__main__':
    output = build_pdf()
    print(f"PDF generated: {output}")
