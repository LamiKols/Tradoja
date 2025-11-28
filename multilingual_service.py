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
            'ussd_main_menu': "AgroLink\n1. List Produce\n2. Check Prices\n3. My Listings\n4. Balance\n5. Register\n6. Transport Jobs\n7. Register as Buyer\n8. Become Agent\n9. Agent Menu",
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
            
            # Transport/Logistics
            'transport_menu': "TRANSPORT JOBS\n1. New Jobs\n2. Register as Transporter\n3. My Bids\n4. Active Trips\n5. Balance\n0. Back",
            'new_transport_job': "New Job #{job_id}: Transport {produce} from {from_location} to {to_location}. Weight: {weight}T. Est. {price}. Reply: BID {job_id} [amount]",
            'bid_placed': "Bid of {amount} placed on Job #{job_id}. You'll be notified if accepted.",
            'bid_accepted': "Your bid of {amount} for Job #{job_id} has been accepted! 50% payment released to wallet.",
            # Transport LITE Registration
            'register_transporter_first': "Please register as transporter first.\nDial *712*55# > 6 > 2 or text JOIN TRK [name] [location] [type]",
            'register_transporter_name': "Enter your name or company name:",
            'register_transporter_location': "Enter your main location (state/city):",
            'register_transporter_vehicle': "Choose vehicle type:\n1. Pickup/Motorcycle\n2. 5-10 Ton Truck\n3. 15-30 Ton Truck\n4. Refrigerated/Cold Truck",
            'register_transporter_success': "Thank you {name}!\nYou are now registered as transporter.\nID: {transporter_id}\nYou will receive jobs immediately.\nSend DOC to complete profile later.",
            'already_transporter': "You are already registered as transporter.\nID: {transporter_id}",
            'transport_balance': "Transporter ID: {transporter_id}\nWallet Balance: ₦{balance}",
            'doc_response': "Complete your profile to get higher ranking and cold-chain bonus.\nVisit: agrolink.ng/transport/complete\nOr call agent: 08012345678",
            
            # Buyer LITE Registration
            'register_buyer_first': "Please register as buyer first.\nDial *712*55# > 7 or text JOIN BUYER [name] [location]",
            'register_buyer_name': "Enter your name or business name:",
            'register_buyer_location': "Enter your location (state/city):",
            'register_buyer_type': "What type of buyer are you?\n1. Retail Buyer\n2. Bulk Trader\n3. Restaurant/Hotel\n4. Agro-Processor",
            'register_buyer_success': "Welcome {name}!\nYou are now registered as buyer.\nYou will receive produce alerts.\nText PRICE to check prices.",
            'already_buyer': "You are already registered as a buyer.",
            
            # Agent LITE Registration
            'register_agent_first': "Please register as agent first.\nDial *712*55# > 8 or text JOIN AGENT [name] [location]",
            'register_agent_name': "Enter your full name:",
            'register_agent_location': "Enter your location/LGA:",
            'register_agent_referral': "Enter referral code or NYSC State Code\n(Press 0 to skip):",
            'register_agent_success': "You are now an AgroLink Agent!\nYour ID: {agent_id}\nYou will earn ₦200 airtime for every 10 farmers you register.\nApproval in 24 hrs. Start registering now!",
            'already_agent': "You are already an agent.\nID: {agent_id}",
            'agent_menu': "AGENT MENU ({agent_id})\nStatus: {status}\n1. Register Farmer\n2. Register Buyer\n3. My Farmers\n4. My Earnings\n0. Back",
            'agent_pending_approval': "Your agent account is pending approval.\nApproval in 24 hrs. You will be notified via SMS.",
            'agent_farmer_name': "Enter farmer's full name:",
            'agent_farmer_location': "Enter farmer's location:",
            'agent_farmer_crop': "Enter farmer's main crop:",
            'agent_farmer_success': "Farmer {name} registered!\nTotal farmers: {total}\nKeep going!",
            'agent_buyer_name': "Enter buyer's name:",
            'agent_buyer_location': "Enter buyer's location:",
            'agent_buyer_success': "Buyer {name} registered!\nTotal buyers: {total}",
            'agent_no_farmers': "You haven't registered any farmers yet.\nPress 1 to start registering.",
            'agent_farmers_list': "Your Farmers:\n{farmers}\n\nTotal: {total}",
            'agent_earnings': "Your Earnings:\nPending: ₦{pending}\nTotal Earned: ₦{total}\n\nFarmers: {farmers}\nBuyers: {buyers}",
            'bid_rejected': "Your bid for Job #{job_id} was not selected. Try other jobs!",
            'trip_started': "Trip #{job_id} started. Track temperature at {tracking_url}",
            'delivery_complete': "Delivery complete! Final payment of {amount} released to your wallet.",
            'cold_chain_bonus': "Cold chain verified! Bonus of {amount} added.",
            'cold_chain_alert': "ALERT: Temperature out of range! Current: {temp}°C. Please check.",
            'no_available_jobs': "No jobs available in your area. We'll notify you when new jobs arrive.",
            'your_bids': "Your Bids:\n{bids_list}",
            'active_trips': "Active Trips:\n{trips_list}",
            
            # SabiBuy Group-Buy System
            'sabibuy_menu': "SABIBUY\n10. Start SabiBuy\n11. Join SabiBuy\n12. My SabiBuys\n13. Earnings\n0. Back",
            'sabibuy_name': "SabiBuy",
            'sabibuyer_name': "SabiBuyer",
            'sabibuy_captain': "SabiBuyer Captain",
            'sabibuy_select_produce': "Choose produce to sell:\n{produce_list}\nEnter number:",
            'sabibuy_set_price': "Farm price: ₦{farm_price}\nSuggested: ₦{suggested} (profit ₦{margin}/unit)\nEnter your selling price:",
            'sabibuy_set_location': "Enter delivery LGA/Market:",
            'sabibuy_confirm': "CONFIRM SabiBuy:\n{produce} @ ₦{price}\nMin: {min_qty} {unit}s\nDelivery: {location}\n1. Confirm\n2. Cancel",
            'sabibuy_created': "SabiBuy Created!\nCode: {code}\nForward to your people!\nShare: {code} {quantity} bags",
            'sabibuy_share_prompt': "Forward {code} to your people!",
            'sabibuy_join_prompt': "Enter SabiBuy code:",
            'sabibuy_join_quantity': "Code: {code}\n{produce} @ ₦{price}/{unit}\nEnter quantity:",
            'sabibuy_join_confirm': "Order: {quantity} {unit}s\nTotal: ₦{total}\n1. Pay with T2 Wallet\n2. Pay with Paystack\n3. Cancel",
            'sabibuy_order_placed': "Order placed!\n{quantity} {unit}s for ₦{total}\nPay now to secure your order.",
            'sabibuy_payment_confirmed': "Payment confirmed for {code}!\n{quantity} {unit}s @ {amount}.\nWe'll notify you when ready.",
            'sabibuy_order_received': "New order for {code}!\nProgress: {progress}%",
            'sabibuy_batch_closed': "Batch CLOSED!\n{code}: {quantity} units sold!\nBooking logistics now...",
            'sabibuy_logistics_booked': "Logistics booked for {code}!\nTruck arriving soon.",
            'sabibuy_profit_paid': "PROFIT PAID!\n{amount} sent to your wallet!",
            'sabibuy_delivery_complete': "Delivery complete!\n{quantity} {unit}s ready at {location}",
            'sabibuy_progress_update': "Your SabiBuy {code} is {progress}% full!",
            'sabibuy_invalid_code': "Invalid SabiBuy code. Check and try again.",
            'sabibuy_expired': "This SabiBuy has expired.",
            'sabibuy_max_campaigns': "Max {max} active SabiBuys. Upgrade to Captain for unlimited!",
            'sabibuy_upgrade_captain': "Upgrade to SabiBuyer Captain:\n₦5,000 one-time\nUnlimited campaigns + Gold Badge\n1. Upgrade\n2. Cancel",
            'sabibuy_captain_welcome': "Welcome SabiBuyer Captain!\nGold Badge unlocked!\nUnlimited campaigns enabled!",
            'sabibuy_my_campaigns': "Your SabiBuys:\n{campaigns_list}",
            'sabibuy_earnings': "SabiBuyer Earnings:\nPending: ₦{pending}\nTotal: ₦{total}\nCampaigns: {campaigns}",
            'sabibuy_leaderboard': "Top SabiBuyers:\n{leaderboard}",
        },
        
        'yo': {  # Yoruba
            'welcome': "Kaabo si AgroLink! Oja Ogbin Nigeria.",
            'welcome_back': "Kaabo pada, {name}!",
            'register_prompt': "Lati forukọsilẹ, fesi: JOIN [orukọ] [ipo] [irugbin]",
            'registration_success': "O ti forukọsilẹ bi agbe! Awọn aṣẹ: LIST, PRICE, HELP",
            'already_registered': "O ti forukọsilẹ tẹlẹ. Fi HELP ranṣẹ fun awọn aṣẹ.",
            
            'ussd_main_menu': "AgroLink\n1. Fi Ẹfọ Silẹ\n2. Wo Owo\n3. Awọn Iṣe Mi\n4. Iwontunwonsi\n5. Forukọsilẹ\n6. Awọn Iṣẹ Gbigbe\n7. Forukọsilẹ bi Olura\n8. Di Aṣoju\n9. Akojọ Aṣoju",
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
            
            # Transport/Logistics
            'transport_menu': "AWỌN IṢẸ GBIGBE\n1. Iṣẹ Titun\n2. Forukọsilẹ bi Awakọ\n3. Awọn Ifiranṣẹ Mi\n4. Irin-ajo Ti N Ṣiṣẹ\n5. Iwontunwonsi\n0. Pada",
            'new_transport_job': "Iṣẹ #{job_id}: Gbe {produce} lati {from_location} si {to_location}. Iwuwo: {weight}T. Idiyele: {price}. Dahun: BID {job_id} [iye]",
            'bid_placed': "A ti fi ₦{amount} silẹ fun Iṣẹ #{job_id}.",
            'bid_accepted': "A ti gba ifiranṣẹ rẹ ti ₦{amount} fun Iṣẹ #{job_id}! A ti tu 50% silẹ.",
            # Transport LITE Registration
            'register_transporter_first': "Jọwọ forukọsilẹ bi awakọ.\nPe *712*55# > 6 > 2 tabi fi JOIN TRK [orukọ] [ipo] [iru] ranṣẹ",
            'register_transporter_name': "Tẹ orukọ tabi orukọ ile-iṣẹ rẹ:",
            'register_transporter_location': "Tẹ ipo akọkọ rẹ (ipinlẹ/ilu):",
            'register_transporter_vehicle': "Yan iru ọkọ:\n1. Kẹkẹ\n2. Mọto Tọọnu 5-10\n3. Mọto Tọọnu 15-30\n4. Mọto Tutu/Firiji",
            'register_transporter_success': "O ṣeun {name}!\nO ti forukọsilẹ bi awakọ.\nID: {transporter_id}\nIwọ yoo gba iṣẹ lẹsẹkẹsẹ.\nFi DOC ranṣẹ lati pari profaili rẹ.",
            'already_transporter': "O ti forukọsilẹ bi awakọ.\nID: {transporter_id}",
            'transport_balance': "ID Awakọ: {transporter_id}\nIwontunwonsi: ₦{balance}",
            'doc_response': "Pari profaili rẹ lati ni ipo giga ati bonus firiji.\nṢabẹwo: agrolink.ng/transport/complete",
            
            # Buyer LITE Registration
            'register_buyer_first': "Jọwọ forukọsilẹ bi olura.\nPe *712*55# > 7 tabi fi JOIN BUYER [orukọ] [ipo] ranṣẹ",
            'register_buyer_name': "Tẹ orukọ tabi orukọ iṣowo rẹ:",
            'register_buyer_location': "Tẹ ipo rẹ (ipinlẹ/ilu):",
            'register_buyer_type': "Iru olura wo ni o jẹ?\n1. Olura Sọtọ\n2. Oniṣowo Pupo\n3. Ile Ounjẹ/Hoteli\n4. Oniṣẹ Ogbin",
            'register_buyer_success': "Kaabo {name}!\nO ti forukọsilẹ bi olura.\nIwọ yoo gba ifiranṣẹ nipa irugbin.\nFi PRICE ranṣẹ lati ṣayẹwo owo.",
            'already_buyer': "O ti forukọsilẹ tẹlẹ bi olura.",
            
            # Agent LITE Registration
            'register_agent_first': "Jọwọ forukọsilẹ bi aṣoju.\nPe *712*55# > 8 tabi fi JOIN AGENT [orukọ] [ipo] ranṣẹ",
            'register_agent_name': "Tẹ orukọ rẹ ni kikun:",
            'register_agent_location': "Tẹ ipo/LGA rẹ:",
            'register_agent_referral': "Tẹ koodu itọkasi tabi koodu NYSC\n(Tẹ 0 lati fo):",
            'register_agent_success': "O ti di Aṣoju AgroLink!\nID Rẹ: {agent_id}\nIwọ yoo gba ₦200 airtime fun agbe 10 ti o forukọsilẹ.\nIfọwọsi ni wakati 24. Bẹrẹ forukọsilẹ bayi!",
            'already_agent': "O ti jẹ aṣoju tẹlẹ.\nID: {agent_id}",
            'agent_menu': "AKOJỌ AṢOJU ({agent_id})\nIpo: {status}\n1. Forukọsilẹ Agbe\n2. Forukọsilẹ Olura\n3. Awọn Agbe Mi\n4. Ere Mi\n0. Pada",
            'agent_pending_approval': "Akọọlẹ aṣoju rẹ n duro de ifọwọsi.\nIfọwọsi ni wakati 24.",
            'agent_farmer_name': "Tẹ orukọ agbe ni kikun:",
            'agent_farmer_location': "Tẹ ipo agbe:",
            'agent_farmer_crop': "Tẹ irugbin akọkọ agbe:",
            'agent_farmer_success': "A ti forukọsilẹ agbe {name}!\nApapọ agbe: {total}",
            'agent_buyer_name': "Tẹ orukọ olura:",
            'agent_buyer_location': "Tẹ ipo olura:",
            'agent_buyer_success': "A ti forukọsilẹ olura {name}!\nApapọ olura: {total}",
            'agent_no_farmers': "O ko ti forukọsilẹ agbe kankan.",
            'agent_farmers_list': "Awọn Agbe Rẹ:\n{farmers}\n\nApapọ: {total}",
            'agent_earnings': "Ere Rẹ:\nTi n duro: ₦{pending}\nApapọ: ₦{total}\n\nAgbe: {farmers}\nOlura: {buyers}",
            'delivery_complete': "Ifijiṣẹ ti pari! A ti tu owo ikẹhin ti ₦{amount} silẹ.",
            
            # SabiBuy (SabiRa) - Yoruba
            'sabibuy_menu': "SABIRA\n10. Bẹrẹ SabiRa\n11. Darapọ SabiRa\n12. Awọn SabiRa Mi\n13. Ere\n0. Pada",
            'sabibuy_name': "SabiRa",
            'sabibuyer_name': "Oníṣòwò Sabi",
            'sabibuy_captain': "Olórí Oníṣòwò Sabi",
            'sabibuy_select_produce': "Yan irugbin lati ta:\n{produce_list}\nTẹ nọmba:",
            'sabibuy_set_price': "Owo agbe: ₦{farm_price}\nA ṣeduro: ₦{suggested} (ere ₦{margin}/ọkan)\nTẹ owo titaja rẹ:",
            'sabibuy_set_location': "Tẹ LGA/Oja ifijiṣẹ:",
            'sabibuy_confirm': "JẸRI SabiRa:\n{produce} @ ₦{price}\nIye kekere: {min_qty} {unit}\nIfijiṣẹ: {location}\n1. Jẹri\n2. Fagilee",
            'sabibuy_created': "SabiRa Ti Ṣẹda!\nKoodu: {code}\nFi ranṣẹ si awọn eniyan rẹ!",
            'sabibuy_share_prompt': "Fi {code} ranṣẹ si awọn eniyan rẹ!",
            'sabibuy_join_prompt': "Tẹ koodu SabiRa:",
            'sabibuy_join_quantity': "Koodu: {code}\n{produce} @ ₦{price}/{unit}\nTẹ iye:",
            'sabibuy_join_confirm': "Aṣẹ: {quantity} {unit}\nApapọ: ₦{total}\n1. San pẹlu T2\n2. San pẹlu Paystack\n3. Fagilee",
            'sabibuy_order_placed': "A ti gba aṣẹ!\n{quantity} {unit} fun ₦{total}\nSan ni bayi.",
            'sabibuy_payment_confirmed': "A ti gba isanwo fun {code}!\n{quantity} {unit} @ {amount}.",
            'sabibuy_order_received': "Aṣẹ titun fun {code}!\nIlọsiwaju: {progress}%",
            'sabibuy_batch_closed': "A ti pa!\n{code}: {quantity} ti ta!\nA n ṣeto gbigbe...",
            'sabibuy_logistics_booked': "A ti ṣeto gbigbe fun {code}!\nMọto n bọ.",
            'sabibuy_profit_paid': "A TI SAN ERE!\n{amount} ti ranṣẹ si apo rẹ!",
            'sabibuy_delivery_complete': "Ifijiṣẹ ti pari!\n{quantity} {unit} ti ṣetan ni {location}",
            'sabibuy_progress_update': "SabiRa {code} rẹ ti kun {progress}%!",
            'sabibuy_invalid_code': "Koodu SabiRa ti ko tọ.",
            'sabibuy_captain_welcome': "Kaabo Olórí Oníṣòwò Sabi!\nBadge Goolu ti ṣii!",
        },
        
        'ha': {  # Hausa
            'welcome': "Barka da zuwa AgroLink! Kasuwar Noma ta Nigeria.",
            'welcome_back': "Barka da dawowa, {name}!",
            'register_prompt': "Don rajista, amsa: JOIN [suna] [wuri] [amfani]",
            'registration_success': "An yi rajista a matsayin manomi! Umarni: LIST, PRICE, HELP",
            'already_registered': "An riga an yi maka rajista. Aika HELP don umarni.",
            
            'ussd_main_menu': "AgroLink\n1. Jera Amfanin Gona\n2. Duba Farashi\n3. Jerin Nawa\n4. Ma'auni\n5. Rajista\n6. Aikin Mota\n7. Rajista a matsayin Mai Saya\n8. Zama Wakili\n9. Akwatin Wakili",
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
            
            # Transport/Logistics
            'transport_menu': "AIKIN MOTA\n1. Sabbin Aiyuka\n2. Yi Rajista a matsayin Direba\n3. Ƙimar Nawa\n4. Tafiye-tafiye masu aiki\n5. Ma'auni\n0. Koma",
            'new_transport_job': "Aiki #{job_id}: Kai {produce} daga {from_location} zuwa {to_location}. Nauyi: {weight}T. Kuɗi: {price}. Amsa: BID {job_id} [adadi]",
            'bid_placed': "An ajiye ₦{amount} don Aiki #{job_id}.",
            'bid_accepted': "An karɓi ₦{amount} don Aiki #{job_id}! An saki 50%.",
            # Transport LITE Registration
            'register_transporter_first': "Da fatan za a yi rajista a matsayin direba.\nKira *712*55# > 6 > 2 ko aika JOIN TRK [suna] [wuri] [iri]",
            'register_transporter_name': "Shigar da sunan ku ko sunan kamfani:",
            'register_transporter_location': "Shigar da wurin ku (jiha/gari):",
            'register_transporter_vehicle': "Zaɓi irin mota:\n1. Keke/Babur\n2. Mota Ton 5-10\n3. Mota Ton 15-30\n4. Mota Mai Sanyi/Firiji",
            'register_transporter_success': "Na gode {name}!\nAn yi muku rajista a matsayin direba.\nID: {transporter_id}\nZa ku sami aiyuka nan da nan.\nAika DOC don kammala bayananku.",
            'already_transporter': "An riga an yi muku rajista a matsayin direba.\nID: {transporter_id}",
            'transport_balance': "ID Direba: {transporter_id}\nMa'auni: ₦{balance}",
            'doc_response': "Kammala bayananku don samun matsayi mafi girma da bonus firiji.\nZiyarci: agrolink.ng/transport/complete",
            
            # Buyer LITE Registration
            'register_buyer_first': "Da fatan za a yi rajista a matsayin mai saya.\nKira *712*55# > 7 ko aika JOIN BUYER [suna] [wuri]",
            'register_buyer_name': "Shigar da sunan ku ko sunan kasuwanci:",
            'register_buyer_location': "Shigar da wurin ku (jiha/gari):",
            'register_buyer_type': "Wane irin mai saya ne ku?\n1. Mai Saye Daki-Daki\n2. Mai Cinikin Girma\n3. Gidan Abinci/Otal\n4. Mai Sarrafa Noma",
            'register_buyer_success': "Barka da zuwa {name}!\nAn yi muku rajista a matsayin mai saya.\nZa ku sami saƙon kayan amfanin gona.\nAika PRICE don duba farashi.",
            'already_buyer': "An riga an yi muku rajista a matsayin mai saya.",
            
            # Agent LITE Registration
            'register_agent_first': "Da fatan za a yi rajista a matsayin wakili.\nKira *712*55# > 8 ko aika JOIN AGENT [suna] [wuri]",
            'register_agent_name': "Shigar da sunan ku duka:",
            'register_agent_location': "Shigar da wurin/LGA:",
            'register_agent_referral': "Shigar da lambar shawarwari ko lambar NYSC\n(Latsa 0 don tsallake):",
            'register_agent_success': "Yanzu kai ne Wakili na AgroLink!\nID naka: {agent_id}\nZa ku sami ₦200 airtime don manoma 10 da ku yi rajista.\nAmincewa cikin sa'o'i 24. Fara yanzu!",
            'already_agent': "An riga an yi muku rajista a matsayin wakili.\nID: {agent_id}",
            'agent_menu': "AKWATIN WAKILI ({agent_id})\nMatsayi: {status}\n1. Rajista Manomi\n2. Rajista Mai Saya\n3. Manomina\n4. Ribar Na\n0. Komawa",
            'agent_pending_approval': "Asusun wakili na jiran amincewa.\nAmincewa cikin sa'o'i 24.",
            'agent_farmer_name': "Shigar da sunan manomi duka:",
            'agent_farmer_location': "Shigar da wurin manomi:",
            'agent_farmer_crop': "Shigar da amfanin gona na manomi:",
            'agent_farmer_success': "An yi rajista manomi {name}!\nJimillar manoma: {total}",
            'agent_buyer_name': "Shigar da sunan mai saya:",
            'agent_buyer_location': "Shigar da wurin mai saya:",
            'agent_buyer_success': "An yi rajista mai saya {name}!\nJimillar masu saya: {total}",
            'agent_no_farmers': "Ba ku yi rajista kowane manomi ba tukuna.",
            'agent_farmers_list': "Manomanku:\n{farmers}\n\nJimilla: {total}",
            'agent_earnings': "Ribarku:\nTana Jira: ₦{pending}\nJimilla: ₦{total}\n\nManoma: {farmers}\nMasu Saya: {buyers}",
            'delivery_complete': "Bayarwa ta kammala! An saki ₦{amount} na ƙarshe.",
            'cold_chain_bonus': "An tabbatar da sanyi! An ƙara ₦{amount}.",
            
            # SabiBuy (SaniSaya) - Hausa
            'sabibuy_menu': "SANISAYA\n10. Fara SaniSaya\n11. Shiga SaniSaya\n12. SaniSaya Nawa\n13. Riba\n0. Koma",
            'sabibuy_name': "SaniSaya",
            'sabibuyer_name': "Mai Hankali",
            'sabibuy_captain': "Shugaban Mai Hankali",
            'sabibuy_select_produce': "Zaɓi amfanin gona don sayarwa:\n{produce_list}\nShigar lamba:",
            'sabibuy_set_price': "Farashin manomi: ₦{farm_price}\nAn ba da shawara: ₦{suggested} (riba ₦{margin}/ɗaya)\nShigar farashin sayarwa:",
            'sabibuy_set_location': "Shigar LGA/Kasuwa don bayarwa:",
            'sabibuy_confirm': "TABBATAR SaniSaya:\n{produce} @ ₦{price}\nMafi ƙaranci: {min_qty} {unit}\nBayarwa: {location}\n1. Tabbatar\n2. Soke",
            'sabibuy_created': "An Ƙirƙiri SaniSaya!\nLamba: {code}\nAika ga mutanenka!",
            'sabibuy_share_prompt': "Aika {code} ga mutanenka!",
            'sabibuy_join_prompt': "Shigar lambar SaniSaya:",
            'sabibuy_join_quantity': "Lamba: {code}\n{produce} @ ₦{price}/{unit}\nShigar adadi:",
            'sabibuy_join_confirm': "Oda: {quantity} {unit}\nJimilla: ₦{total}\n1. Biya da T2\n2. Biya da Paystack\n3. Soke",
            'sabibuy_order_placed': "An sanya oda!\n{quantity} {unit} don ₦{total}\nBiya yanzu.",
            'sabibuy_payment_confirmed': "An tabbatar da biyan kuɗi don {code}!\n{quantity} {unit} @ {amount}.",
            'sabibuy_order_received': "Sabon oda don {code}!\nCi gaba: {progress}%",
            'sabibuy_batch_closed': "An rufe!\n{code}: An sayar da {quantity}!\nAna shirya jigilar...",
            'sabibuy_logistics_booked': "An shirya jigilar {code}!\nMota tana zuwa.",
            'sabibuy_profit_paid': "AN BIYA RIBA!\nAn aika {amount} zuwa walat ɗinka!",
            'sabibuy_delivery_complete': "Bayarwa ta kammala!\n{quantity} {unit} a shirye a {location}",
            'sabibuy_progress_update': "SaniSaya {code} naka ya cika {progress}%!",
            'sabibuy_invalid_code': "Lambar SaniSaya ba daidai ba.",
            'sabibuy_captain_welcome': "Barka Shugaban Mai Hankali!\nAn buɗe Badge na Zinari!",
        },
        
        'pcm': {  # Nigerian Pidgin
            'welcome': "Welcome to AgroLink! Na Nigeria Farm Market.",
            'welcome_back': "You don come back, {name}!",
            'register_prompt': "To register, reply: JOIN [your name] [where you dey] [wetin you dey grow]",
            'registration_success': "E don register you as farmer! Commands: LIST, PRICE, HELP",
            'already_registered': "You don already register. Send HELP for commands.",
            
            'ussd_main_menu': "AgroLink\n1. Put Produce\n2. Check Price\n3. My Produce\n4. My Balance\n5. Register\n6. Transport Work\n7. Register as Buyer\n8. Become Agent\n9. Agent Work",
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
            
            # Transport/Logistics
            'transport_menu': "TRANSPORT WORK\n1. New Job\n2. Register as Driver\n3. My Bids\n4. Active Trips\n5. Balance\n0. Go Back",
            'new_transport_job': "Job #{job_id}: Carry {produce} from {from_location} go {to_location}. Weight: {weight}T. Price: {price}. Reply: BID {job_id} [amount]",
            'bid_placed': "E don put your ₦{amount} for Job #{job_id}.",
            'bid_accepted': "Dem don accept your ₦{amount} for Job #{job_id}! 50% don enter your pocket.",
            # Transport LITE Registration
            'register_transporter_first': "Abeg register as driver first.\nDial *712*55# > 6 > 2 or text JOIN TRK [name] [location] [type]",
            'register_transporter_name': "Type your name or company name:",
            'register_transporter_location': "Type your main location (state/city):",
            'register_transporter_vehicle': "Choose your motor type:\n1. Okada/Pickup\n2. 5-10 Ton Motor\n3. 15-30 Ton Trailer\n4. Cold Chain/Fridge Motor",
            'register_transporter_success': "Thank you {name}!\nE don register you as driver.\nID: {transporter_id}\nYou go start dey receive job now now.\nText DOC to finish your profile later.",
            'already_transporter': "You don already register as driver.\nID: {transporter_id}",
            'transport_balance': "Driver ID: {transporter_id}\nBalance: ₦{balance}",
            'doc_response': "Finish your profile to get better ranking and cold-chain bonus.\nGo: agrolink.ng/transport/complete",
            
            # Buyer LITE Registration
            'register_buyer_first': "Abeg register as buyer first.\nDial *712*55# > 7 or text JOIN BUYER [name] [location]",
            'register_buyer_name': "Type your name or business name:",
            'register_buyer_location': "Type your location (state/city):",
            'register_buyer_type': "Wetin kind buyer you be?\n1. Small Small Buyer\n2. Big Trader\n3. Restaurant/Hotel\n4. Agro-Processor",
            'register_buyer_success': "Welcome {name}!\nE don register you as buyer.\nYou go dey receive produce alert.\nText PRICE to check price.",
            'already_buyer': "You don already register as buyer.",
            
            # Agent LITE Registration
            'register_agent_first': "Abeg register as agent first.\nDial *712*55# > 8 or text JOIN AGENT [name] [location]",
            'register_agent_name': "Type your full name:",
            'register_agent_location': "Type your location/LGA:",
            'register_agent_referral': "Type referral code or NYSC State Code\n(Press 0 to skip):",
            'register_agent_success': "You don become AgroLink Agent!\nYour ID: {agent_id}\nYou go earn ₦200 airtime for every 10 farmers wey you register.\nApproval go come in 24 hrs. Start now!",
            'already_agent': "You don already be agent.\nID: {agent_id}",
            'agent_menu': "AGENT MENU ({agent_id})\nStatus: {status}\n1. Register Farmer\n2. Register Buyer\n3. My Farmers\n4. My Money\n0. Go Back",
            'agent_pending_approval': "Your agent account dey wait for approval.\nApproval go come in 24 hrs.",
            'agent_farmer_name': "Type farmer full name:",
            'agent_farmer_location': "Type farmer location:",
            'agent_farmer_crop': "Type farmer main crop:",
            'agent_farmer_success': "Farmer {name} don register!\nTotal farmers: {total}",
            'agent_buyer_name': "Type buyer name:",
            'agent_buyer_location': "Type buyer location:",
            'agent_buyer_success': "Buyer {name} don register!\nTotal buyers: {total}",
            'agent_no_farmers': "You never register any farmer yet.",
            'agent_farmers_list': "Your Farmers:\n{farmers}\n\nTotal: {total}",
            'agent_earnings': "Your Money:\nPending: ₦{pending}\nTotal: ₦{total}\n\nFarmers: {farmers}\nBuyers: {buyers}",
            'delivery_complete': "Delivery don complete! ₦{amount} final payment don enter.",
            'cold_chain_bonus': "Cold chain verified! Bonus of ₦{amount} don add.",
            
            # SabiBuy - Pidgin
            'sabibuy_menu': "SABIBUY\n10. Start SabiBuy\n11. Join SabiBuy\n12. My SabiBuys\n13. My Money\n0. Go Back",
            'sabibuy_name': "SabiBuy",
            'sabibuyer_name': "SabiBuyer",
            'sabibuy_captain': "SabiBuyer Captain",
            'sabibuy_select_produce': "Choose produce wey you wan sell:\n{produce_list}\nType number:",
            'sabibuy_set_price': "Farm price: ₦{farm_price}\nWe suggest: ₦{suggested} (profit ₦{margin}/one)\nType your selling price:",
            'sabibuy_set_location': "Type delivery LGA/Market:",
            'sabibuy_confirm': "CONFIRM SabiBuy:\n{produce} @ ₦{price}\nMinimum: {min_qty} {unit}s\nDelivery: {location}\n1. Confirm\n2. Cancel",
            'sabibuy_created': "SabiBuy Don Create!\nCode: {code}\nForward am to your people!",
            'sabibuy_share_prompt': "Forward {code} to your people!",
            'sabibuy_join_prompt': "Type SabiBuy code:",
            'sabibuy_join_quantity': "Code: {code}\n{produce} @ ₦{price}/{unit}\nHow many you wan buy:",
            'sabibuy_join_confirm': "Order: {quantity} {unit}s\nTotal: ₦{total}\n1. Pay with T2 Wallet\n2. Pay with Paystack\n3. Cancel",
            'sabibuy_order_placed': "Order don place!\n{quantity} {unit}s for ₦{total}\nPay now make you secure am.",
            'sabibuy_payment_confirmed': "Payment don confirm for {code}!\n{quantity} {unit}s @ {amount}.\nWe go tell you when e ready.",
            'sabibuy_order_received': "New order for {code}!\nProgress: {progress}%",
            'sabibuy_batch_closed': "Batch don CLOSE!\n{code}: {quantity} units don sell!\nWe dey book motor now...",
            'sabibuy_logistics_booked': "Motor don book for {code}!\nTruck dey come.",
            'sabibuy_profit_paid': "PROFIT DON PAY!\n{amount} don enter your wallet!",
            'sabibuy_delivery_complete': "Delivery don complete!\n{quantity} {unit}s dey ready for {location}",
            'sabibuy_progress_update': "Your SabiBuy {code} don reach {progress}%!",
            'sabibuy_invalid_code': "SabiBuy code no correct. Check am try again.",
            'sabibuy_captain_welcome': "Welcome SabiBuyer Captain!\nGold Badge don open!\nUnlimited SabiBuys don enable!",
        },
        
        'ig': {  # Igbo
            'welcome': "Nno na AgroLink! Ahịa Ọrụ Ugbo Nigeria.",
            'welcome_back': "Nnọọ, {name}!",
            'register_prompt': "Iji debanye aha, zaa: JOIN [aha] [ebe] [ihe ọkụkụ]",
            'registration_success': "E debanyela gị dị ka onye ọrụ ugbo! Iwu: LIST, PRICE, HELP",
            'already_registered': "E debanyela aha gị. Zipu HELP maka iwu.",
            
            'ussd_main_menu': "AgroLink\n1. Dee Ihe Ubi\n2. Lee Ọnụ Ahịa\n3. Ihe Ndepụta M\n4. Ego M\n5. Debanye Aha\n6. Ọrụ Njem\n7. Debanye Aha dị ka Onye Ọzụzụ\n8. Bụrụ Onye Nnọchite\n9. Ngalaba Onye Nnọchite",
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
            
            # Transport/Logistics
            'transport_menu': "ỌRỤ NJEM\n1. Ọrụ Ọhụrụ\n2. Debanye Aha dị ka Onye Ọkwọ Ụgbọ\n3. Ego M Kwụrụ\n4. Njem Na-arụ Ọrụ\n5. Ego M\n0. Laghachi",
            'new_transport_job': "Ọrụ #{job_id}: Buru {produce} si {from_location} gaa {to_location}. Ọnụ ọgụgụ: {weight}T. Ọnụ ahịa: {price}. Zaa: BID {job_id} [ego]",
            'bid_placed': "E tinyela ₦{amount} maka Ọrụ #{job_id}.",
            'bid_accepted': "A nabatara ₦{amount} maka Ọrụ #{job_id}! A tọhapụla 50%.",
            # Transport LITE Registration
            'register_transporter_first': "Biko debanye aha dị ka onye ọkwọ ụgbọ.\nKpọọ *712*55# > 6 > 2 ma ọ bụ zipu JOIN TRK [aha] [ebe] [ụdị]",
            'register_transporter_name': "Tinye aha gị ma ọ bụ aha ụlọ ọrụ:",
            'register_transporter_location': "Tinye ebe gị (steeti/obodo):",
            'register_transporter_vehicle': "Họrọ ụdị ụgbọ:\n1. Okada/Pickup\n2. Ụgbọ Ton 5-10\n3. Ụgbọ Ton 15-30\n4. Ụgbọ Oyi/Fridge",
            'register_transporter_success': "Daalụ {name}!\nE debanyela aha gị dị ka onye ọkwọ ụgbọ.\nID: {transporter_id}\nỊ ga-amalite inweta ọrụ ugbu a.\nZipu DOC iji mezue profaịlụ gị.",
            'already_transporter': "E debanyela aha gị dị ka onye ọkwọ ụgbọ.\nID: {transporter_id}",
            'transport_balance': "ID Onye Ọkwọ: {transporter_id}\nEgo: ₦{balance}",
            'doc_response': "Mezue profaịlụ gị iji nweta ọkwa dị elu na bonus oyi.\nGaa: agrolink.ng/transport/complete",
            
            # Buyer LITE Registration
            'register_buyer_first': "Biko debanye aha dị ka onye ọzụzụ.\nKpọọ *712*55# > 7 ma ọ bụ zipu JOIN BUYER [aha] [ebe]",
            'register_buyer_name': "Tinye aha gị ma ọ bụ aha azụmaahịa:",
            'register_buyer_location': "Tinye ebe gị (steeti/obodo):",
            'register_buyer_type': "Kedu ụdị onye ọzụzụ ị bụ?\n1. Onye Ọzụzụ Ntakịrị\n2. Onye Ahịa Ukwu\n3. Ụlọ Nri/Hotelu\n4. Onye Na-arụ Ọrụ Ugbo",
            'register_buyer_success': "Nno {name}!\nE debanyela aha gị dị ka onye ọzụzụ.\nỊ ga-anata ozi banyere ihe ọkụkụ.\nZipu PRICE iji lee ọnụ ahịa.",
            'already_buyer': "E debanyela aha gị dị ka onye ọzụzụ.",
            
            # Agent LITE Registration
            'register_agent_first': "Biko debanye aha dị ka onye nnọchite.\nKpọọ *712*55# > 8 ma ọ bụ zipu JOIN AGENT [aha] [ebe]",
            'register_agent_name': "Tinye aha gị zuru ezu:",
            'register_agent_location': "Tinye ebe/LGA gị:",
            'register_agent_referral': "Tinye koodu ntụnye ma ọ bụ koodu NYSC\n(Pịa 0 iji wụfee):",
            'register_agent_success': "Ị bụ ugbu a Onye Nnọchite AgroLink!\nID gị: {agent_id}\nỊ ga-enweta ₦200 airtime maka ndị ọrụ ugbo 10 ị debanyere.\nNkwado n'ime awa 24. Malite ugbu a!",
            'already_agent': "E debanyela aha gị dị ka onye nnọchite.\nID: {agent_id}",
            'agent_menu': "NGALABA ONYE NNỌCHITE ({agent_id})\nỌnọdụ: {status}\n1. Debanye Onye Ọrụ Ugbo\n2. Debanye Onye Ọzụzụ\n3. Ndị Ọrụ Ugbo M\n4. Ego M\n0. Laghachi",
            'agent_pending_approval': "Akaụntụ onye nnọchite gị na-eche nkwado.\nNkwado n'ime awa 24.",
            'agent_farmer_name': "Tinye aha onye ọrụ ugbo zuru ezu:",
            'agent_farmer_location': "Tinye ebe onye ọrụ ugbo:",
            'agent_farmer_crop': "Tinye ihe ọkụkụ onye ọrụ ugbo:",
            'agent_farmer_success': "E debanyere onye ọrụ ugbo {name}!\nNchịkọta ndị ọrụ ugbo: {total}",
            'agent_buyer_name': "Tinye aha onye ọzụzụ:",
            'agent_buyer_location': "Tinye ebe onye ọzụzụ:",
            'agent_buyer_success': "E debanyere onye ọzụzụ {name}!\nNchịkọta ndị ọzụzụ: {total}",
            'agent_no_farmers': "Ị debanyebeghị onye ọrụ ugbo ọ bụla.",
            'agent_farmers_list': "Ndị Ọrụ Ugbo Gị:\n{farmers}\n\nNchịkọta: {total}",
            'agent_earnings': "Ego Gị:\nNa-echere: ₦{pending}\nNchịkọta: ₦{total}\n\nNdị Ọrụ Ugbo: {farmers}\nNdị Ọzụzụ: {buyers}",
            'delivery_complete': "Nnyefe zuru ezu! A tọhapụla ₦{amount} ikpeazụ.",
            'cold_chain_bonus': "A gosipụtara oyi! A gbakwunyere ₦{amount}.",
            
            # SabiBuy - Igbo
            'sabibuy_menu': "SABIBUY\n10. Malite SabiBuy\n11. Sonye SabiBuy\n12. SabiBuy M\n13. Ego Uru\n0. Laghachi",
            'sabibuy_name': "SabiBuy",
            'sabibuyer_name': "Onye Sabi",
            'sabibuy_captain': "Onyeisi Sabi",
            'sabibuy_select_produce': "Họrọ ihe ubi ị ga-ere:\n{produce_list}\nTinye nọmba:",
            'sabibuy_set_price': "Ọnụ ahịa ugbo: ₦{farm_price}\nAtụ aro: ₦{suggested} (uru ₦{margin}/otu)\nTinye ọnụ ahịa gị:",
            'sabibuy_set_location': "Tinye LGA/Ahịa nnyefe:",
            'sabibuy_confirm': "KWADO SabiBuy:\n{produce} @ ₦{price}\nỌnụ ọgụgụ kacha nta: {min_qty} {unit}\nNnyefe: {location}\n1. Kwado\n2. Kagbuo",
            'sabibuy_created': "E mepụtara SabiBuy!\nKoodu: {code}\nZigara ndị gị!",
            'sabibuy_share_prompt': "Zigara {code} ndị gị!",
            'sabibuy_join_prompt': "Tinye koodu SabiBuy:",
            'sabibuy_join_quantity': "Koodu: {code}\n{produce} @ ₦{price}/{unit}\nTinye ole ị chọrọ:",
            'sabibuy_join_confirm': "Nnyocha: {quantity} {unit}\nNchịkọta: ₦{total}\n1. Kwụọ ego site na T2\n2. Kwụọ ego site na Paystack\n3. Kagbuo",
            'sabibuy_order_placed': "E nyere iwu!\n{quantity} {unit} maka ₦{total}\nKwụọ ugbu a.",
            'sabibuy_payment_confirmed': "A kwadoro ịkwụ ụgwọ maka {code}!\n{quantity} {unit} @ {amount}.",
            'sabibuy_order_received': "Nnyocha ọhụrụ maka {code}!\nỌganiru: {progress}%",
            'sabibuy_batch_closed': "A mechiri!\n{code}: E rere {quantity}!\nA na-ahazi ọgbọ ugbu a...",
            'sabibuy_logistics_booked': "A hazila ọgbọ maka {code}!\nỤgbọ ala na-abịa.",
            'sabibuy_profit_paid': "A KWỤRỤ URU!\n{amount} ezitela na akpa ego gị!",
            'sabibuy_delivery_complete': "Nnyefe zuru ezu!\n{quantity} {unit} dị njikere na {location}",
            'sabibuy_progress_update': "SabiBuy {code} gị ejupụtala {progress}%!",
            'sabibuy_invalid_code': "Koodu SabiBuy adịghị mma.",
            'sabibuy_captain_welcome': "Nno Onyeisi Sabi!\nBadge Ọlaedo emepela!",
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
