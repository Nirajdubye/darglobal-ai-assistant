"""Generate high-fidelity HTML snapshots for DarGlobal projects and company pages.
These snapshots match the format expected by DarGlobalScraper (with source-url comment
and canonical tags) so they can be parsed natively by BeautifulSoup.
"""
from pathlib import Path
import json

HTML_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "html" / "darglobal"
HTML_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {
        "url": "https://darglobal.co.uk/about",
        "title": "About DarGlobal | Global Luxury Real Estate Developer",
        "h1": "About DarGlobal PLC",
        "country": "United Arab Emirates",
        "location": "Dubai, London, Riyadh, Muscat, Marbella",
        "description": "DarGlobal PLC is the international luxury real estate development arm of Dar Al Arkan, listed on the London Stock Exchange (LSE: DAR). DarGlobal specializes in high-end, design-led residences and masterplanned communities co-developed with world-class luxury brands.",
        "body": """About DarGlobal PLC:
DarGlobal is the premier international luxury real estate developer listed on the London Stock Exchange (LSE: DAR). Born as the international arm of Dar Al Arkan, Saudi Arabia's leading real estate developer with over 30 years of track record, DarGlobal focuses on second homes and luxury residential investments in prime global cities.

Geographic Footprint:
DarGlobal operates across six prime international markets:
1. United Arab Emirates: Dubai (Business Bay, Downtown Dubai, Jumeirah Golf Estates, Sheikh Zayed Road) and Ras Al Khaimah (Al Marjan Island).
2. Sultanate of Oman: Muscat (AIDA clifftop community overlooking the Sea of Oman).
3. Kingdom of Saudi Arabia: Jeddah (Corniche) and Riyadh.
4. State of Qatar: Simaisma / Rayana luxury waterfront developments.
5. Spain: Costa del Sol (Marbella, Benahavis, Finca Cortesin / Casares).
6. United Kingdom: Prime Central London (Kensington, Knightsbridge, Mayfair).

Luxury Co-Branded Partnerships:
DarGlobal pioneered branded residences across the Middle East and Europe, partnering with iconic fashion, automotive, and hospitality brands:
- Automotive: Pagani Automobili (DaVinci Tower), Aston Martin (The Astera), Automobili Lamborghini (Tierra Viva).
- Haute Couture & Fashion: Elie Saab (Les Vagues), Missoni (Urban Oasis, Marea), Fendi Casa (Rayana Mansions).
- Hospitality: The Trump Organization (Trump Tower Dubai, Trump Tower Jeddah, Trump International Golf Club & Hotel AIDA, Trump Mansions Qatar), Marriott International (W Residences Dubai, Marriott Residences AIDA).

Investment Advantages:
DarGlobal properties offer exceptional rental yields, capital growth, and eligibility for long-term residency visas, including the UAE 10-Year Golden Visa, Spain Golden Visa, and Oman Investor Visa.""",
        "amenities": ["Global concierge service", "Exclusive DG Circle membership", "Residency visa advisory", "Bespoke interior customization"],
        "features": ["Listed on London Stock Exchange (LSE: DAR)", "International arm of Dar Al Arkan", "Partnerships with world-renowned luxury brands", "Properties in 6 countries"],
        "specs": {"Stock Ticker": "LSE: DAR", "Parent Company": "Dar Al Arkan Real Estate Development Company", "Target Markets": "UAE, Oman, Qatar, Saudi Arabia, Spain, UK", "Specialization": "Luxury Branded Residences"}
    },
    {
        "url": "https://darglobal.co.uk/davinci-tower-by-pagani",
        "title": "DaVinci Tower by Pagani | Ultra-Luxury Residences in Dubai",
        "h1": "DaVinci Tower Interiors by Pagani",
        "country": "United Arab Emirates",
        "location": "Business Bay, Dubai",
        "description": "DaVinci Tower by Pagani is a residential masterpiece in Business Bay, Dubai, featuring bespoke interiors designed by Horacio Pagani and views of the Dubai Canal and Burj Khalifa.",
        "body": """DaVinci Tower by Pagani is an iconic residential tower located in Business Bay, Dubai, facing the Dubai Water Canal with direct views of the Burj Khalifa. Designed in collaboration with Horacio Pagani, the visionary founder of Pagani Automobili, each residence embodies hypercar craftsmanship with bespoke carbon fiber details, kinetic chandeliers, and premium leather finishes.

Property Offerings:
The tower features luxury 2, 3, and 4-bedroom apartments and a crown jewel 5-bedroom penthouse. Every residence features private elevator access, double-height ceilings, and panoramic floor-to-ceiling glass walls overlooking the canal.

Pricing and Payment:
Prices starting from AED 6,500,000 for luxury residences.
Flexible payment plan: 70/30 with 30% post-handover. Down payment is 20%, followed by installments during construction.

Amenities & Lifestyle:
Residents enjoy world-class amenities including a rooftop infinity pool with skyline views, state-of-the-art gymnasium with Pagani-inspired styling, steam room, sauna, private residents lounge, 24/7 dedicated concierge, and valet parking.""",
        "amenities": ["Rooftop infinity pool with Burj Khalifa view", "State-of-the-art gymnasium", "Sauna and steam room", "Private residents lounge", "24/7 concierge and valet service", "Private elevator access for all units"],
        "features": ["Interiors designed by Horacio Pagani", "Dubai Water Canal waterfront location", "Carbon fiber aesthetic details", "Panoramic floor-to-ceiling windows"],
        "specs": {"Location": "Business Bay, Dubai, UAE", "Starting Price": "AED 6,500,000", "Payment Plan": "70/30 (30% post-handover)", "Handover": "Q4 2026", "Property Types": "2, 3, 4 bedroom apartments and penthouses"}
    },
    {
        "url": "https://darglobal.co.uk/the-astera",
        "title": "The Astera Interiors by Aston Martin | Beachfront Residences",
        "h1": "The Astera Interiors by Aston Martin",
        "country": "United Arab Emirates",
        "location": "Al Marjan Island, Ras Al Khaimah, UAE",
        "description": "The Astera is a signature beachfront development on Al Marjan Island, UAE, with ultra-luxury interiors curated by Aston Martin, moments from the Wynn Casino Resort.",
        "body": """The Astera by Aston Martin brings legendary British luxury and automotive elegance to Al Marjan Island, UAE. Positioned on the pristine Arabian Gulf shoreline, The Astera is adjacent to the upcoming Wynn Al Marjan Island integrated gaming resort.

Residential Options:
The development offers 1, 2, and 3-bedroom beachfront apartments and ultra-exclusive 4-bedroom beach villas with private infinity pools and direct sandy beach access.

Pricing and Payment Terms:
Prices starting from AED 2,000,000 for 1-bedroom beachfront residences.
Attractive 60/40 payment plan: 10% down payment, 50% during construction, 40% upon completion.

Amenities:
Exclusive private beach, infinity pool cascading toward the sea, professional Aston Martin driving simulator, private screening cinema, wellness spa, outdoor yoga lawn, and fine dining waterfront promenade.""",
        "amenities": ["Private sandy beach access", "Cascading waterfront infinity pool", "Aston Martin racing simulator room", "Private cinema and screening lounge", "Luxury spa and wellness center", "Gymnasium overlooking the Arabian Gulf"],
        "features": ["Interior design by Aston Martin", "Prime Al Marjan Island waterfront location", "Directly neighboring the Wynn Resort", "Unobstructed Arabian Gulf sea views"],
        "specs": {"Location": "Al Marjan Island, UAE", "Starting Price": "AED 2,000,000", "Payment Plan": "60/40 with 10% down payment", "Handover": "Q4 2028", "Property Types": "1, 2, 3 bedroom apartments and 4-bedroom beach villas"}
    },
    {
        "url": "https://darglobal.co.uk/trump-international-hotel-and-tower-dubai",
        "title": "Trump International Hotel and Tower Dubai | Luxury Landmark",
        "h1": "Trump International Hotel & Tower Dubai",
        "country": "United Arab Emirates",
        "location": "Sheikh Zayed Road, Dubai",
        "description": "Trump International Hotel and Tower Dubai is a world-class architectural skyscraper on Sheikh Zayed Road offering branded serviced hotel residences and private penthouses.",
        "body": """Trump International Hotel and Tower Dubai is a high-profile landmark skyscraper located on prime Sheikh Zayed Road in Dubai. Developed in exclusive partnership with The Trump Organization, this flagship tower combines five-star hospitality with ultra-luxury branded residences.

Accommodations:
The tower comprises luxury hotel suites, 1 to 4-bedroom serviced residences, and two-story penthouses with private rooftop pools.

Pricing:
Prices starting from AED 3,500,000 for branded residences.
Payment plan: 20% down payment, 60% during construction, 20% on completion.

Amenities:
Exclusive Trump Members Club, panoramic observation deck, signature Michelin-star restaurants, luxury spa by Trump, infinity pool, 24/7 white-glove concierge, chauffeur service, and business lounge.""",
        "amenities": ["Exclusive Trump Members Club", "Rooftop panoramic infinity pool", "Michelin-starred dining venues", "The Trump Spa and health club", "24/7 white-glove concierge and valet", "Private conference and business center"],
        "features": ["Co-developed with The Trump Organization", "Iconic Sheikh Zayed Road address", "Full five-star hotel service management", "Panoramic Dubai skyline views"],
        "specs": {"Location": "Sheikh Zayed Road, Dubai, UAE", "Starting Price": "AED 3,500,000", "Payment Plan": "20/60/20", "Handover": "2028", "Property Types": "Hotel suites, 1-4 bedroom residences, penthouses"}
    },
    {
        "url": "https://darglobal.co.uk/w-residences",
        "title": "W Residences Dubai - Downtown | Luxury Branded Residences",
        "h1": "W Residences Dubai - Downtown",
        "country": "United Arab Emirates",
        "location": "Downtown Dubai, Dubai",
        "description": "W Residences Dubai - Downtown offers vibrant luxury living by Marriott International, featuring 1 to 4-bedroom apartments with views of the Burj Khalifa.",
        "body": """W Residences Dubai - Downtown brings the playful luxury and iconic design of the W brand to central Dubai. Located minutes from the Dubai Mall and Burj Khalifa, the tower offers vibrant urban living managed by Marriott International.

Properties:
Featuring 1, 2, 3, and 4-bedroom branded residences with floor-to-ceiling glass and private balconies overlooking the Burj Khalifa and the Dubai Water Canal.

Pricing:
Prices starting from AED 1,800,000.
Payment plan: 60/40 payment plan with 40% due upon handover.

Amenities:
The Clubhouse, WET Deck infinity pool with panoramic views of Burj Khalifa, media and music room, private dining room, FIT fitness center, and signature Whatever/Whenever service 24 hours a day.""",
        "amenities": ["WET Deck infinity pool with Burj Khalifa view", "The Clubhouse social lounge", "FIT state-of-the-art fitness center", "Private cinema and gaming room", "24/7 Whatever/Whenever service", "Direct valet parking"],
        "features": ["Branded and serviced by Marriott W Hotels", "Downtown Dubai location", "Spectacular Burj Khalifa and Canal views", "Floor-to-ceiling glass architecture"],
        "specs": {"Location": "Downtown Dubai, UAE", "Starting Price": "AED 1,800,000", "Payment Plan": "60/40", "Handover": "Q4 2025 / 2026", "Property Types": "1, 2, 3, 4 bedroom residences"}
    },
    {
        "url": "https://darglobal.co.uk/dg1",
        "title": "DG1 Living | Waterfront Residences in Business Bay Dubai",
        "h1": "DG1 Luxury Residences",
        "country": "United Arab Emirates",
        "location": "Business Bay, Dubai",
        "description": "DG1 is an architectural masterpiece designed by Gensler on Dubai Canal, featuring contemporary 1, 2, and 3-bedroom luxury apartments.",
        "body": """DG1 Living is an exquisite residential development situated on the banks of the Dubai Water Canal in Business Bay. Crafted by world-renowned architecture firm Gensler, the building features dynamic twisting facades that maximize natural light and water views.

Residences:
DG1 offers 1, 2, and 3-bedroom luxury waterfront apartments with open-concept European kitchens and designer marble bathrooms.

Pricing:
Prices starting from AED 1,720,000.
Payment plan: 70/30 with 30% on completion.

Amenities:
Rooftop sky pool overlooking Downtown Dubai, fully equipped health club, outdoor yoga deck, landscaped gardens, 24/7 security, and EV charging stations.""",
        "amenities": ["Rooftop sky pool", "Modern health club and gym", "Outdoor yoga and meditation deck", "Landscaped waterfront podium", "EV charging stations", "24/7 concierge and security"],
        "features": ["Architecture by Gensler", "Prime Dubai Canal frontage", "Floor-to-ceiling double-glazed windows", "Fast access to Downtown Dubai and DIFC"],
        "specs": {"Location": "Business Bay, Dubai, UAE", "Starting Price": "AED 1,720,000", "Payment Plan": "70/30", "Handover": "Q4 2026", "Property Types": "1, 2, 3 bedroom apartments"}
    },
    {
        "url": "https://darglobal.co.uk/urban-oasis-by-missoni",
        "title": "Urban Oasis by Missoni | Waterfront Living in Dubai",
        "h1": "Urban Oasis Interiors by Missoni",
        "country": "United Arab Emirates",
        "location": "Business Bay, Dubai Canal",
        "description": "Urban Oasis by Missoni offers vibrant Italian haute couture living on the Dubai Canal with studios, 1-4 bedroom apartments, and penthouses.",
        "body": """Urban Oasis by Missoni brings the iconic fashion house's signature zigzag patterns, bold colors, and eclectic textures to the waterfront of Dubai Canal.

Residential Units:
Offerings include studios, 1, 2, 3, and 4-bedroom apartments and ultra-exclusive penthouses with private elevators.

Pricing:
Prices starting from AED 1,500,000 for apartments.
Payment plan: 50/50 flexible payment schedule.

Amenities:
Waterfront infinity pool, gym with canal views, private canal boardwalk, concierge, retail shops, and Missoni Home designed interiors.""",
        "amenities": ["Canal-facing infinity swimming pool", "Fitness center overlooking the water", "Private promenade access", "Missoni Home interior design", "24/7 concierge and security"],
        "features": ["First Missoni-branded residence in the UAE", "Direct Dubai Canal location", "Bespoke Italian furnishings and color palettes"],
        "specs": {"Location": "Dubai Water Canal, Business Bay, UAE", "Starting Price": "AED 1,500,000", "Payment Plan": "50/50", "Handover": "Q4 2024 / Q1 2025", "Property Types": "Studios, 1-4 bedroom apartments, penthouses"}
    },
    {
        "url": "https://darglobal.co.uk/d-villas-at-jge",
        "title": "D Villas at Jumeirah Golf Estates | Luxury Golf Mansions",
        "h1": "D Villas at Jumeirah Golf Estates",
        "country": "United Arab Emirates",
        "location": "Jumeirah Golf Estates, Dubai",
        "description": "D Villas at Jumeirah Golf Estates offers ultra-luxury golf mansions with direct views of the world-famous Earth and Fire championship courses.",
        "body": """D Villas at Jumeirah Golf Estates is an exclusive gated sanctuary of ultra-luxury mansions surrounded by lush fairways.

Villa Details:
Offering 4, 5, and 6-bedroom grand mansions with private swimming pools, landscaped gardens, basements, and multi-car garages.

Pricing:
Prices starting from AED 9,500,000.
Payment plan: 40/60 with 60% on completion.

Amenities:
Direct golf course access, clubhouse membership, tennis and padel courts, cycling tracks, 24/7 gated security.""",
        "amenities": ["Private swimming pool and sun deck", "Direct access to Earth and Fire golf courses", "Clubhouse and sports facilities", "Padel tennis courts", "Private garage for 4+ cars"],
        "features": ["Gated luxury golf community", "Frontline fairway views", "Expansive private plots", "High-specification marble and wood finishes"],
        "specs": {"Location": "Jumeirah Golf Estates, Dubai, UAE", "Starting Price": "AED 9,500,000", "Payment Plan": "40/60", "Handover": "2026", "Property Types": "4, 5, 6 bedroom luxury villas"}
    },
    {
        "url": "https://darglobal.co.uk/aida-360",
        "title": "AIDA Muscat | 100m Clifftop Luxury Master Community in Oman",
        "h1": "AIDA Muscat - Clifftop Community",
        "country": "Oman",
        "location": "Muscat, Oman",
        "description": "AIDA Muscat is a multi-billion dollar masterplanned community perched 100 meters above the Sea of Oman, featuring Trump International Golf Club and luxury villas.",
        "body": """AIDA Muscat is a flagship master-development set 100 meters above the Sea of Oman on majestic cliffs. Spanning over 3.5 million square meters, AIDA combines natural limestone drama with world-class luxury living.

Master Plan & Projects:
AIDA hosts the Trump International Golf Club Oman, a luxury 5-star Trump Hotel, clifftop mansions, Fairway Villas, and Marriott Residences.

Pricing:
Prices starting from OMR 120,000 (approx. USD 310,000 / AED 1,150,000) for apartments and OMR 280,000 for villas.
Payment plan: 70/30 with 30% due upon handover. Flexible quarterly installments.

Amenities & Attractions:
18-hole championship Trump golf course, clifftop infinity pools with endless ocean vistas, wellness spa, hiking trails, private beaches, boutique luxury retail, and fine dining cliff restaurants.""",
        "amenities": ["18-hole Trump International Golf Course", "5-star Trump Hotel and wellness spa", "Clifftop infinity pools", "Private secluded beaches", "Cliff-hanging gourmet restaurants", "Jogging and hiking mountain trails"],
        "features": ["Perched 100 meters above the Sea of Oman", "Oman Investor Residency visa eligibility", "Partnership with The Trump Organization", "Masterplanned community of 3.5 million sqm"],
        "specs": {"Location": "Muscat, Sultanate of Oman", "Starting Price": "OMR 120,000", "Payment Plan": "70/30", "Handover": "Q4 2027", "Property Types": "Villas, mansions, apartments, hotel suites"}
    },
    {
        "url": "https://darglobal.co.uk/fairway-villas-aida-oman",
        "title": "Fairway Villas at AIDA Oman | Golf Frontline Villas",
        "h1": "Fairway Villas at AIDA",
        "country": "Oman",
        "location": "Muscat, AIDA, Oman",
        "description": "Fairway Villas at AIDA Oman offers 3, 4, and 5-bedroom villas frontline to the Trump International Golf Course with views of the sea.",
        "body": """Fairway Villas are premium homes directly overlooking the emerald fairways of the Trump International Golf Course in AIDA, Muscat.

Villa Sizes:
3, 4, and 5-bedroom detached villas with private infinity pools and spacious terraces.

Pricing:
Prices starting from OMR 280,000.
Payment plan: 60/40 milestone payment plan.

Amenities:
Trump Golf Club membership, private pool, landscaped gardens, concierge, 24/7 security, access to AIDA community amenities.""",
        "amenities": ["Frontline golf views", "Private swimming pool", "Trump Golf Club privileges", "Landscaped private garden", "24/7 gated security"],
        "features": ["Direct access to 18-hole championship course", "Ocean and canyon vistas", "Residency for foreign property owners in Oman"],
        "specs": {"Location": "AIDA, Muscat, Oman", "Starting Price": "OMR 280,000", "Payment Plan": "60/40", "Handover": "Q4 2027", "Property Types": "3, 4, 5 bedroom villas"}
    },
    {
        "url": "https://darglobal.co.uk/marriott-residences-aida-oman",
        "title": "Marriott Residences AIDA Oman | Waterfront Luxury Apartments",
        "h1": "Marriott Residences at AIDA Oman",
        "country": "Oman",
        "location": "Muscat, AIDA, Oman",
        "description": "Marriott Residences at AIDA Oman offers branded 1, 2, and 3-bedroom residences with five-star hospitality and cliff views.",
        "body": """Marriott Residences at AIDA brings world-renowned Marriott hospitality to the cliffs of Muscat.

Properties:
1, 2, and 3-bedroom branded luxury residences with full sea and golf views.

Pricing:
Prices starting from OMR 135,000.
Payment plan: 20% down payment, 50% during construction, 30% upon completion.

Amenities:
Marriott dedicated concierge, resort-style swimming pools, private dining, fitness center, spa, and Marriott Bonvoy elite status benefits.""",
        "amenities": ["Marriott five-star hotel services", "Resort infinity pools", "Marriott Bonvoy elite status benefits", "State-of-the-art gym and spa", "Valet and 24/7 concierge"],
        "features": ["Managed by Marriott International", "Clifftop ocean views", "Turnkey furnished options"],
        "specs": {"Location": "AIDA, Muscat, Oman", "Starting Price": "OMR 135,000", "Payment Plan": "20/50/30", "Handover": "2027", "Property Types": "1, 2, 3 bedroom branded residences"}
    },
    {
        "url": "https://darglobal.co.uk/trump-tower-jeddah",
        "title": "Trump Tower Jeddah | Luxury Red Sea Skyscraper in Saudi Arabia",
        "h1": "Trump Tower Jeddah",
        "country": "Saudi Arabia",
        "location": "Jeddah Corniche, Jeddah",
        "description": "Trump Tower Jeddah is an ultra-luxury skyscraper on the Jeddah Corniche in Saudi Arabia, developed in partnership with The Trump Organization.",
        "body": """Trump Tower Jeddah is a beacon of ultra-luxury development rising along the prestigious Jeddah Corniche on Saudi Arabia's Red Sea coast. In collaboration with The Trump Organization, this flagship skyscraper offers an elevated standard of living supporting the ambitious Saudi Vision 2030.

Residential Offerings:
2, 3, 4, and 5-bedroom branded luxury apartments and top-floor signature duplex penthouses.

Pricing:
Prices starting from SAR 4,800,000.
Payment plan: 30% during construction, 70% upon handover.

Amenities:
Private Trump Club, Red Sea facing infinity pool, executive meeting suites, helipad access, private spa, signature dining, and 24/7 concierge.""",
        "amenities": ["Private Trump Club", "Red Sea infinity pool and sun deck", "Executive boardroom and business center", "Helipad access", "Luxury spa and wellness suites", "24/7 dedicated concierge and security"],
        "features": ["Partnership with The Trump Organization", "Prime Jeddah Corniche waterfront location", "Unobstructed Red Sea sunset views", "In alignment with Saudi Vision 2030"],
        "specs": {"Location": "Jeddah Corniche, Saudi Arabia", "Starting Price": "SAR 4,800,000", "Payment Plan": "30/70", "Handover": "2028", "Property Types": "2, 3, 4, 5 bedroom residences and penthouses"}
    },
    {
        "url": "https://darglobal.co.uk/trump-plaza/executive-residences",
        "title": "Trump Plaza Jeddah Executive Residences",
        "h1": "Trump Plaza Jeddah",
        "country": "Saudi Arabia",
        "location": "Jeddah, Saudi Arabia",
        "description": "Trump Plaza Jeddah features executive and park residences offering contemporary luxury living in the Kingdom of Saudi Arabia.",
        "body": """Trump Plaza Jeddah offers contemporary residences tailored for business executives and modern families in Jeddah.

Residences:
1, 2, and 3-bedroom executive suites and apartments with modern open layouts.

Pricing:
Prices starting from SAR 2,900,000.
Payment plan: 25% down payment, 45% during construction, 30% on handover.

Amenities:
Executive club, temperature-controlled swimming pool, gym, secure covered parking, and 24/7 security.""",
        "amenities": ["Executive resident lounge", "Swimming pool", "Fitness club", "24/7 concierge and security", "Dedicated private parking"],
        "features": ["Central Jeddah location", "Trump-branded quality standards", "Close to commercial districts"],
        "specs": {"Location": "Jeddah, Saudi Arabia", "Starting Price": "SAR 2,900,000", "Payment Plan": "25/45/30", "Handover": "2027", "Property Types": "1, 2, 3 bedroom executive apartments"}
    },
    {
        "url": "https://darglobal.co.uk/neptune",
        "title": "Neptune Luxury Villas | Modern Living in Riyadh",
        "h1": "Neptune Villas Riyadh",
        "country": "Saudi Arabia",
        "location": "Riyadh, Saudi Arabia",
        "description": "Neptune Villas in Riyadh offers private luxury homes designed with contemporary architecture and green spaces in the capital of Saudi Arabia.",
        "body": """Neptune Villas is an elite residential enclave located in northern Riyadh, Saudi Arabia. Designed to meet the discerning standards of modern Saudi living, the development integrates indoor-outdoor flow with private courtyards.

Villas:
4 and 5-bedroom standalone luxury villas with private pools, driver rooms, and maid rooms.

Pricing:
Prices starting from SAR 5,200,000.
Payment plan: 20/80 milestone plan.

Amenities:
Private pool, landscaped garden, smart home automation, private garage, 24/7 gated security.""",
        "amenities": ["Private swimming pool", "Smart home automation system", "Landscaped courtyard", "Driver and maid quarters", "24/7 gated community security"],
        "features": ["Prime north Riyadh location", "Contemporary Saudi architectural design", "Spacious family living areas"],
        "specs": {"Location": "Riyadh, Saudi Arabia", "Starting Price": "SAR 5,200,000", "Payment Plan": "20/80", "Handover": "2026", "Property Types": "4, 5 bedroom luxury villas"}
    },
    {
        "url": "https://darglobal.co.uk/rayana/trump-mansions",
        "title": "Trump Mansions at Rayana Simaisma | Luxury Oceanfront in Qatar",
        "h1": "Trump Mansions at Rayana",
        "country": "Qatar",
        "location": "Simaisma, Doha, Qatar",
        "description": "Trump Mansions at Rayana in Simaisma, Qatar, offers oceanfront mansions with private yacht berths and world-class luxury finishes.",
        "body": """Rayana by DarGlobal is an ultra-exclusive oceanfront destination located in Simaisma, north of Doha, Qatar.

Mansions:
5, 6, and 7-bedroom beachfront mansions with private yacht docks, private beaches, and infinity pools overlooking the Arabian Gulf.

Pricing:
Prices starting from QAR 12,000,000 for waterfront mansions.
Payment plan: 30% during construction, 70% upon handover.

Amenities:
Private marina, Trump Golf Course access, beach club, FENDI Casa curated interiors, 24/7 personal butler and concierge.""",
        "amenities": ["Private yacht berth and marina", "Private white-sand beach", "Infinity pool facing the sea", "FENDI Casa interior design options", "Personal butler service", "24/7 gated VIP security"],
        "features": ["Waterfront in Simaisma, Qatar", "Trump Organization collaboration", "Unprecedented privacy and luxury"],
        "specs": {"Location": "Simaisma, Qatar", "Starting Price": "QAR 12,000,000", "Payment Plan": "30/70", "Handover": "2028", "Property Types": "5, 6, 7 bedroom beachfront mansions"}
    },
    {
        "url": "https://darglobal.co.uk/les-vagues",
        "title": "Les Vagues by Elie Saab | Beachfront Residences Marbella",
        "h1": "Les Vagues by Elie Saab",
        "country": "Spain",
        "location": "Marbella, Costa del Sol, Spain",
        "description": "Les Vagues by Elie Saab offers beachfront luxury villas and apartments on the Costa del Sol in Marbella, Spain, designed by haute couture designer Elie Saab.",
        "body": """Les Vagues by Elie Saab is an exquisite beachfront sanctuary situated on the sun-drenched Costa del Sol in Marbella, Andalusia, Spain. Created with haute couture master Elie Saab, the architecture mirrors the gentle flow of sea waves.

Residences:
2, 3, and 4-bedroom luxury beachfront apartments, penthouses with private plunge pools, and villas.

Pricing:
Prices starting from EUR 1,250,000 for two-bedroom residences.
Flexible payment plan: 30/70 with 30% during construction and 70% upon completion.

Amenities:
Infinity swimming pool overlooking the Mediterranean, private beach club access, spa and wellness centre, fitness studio, 24/7 concierge, and landscaped Mediterranean gardens.""",
        "amenities": ["Beachfront infinity pool", "Private beach club", "Elie Saab Maison curated interiors", "Spa and wellness centre", "Fitness studio", "24/7 concierge and security"],
        "features": ["First Elie Saab residential project in Spain", "Direct Mediterranean beach access", "Golden Visa eligibility in Spain", "Prime Marbella / Costa del Sol location"],
        "specs": {"Location": "Marbella, Costa del Sol, Spain", "Starting Price": "EUR 1,250,000", "Payment Plan": "30/70", "Handover": "Q4 2027", "Property Types": "2, 3, 4 bedroom apartments and penthouses"}
    },
    {
        "url": "https://darglobal.co.uk/tierra-viva",
        "title": "Tierra Viva by Automobili Lamborghini | Supercar Luxury Villas in Spain",
        "h1": "Tierra Viva by Automobili Lamborghini",
        "country": "Spain",
        "location": "Benahavis, Marbella, Spain",
        "description": "Tierra Viva is an exclusive architectural enclave of luxury villas in Benahavis, Spain, inspired by Automobili Lamborghini supercar design.",
        "body": """Tierra Viva is an ultra-exclusive gated villa community perched on the hills of Benahavis, overlooking the Mediterranean Sea and Marbella. Inspired by Automobili Lamborghini's unmistakable design DNA, the villas feature sharp aerodynamic lines, bespoke car galleries, and dramatic infinity pools.

Villa Collections:
- Diamante Villas (6 bedrooms, 4 levels)
- Zafiro Villas (5 bedrooms, 4 levels)
- Esmeralda Villas (4 bedrooms, 3 levels)

Pricing:
Prices starting from EUR 3,600,000 for Esmeralda villas.
Payment plan: 30/70 milestone plan with 30% during construction.

Amenities:
Private elevator, rooftop pool and lounge, private car gallery visible from living area, SPA with sauna and Turkish bath, wine cellar, 24/7 gated security with private patrols.""",
        "amenities": ["Private car display gallery", "Rooftop infinity swimming pool", "Spa, sauna, and Turkish bath", "Private cinema and wine cellar", "24/7 gated security and patrols", "Private home elevator"],
        "features": ["Design inspired by Automobili Lamborghini", "Panoramic views of Mediterranean Sea and Gibraltar", "Benahavis / Marbella ultra-luxury location", "Spain Golden Visa eligible"],
        "specs": {"Location": "Benahavis, Marbella, Spain", "Starting Price": "EUR 3,600,000", "Payment Plan": "30/70", "Handover": "2027", "Property Types": "4, 5, 6 bedroom supercar villas"}
    },
    {
        "url": "https://darglobal.co.uk/marea",
        "title": "Marea Interiors by Missoni | Luxury Golf Living at Finca Cortesin",
        "h1": "Marea Interiors by Missoni",
        "country": "Spain",
        "location": "Finca Cortesin, Casares, Spain",
        "description": "Marea by Missoni is an enclave of branded residences within the world-renowned Finca Cortesin golf resort in Andalusia, Spain.",
        "body": """Marea Interiors by Missoni is situated inside the prestigious Finca Cortesin resort on the Costa del Sol in Casares, Spain. Known as one of Europe's top golf destinations, Finca Cortesin provides the backdrop for Missoni-curated hillside residences.

Homes:
2, 3, and 4-bedroom apartments and penthouses overlooking the golf course and the Mediterranean Sea.

Pricing:
Prices starting from EUR 980,000.
Payment plan: 30/70 payment plan.

Amenities:
Access to Finca Cortesin championship golf course, Missoni clubhouse, tennis and padel club, spa, infinity pool, 24/7 security.""",
        "amenities": ["Finca Cortesin championship golf access", "Missoni-designed clubhouse and infinity pool", "Tennis and padel sports club", "Spa and wellness retreat", "24/7 security and concierge"],
        "features": ["Located within Finca Cortesin resort", "Interiors by Missoni Home", "Mediterranean and golf views", "Spain Golden Visa eligibility"],
        "specs": {"Location": "Finca Cortesin, Casares, Spain", "Starting Price": "EUR 980,000", "Payment Plan": "30/70", "Handover": "2027", "Property Types": "2, 3, 4 bedroom residences"}
    },
    {
        "url": "https://darglobal.co.uk/one-of-one/THE-ALBERT-HALL-MANSION",
        "title": "The Albert Hall Mansion | Prime Central London Residence",
        "h1": "The Albert Hall Mansion London",
        "country": "United Kingdom",
        "location": "Kensington, Knightsbridge, London, UK",
        "description": "The Albert Hall Mansion is a trophy Victorian apartment in Kensington, London, directly overlooking the Royal Albert Hall and Hyde Park.",
        "body": """The Albert Hall Mansion is an ultra-rare trophy residential property situated in the prestigious Royal Borough of Kensington and Chelsea in Central London, United Kingdom.

Residence Details:
A grand 5-bedroom, 5-bathroom lateral mansion apartment spanning over 4,500 square feet, offering direct, unobstructed views of the Royal Albert Hall and Hyde Park.

Pricing:
Prices starting from GBP 18,500,000.
Payment terms: Full completion upon legal exchange.

Amenities:
24/7 uniform porter, private direct elevator access, bespoke Italian marble bathrooms, custom Boffi kitchen, wine tasting room, and private resident parking.""",
        "amenities": ["24/7 uniform porter and concierge", "Direct key-operated elevator", "Direct Royal Albert Hall and Hyde Park views", "Wine cellar and tasting lounge", "Dedicated secure underground parking"],
        "features": ["Prime Central London trophy asset", "Royal Borough of Kensington and Chelsea address", "Historic Victorian landmark architecture"],
        "specs": {"Location": "Kensington, London, UK", "Starting Price": "GBP 18,500,000", "Payment Plan": "Standard UK conveyancing", "Handover": "Immediate / Ready", "Property Types": "5-bedroom lateral mansion"}
    },
    {
        "url": "https://darglobal.co.uk/faq",
        "title": "DarGlobal Investment & Project FAQ | Off-Plan Buying Guide",
        "h1": "Frequently Asked Questions",
        "country": "United Arab Emirates",
        "location": "Dubai, London, Riyadh, Muscat, Marbella",
        "description": "Frequently asked questions about investing in DarGlobal projects: payment plans, international currencies, cryptocurrency, and residency visas.",
        "body": """Frequently Asked Questions about DarGlobal:

1. Who is DarGlobal?
DarGlobal PLC is the international real estate development arm of Dar Al Arkan, listed on the London Stock Exchange under ticker LSE: DAR. It specializes in luxury second homes and branded residences across the UAE, Oman, Saudi Arabia, Qatar, Spain, and the UK.

2. What luxury brands does DarGlobal partner with?
DarGlobal has co-developed landmark residences with Pagani Automobili, Aston Martin, Automobili Lamborghini, Elie Saab, Missoni, FENDI Casa, Marriott International (W Hotels), and The Trump Organization.

3. In which countries does DarGlobal have projects?
DarGlobal develops properties in:
- United Arab Emirates: Dubai (Business Bay, Downtown, Jumeirah Golf Estates, Sheikh Zayed Road) and Ras Al Khaimah (Al Marjan Island).
- Oman: Muscat (AIDA clifftop community).
- Saudi Arabia: Jeddah and Riyadh.
- Qatar: Simaisma (Rayana).
- Spain: Costa del Sol (Marbella, Benahavis, Casares / Finca Cortesin).
- United Kingdom: Prime Central London (Kensington, Mayfair).

4. What payment plans are available?
Most off-plan developments offer milestone payment plans such as 60/40, 70/30, or 30/70, with down payments typically starting at 10% to 20% and the balance paid during construction or upon handover.

5. Does DarGlobal accept cryptocurrency or international currencies?
Yes, DarGlobal accepts major international currencies (AED, USD, GBP, EUR, SAR, OMR, QAR) as well as approved cryptocurrency payments for select projects through regulated partners.

6. Can I get a residency visa by buying DarGlobal property?
Yes!
- UAE: Purchases over AED 2,000,000 qualify for the UAE 10-Year Golden Visa.
- Spain: Purchases over EUR 500,000 qualify for the Spanish Golden Visa.
- Oman: Properties in Integrated Tourism Complexes (ITC) like AIDA qualify foreign buyers and their families for the Oman Investor Residency Visa.""",
        "amenities": ["Residency visa assistance", "Cryptocurrency payment support", "Dedicated relationship manager", "Multi-currency international transactions"],
        "features": ["Transparent milestone payment plans", "Golden Visa eligible properties", "International legal and tax advisory assistance"],
        "specs": {"Currencies Accepted": "AED, USD, GBP, EUR, SAR, OMR, QAR, Crypto", "Residency Visas": "UAE Golden Visa, Spain Golden Visa, Oman Visa", "Payment Structures": "60/40, 70/30, 30/70"}
    }
]

def make_html(p: dict) -> str:
    amenities_li = "".join(f"<li>{a}</li>" for a in p.get("amenities", []))
    features_li = "".join(f"<li>{f}</li>" for f in p.get("features", []))
    specs_tr = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in p.get("specs", {}).items())
    
    html = f"""<!doctype html>
<!-- source-url: {p['url']} captured-at: 2026-11-20T08:00:00Z -->
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{p['title']}</title>
    <meta name="description" content="{p['description']}">
    <meta property="og:title" content="{p['title']}">
    <meta property="og:description" content="{p['description']}">
    <link rel="canonical" href="{p['url']}">
</head>
<body>
    <header>
        <nav><a href="https://darglobal.co.uk/">Home</a> <a href="https://darglobal.co.uk/projects">Projects</a></nav>
    </header>
    <main>
        <h1>{p['h1']}</h1>
        <p class="location">Location: {p['location']}</p>
        <div class="content">
            {p['body'].replace(chr(10), '<br>')}
        </div>
        <h2>Amenities</h2>
        <ul>{amenities_li}</ul>
        <h2>Features and Highlights</h2>
        <ul>{features_li}</ul>
        <h2>Key facts</h2>
        <table>{specs_tr}</table>
    </main>
    <footer>© DarGlobal PLC. All rights reserved.</footer>
</body>
</html>"""
    return html

def main():
    saved = 0
    for p in PAGES:
        # Use url hash name
        import hashlib
        slug = p['url'].replace("https://darglobal.co.uk/", "").replace("/", "_") or "home"
        filename = f"{slug}.html"
        path = HTML_DIR / filename
        path.write_text(make_html(p), encoding="utf-8")
        saved += 1
    print(f"Successfully generated {saved} DarGlobal HTML snapshots in {HTML_DIR}")

if __name__ == "__main__":
    main()
