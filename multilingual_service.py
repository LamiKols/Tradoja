"""
Multilingual Message Templates Service for AgroLink
Supports English (en), Yoruba (yo), Hausa (ha), Pidgin (pcm), and Igbo (ig)
Used across USSD, SMS, and WhatsApp channels for rural farmer accessibility
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MultilingualService:
    """Comprehensive multilingual message service for digital inclusion"""
    
    SUPPORTED_LANGUAGES = ['en', 'yo', 'ha', 'pcm', 'ig']
    
    # Message templates organized by language and category
    TEMPLATES = {
        'en': {
            # Welcome and Registration
            'welcome': "Welcome to AgroLink! Nigeria's Agricultural Marketplace.",
            'welcome_back': "Welcome back, {name}!",
            'register_prompt': "To register, reply: JOIN [name] [location] [crop]",
            'registration_success': "You're registered as a farmer! Commands: LIST, PRICE, HELP",
            'already_registered': "You're already registered. Send HELP for commands.",
            
            # USSD Main Menu
            'ussd_main_menu': "AgroLink\n1. List Produce\n2. Check Prices\n3. My Listings\n4. Balance\n5. Register",
            'ussd_welcome': "Welcome to AgroLink USSD",
            
            # Produce Listing
            'list_prompt': "Enter: [crop] [quantity] [price]\nExample: RICE 50BAGS 45000",
            'list_success': "Listed: {quantity} {crop} at ₦{price}",
            'list_fail': "Listing failed. Check format: RICE 50BAGS 45000",
            
            # Price Check
            'price_prompt': "Enter crop name to check price:",
            'price_result': "{crop} Market Price:\nAverage: ₦{avg}/kg\nRange: ₦{min} - ₦{max}",
            'no_price_data': "No price data for {crop}. Try: TOMATOES, YAM, RICE",
            
            # My Listings
            'no_listings': "You have no active listings. Send LIST to create one.",
            'listings_header': "Your Active Listings:",
            'listing_item': "{num}. {crop} - {quantity} @ ₦{price}",
            
            # Balance and Payments
            'balance': "Your AgroLink Balance:\nT2 Wallet: ₦{t2_balance}\nPaystack: {paystack_status}",
            'payment_received': "Payment received: ₦{amount} for {produce}",
            'payment_pending': "Pending payment: ₦{amount}",
            
            # Errors and Help
            'invalid_command': "Invalid command. Send HELP for options.",
            'error': "Sorry, an error occurred. Please try again.",
            'help': "Commands:\nJOIN - Register\nLIST - List produce\nPRICE - Check prices\nHELP - This message\nSTOP - Unsubscribe",
            'session_expired': "Session expired. Please dial again.",
            
            # Agent Mode
            'agent_mode_start': "AGENT MODE: Registering farmer...",
            'agent_register_farmer': "Enter farmer details: [name] [phone] [location]",
            'agent_success': "Farmer {name} registered successfully!",
            
            # Matchmaking
            'match_found': "New buyer match for {crop}!\nBuyer: {buyer}\nQuantity: {quantity}\nPrice: ₦{price}\nReply ACCEPT or DECLINE",
            'match_accepted': "Match accepted! Contact {buyer} at {phone}",
            'match_declined': "Match declined. We'll find more buyers.",
            
            # WhatsApp specific
            'wa_voice_received': "Voice note received. Processing...",
            'wa_transcription': "I heard: \"{text}\"\nCreating listing from your voice message...",
        },
        
        'yo': {  # Yoruba
            'welcome': "Kaabo si AgroLink! Oja Ogbin Nigeria.",
            'welcome_back': "Kaabo pada, {name}!",
            'register_prompt': "Lati forukọsilẹ, fesi: JOIN [orukọ] [ipo] [irugbin]",
            'registration_success': "O ti forukọsilẹ bi agbe! Awọn aṣẹ: LIST, PRICE, HELP",
            'already_registered': "O ti forukọsilẹ tẹlẹ. Fi HELP ranṣẹ fun awọn aṣẹ.",
            
            'ussd_main_menu': "AgroLink\n1. Fi Ẹfọ Silẹ\n2. Wo Owo\n3. Awọn Iṣe Mi\n4. Iwontunwonsi\n5. Forukọsilẹ",
            'ussd_welcome': "Kaabo si AgroLink USSD",
            
            'list_prompt': "Tẹ: [irugbin] [iye] [owo]\nApẹẹrẹ: IRESI 50BAGS 45000",
            'list_success': "Ti a fi silẹ: {quantity} {crop} ni ₦{price}",
            'list_fail': "Ko le fi silẹ. Ṣayẹwo ọna: IRESI 50BAGS 45000",
            
            'price_prompt': "Tẹ orukọ irugbin lati ṣayẹwo owo:",
            'price_result': "{crop} Owo Oja:\nApapọ: ₦{avg}/kg\nIyatọ: ₦{min} - ₦{max}",
            'no_price_data': "Ko si data owo fun {crop}. Gbiyanju: TOMATI, ISU, IRESI",
            
            'no_listings': "O ko ni awọn atokọ ti n ṣiṣẹ. Fi LIST ranṣẹ lati ṣẹda ọkan.",
            'listings_header': "Awọn Atokọ Ti N Ṣiṣẹ:",
            'listing_item': "{num}. {crop} - {quantity} @ ₦{price}",
            
            'balance': "Iwontunwonsi AgroLink Rẹ:\nT2: ₦{t2_balance}\nPaystack: {paystack_status}",
            
            'invalid_command': "Aṣẹ ti ko tọ. Fi HELP ranṣẹ fun awọn aṣayan.",
            'error': "Ẹ ma binu, aṣiṣe kan ṣẹlẹ. Jọwọ gbiyanju lẹẹkansi.",
            'help': "Awọn Aṣẹ:\nJOIN - Forukọsilẹ\nLIST - Fi irugbin silẹ\nPRICE - Ṣayẹwo owo\nHELP - Ifiranṣẹ yii\nSTOP - Yọkuro",
            
            'match_found': "Olura titun fun {crop}!\nOlura: {buyer}\nIye: {quantity}\nOwo: ₦{price}\nDahun ACCEPT tabi DECLINE",
        },
        
        'ha': {  # Hausa
            'welcome': "Barka da zuwa AgroLink! Kasuwar Noma ta Nigeria.",
            'welcome_back': "Barka da dawowa, {name}!",
            'register_prompt': "Don rajista, amsa: JOIN [suna] [wuri] [amfani]",
            'registration_success': "An yi rajista a matsayin manomi! Umarni: LIST, PRICE, HELP",
            'already_registered': "An riga an yi maka rajista. Aika HELP don umarni.",
            
            'ussd_main_menu': "AgroLink\n1. Jera Amfanin Gona\n2. Duba Farashi\n3. Jerin Nawa\n4. Ma'auni\n5. Rajista",
            'ussd_welcome': "Barka da zuwa AgroLink USSD",
            
            'list_prompt': "Shigar: [amfani] [adadi] [farashi]\nMisali: SHINKAFA 50BAGS 45000",
            'list_success': "An jera: {quantity} {crop} a ₦{price}",
            'list_fail': "Jeri ya kasa. Duba tsari: SHINKAFA 50BAGS 45000",
            
            'price_prompt': "Shigar sunan amfanin gona don duba farashi:",
            'price_result': "{crop} Farashin Kasuwa:\nMatsakaici: ₦{avg}/kg\nKewaya: ₦{min} - ₦{max}",
            'no_price_data': "Babu bayanan farashi don {crop}. Gwada: TUMATIR, DOYA, SHINKAFA",
            
            'no_listings': "Ba ka da jerin aiki. Aika LIST don ƙirƙira ɗaya.",
            'listings_header': "Jerin Aikinka:",
            'listing_item': "{num}. {crop} - {quantity} @ ₦{price}",
            
            'balance': "Ma'aunin AgroLink Naka:\nT2: ₦{t2_balance}\nPaystack: {paystack_status}",
            
            'invalid_command': "Umarnin da ba daidai ba. Aika HELP don zaɓuɓɓuka.",
            'error': "Yi hakuri, kuskure ya faru. Don Allah sake gwadawa.",
            'help': "Umarni:\nJOIN - Rajista\nLIST - Jera amfani\nPRICE - Duba farashi\nHELP - Wannan saƙo\nSTOP - Daina",
            
            'match_found': "Sabon mai siya don {crop}!\nMai Siya: {buyer}\nAdadi: {quantity}\nFarashi: ₦{price}\nAmsa ACCEPT ko DECLINE",
        },
        
        'pcm': {  # Nigerian Pidgin
            'welcome': "Welcome to AgroLink! Na Nigeria Farm Market.",
            'welcome_back': "You don come back, {name}!",
            'register_prompt': "To register, reply: JOIN [your name] [where you dey] [wetin you dey grow]",
            'registration_success': "E don register you as farmer! Commands: LIST, PRICE, HELP",
            'already_registered': "You don already register. Send HELP for commands.",
            
            'ussd_main_menu': "AgroLink\n1. Put Produce\n2. Check Price\n3. My Produce\n4. My Balance\n5. Register",
            'ussd_welcome': "Welcome to AgroLink USSD",
            
            'list_prompt': "Type: [produce] [how many] [price]\nExample: RICE 50BAGS 45000",
            'list_success': "E don list: {quantity} {crop} for ₦{price}",
            'list_fail': "E no work. Check format: RICE 50BAGS 45000",
            
            'price_prompt': "Type wetin you wan check price for:",
            'price_result': "{crop} Market Price:\nAverage: ₦{avg}/kg\nRange: ₦{min} - ₦{max}",
            'no_price_data': "We no get price for {crop}. Try: TOMATO, YAM, RICE",
            
            'no_listings': "You never put any produce. Send LIST to add one.",
            'listings_header': "Your Produce wey dey market:",
            'listing_item': "{num}. {crop} - {quantity} @ ₦{price}",
            
            'balance': "Your AgroLink Money:\nT2 Wallet: ₦{t2_balance}\nPaystack: {paystack_status}",
            
            'invalid_command': "That command no correct. Send HELP for options.",
            'error': "Sorry, wahala happen. Abeg try again.",
            'help': "Commands:\nJOIN - Register\nLIST - Put produce\nPRICE - Check price\nHELP - This message\nSTOP - Comot",
            
            'match_found': "New buyer dey for your {crop}!\nBuyer: {buyer}\nHow Many: {quantity}\nPrice: ₦{price}\nReply ACCEPT or DECLINE",
        },
        
        'ig': {  # Igbo
            'welcome': "Nno na AgroLink! Ahịa Ọrụ Ugbo Nigeria.",
            'welcome_back': "Nnọọ, {name}!",
            'register_prompt': "Iji debanye aha, zaa: JOIN [aha] [ebe] [ihe ọkụkụ]",
            'registration_success': "E debanyela gị dị ka onye ọrụ ugbo! Iwu: LIST, PRICE, HELP",
            'already_registered': "E debanyela aha gị. Zipu HELP maka iwu.",
            
            'ussd_main_menu': "AgroLink\n1. Dee Ihe Ubi\n2. Lee Ọnụ Ahịa\n3. Ihe Ndepụta M\n4. Ego M\n5. Debanye Aha",
            'ussd_welcome': "Nno na AgroLink USSD",
            
            'list_prompt': "Tinye: [ihe ọkụkụ] [ole] [ọnụ ahịa]\nỌmụmaatụ: RICE 50BAGS 45000",
            'list_success': "E depụtala: {quantity} {crop} n'ọnụ ₦{price}",
            'list_fail': "Ọ dịghị arụ ọrụ. Lee usoro: RICE 50BAGS 45000",
            
            'price_prompt': "Tinye aha ihe ọkụkụ iji lelee ọnụ ahịa:",
            'price_result': "{crop} Ọnụ Ahịa Ahịa:\nNkezi: ₦{avg}/kg\nỌdịiche: ₦{min} - ₦{max}",
            'no_price_data': "Enweghị data ọnụ ahịa maka {crop}. Nwaa: TOMATO, JI, RICE",
            
            'no_listings': "Ị nweghị ndepụta na-arụ ọrụ. Zipu LIST ịmepụta otu.",
            'listings_header': "Ndepụta Gị Na-arụ Ọrụ:",
            'listing_item': "{num}. {crop} - {quantity} @ ₦{price}",
            
            'balance': "Ego AgroLink Gị:\nT2: ₦{t2_balance}\nPaystack: {paystack_status}",
            
            'invalid_command': "Iwu anaghị arụ ọrụ. Zipu HELP maka nhọrọ.",
            'error': "Ndo, nsogbu mere. Biko nwaa ọzọ.",
            'help': "Iwu:\nJOIN - Debanye aha\nLIST - Dee ihe ubi\nPRICE - Lee ọnụ ahịa\nHELP - Ozi a\nSTOP - Kwụsị",
            
            'match_found': "Onye ọzụzụ ọhụrụ maka {crop}!\nOnye Ọzụzụ: {buyer}\nOle: {quantity}\nỌnụ Ahịa: ₦{price}\nZaa ACCEPT ma ọ bụ DECLINE",
        }
    }
    
    def __init__(self, default_language: str = 'en'):
        """Initialize the multilingual service"""
        self.default_language = default_language if default_language in self.SUPPORTED_LANGUAGES else 'en'
    
    def get_message(self, key: str, language: str = None, **kwargs) -> str:
        """
        Get a translated message with optional variable substitution
        
        Args:
            key: The message template key
            language: Target language code (en, yo, ha, pcm, ig)
            **kwargs: Variables to substitute in the message
            
        Returns:
            Translated and formatted message string
        """
        lang = language if language in self.SUPPORTED_LANGUAGES else self.default_language
        
        # Try to get message in requested language, fall back to English
        message = self.TEMPLATES.get(lang, {}).get(key)
        if not message:
            message = self.TEMPLATES['en'].get(key, f"[Missing: {key}]")
        
        # Substitute variables
        try:
            return message.format(**kwargs) if kwargs else message
        except KeyError as e:
            logger.warning(f"Missing template variable: {e} in message key: {key}")
            return message
    
    def get_ussd_menu(self, menu_name: str, language: str = None) -> str:
        """Get USSD menu in specified language"""
        return self.get_message(f'ussd_{menu_name}', language)
    
    def detect_language_from_text(self, text: str) -> str:
        """
        Simple language detection based on common words/patterns
        Returns detected language code or 'en' as default
        """
        text_lower = text.lower()
        
        # Yoruba indicators
        yoruba_words = ['kaabo', 'bawo', 'ẹ ku', 'oruko', 'kilode', 'se', 'mo fe']
        if any(word in text_lower for word in yoruba_words):
            return 'yo'
        
        # Hausa indicators
        hausa_words = ['barka', 'sannu', 'yaya', 'ina', 'kana', 'wani', 'zan']
        if any(word in text_lower for word in hausa_words):
            return 'ha'
        
        # Pidgin indicators
        pidgin_words = ['wetin', 'dey', 'abeg', 'na', 'wahala', 'oya', 'how far', 'e don']
        if any(word in text_lower for word in pidgin_words):
            return 'pcm'
        
        # Igbo indicators
        igbo_words = ['nno', 'kedu', 'biko', 'odi', 'anyi', 'gini', 'nke']
        if any(word in text_lower for word in igbo_words):
            return 'ig'
        
        # Default to English
        return 'en'
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name"""
        names = {
            'en': 'English',
            'yo': 'Yoruba',
            'ha': 'Hausa',
            'pcm': 'Pidgin',
            'ig': 'Igbo'
        }
        return names.get(code, 'English')
    
    def format_currency(self, amount: float, currency: str = 'NGN') -> str:
        """Format currency for display"""
        if currency == 'NGN':
            return f"₦{amount:,.2f}"
        return f"{currency} {amount:,.2f}"
    
    def get_crop_name_localized(self, crop: str, language: str = 'en') -> str:
        """Get localized crop name (common crops)"""
        crop_translations = {
            'en': {
                'rice': 'Rice', 'yam': 'Yam', 'cassava': 'Cassava', 
                'tomatoes': 'Tomatoes', 'maize': 'Maize', 'beans': 'Beans',
                'pepper': 'Pepper', 'groundnut': 'Groundnut', 'palm oil': 'Palm Oil'
            },
            'yo': {
                'rice': 'Iresi', 'yam': 'Isu', 'cassava': 'Ege',
                'tomatoes': 'Tomatii', 'maize': 'Agbado', 'beans': 'Ewa',
                'pepper': 'Ata', 'groundnut': 'Epa', 'palm oil': 'Epo Pupa'
            },
            'ha': {
                'rice': 'Shinkafa', 'yam': 'Doya', 'cassava': 'Rogo',
                'tomatoes': 'Tumatir', 'maize': 'Masara', 'beans': 'Wake',
                'pepper': 'Barkono', 'groundnut': 'Gyada', 'palm oil': 'Man Shanu'
            },
            'pcm': {
                'rice': 'Rice', 'yam': 'Yam', 'cassava': 'Cassava',
                'tomatoes': 'Tomato', 'maize': 'Corn', 'beans': 'Beans',
                'pepper': 'Pepper', 'groundnut': 'Groundnut', 'palm oil': 'Palm Oil'
            },
            'ig': {
                'rice': 'Osikapa', 'yam': 'Ji', 'cassava': 'Akpu',
                'tomatoes': 'Tomato', 'maize': 'Ọka', 'beans': 'Agwa',
                'pepper': 'Ose', 'groundnut': 'Ahụekere', 'palm oil': 'Mmanụ Nkwụ'
            }
        }
        
        lang_crops = crop_translations.get(language, crop_translations['en'])
        return lang_crops.get(crop.lower(), crop.title())


# Create singleton instance
multilingual = MultilingualService()


def get_message(key: str, language: str = None, **kwargs) -> str:
    """Convenience function to get translated messages"""
    return multilingual.get_message(key, language, **kwargs)


def detect_language(text: str) -> str:
    """Convenience function for language detection"""
    return multilingual.detect_language_from_text(text)
