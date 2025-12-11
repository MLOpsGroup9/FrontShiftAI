"""
RAG service - company name normalization and filtering
"""

# Company name mapping for vector DB metadata
METADATA_TO_DB_COMPANY_MAP = {
    # Cleaning & Maintenance
    "maintenance afl cleaning services": "AFL Cleaning Services",
    "cleaning maintenance afl cleaning services": "AFL Cleaning Services",
    "cleaning&maintenance afl cleaning services": "AFL Cleaning Services",
    "afl cleaning services": "AFL Cleaning Services",
    
    "the clean space": "The Clean Space",
    "cleaning&maintenance the clean space": "The Clean Space",
    
    "prestige janitorial service": "Prestige Janitorial Service",
    "cleaning&maintenance prestige janitorial service": "Prestige Janitorial Service",
    
    # Healthcare
    "healthcare crouse medical practice": "Crouse Medical Practice",
    "crouse medical practice": "Crouse Medical Practice",
    "crouse medical": "Crouse Medical Practice",
    
    "healthcare services group": "Healthcare Services Group",
    "healthcare healthcare services group": "Healthcare Services Group",
    
    # Finance
    "finance old national bank": "Old National Bank",
    "old national bank": "Old National Bank",
    
    "finance home bank": "Home Bank",
    "home bank": "Home Bank",
    
    # Retail
    "retail lunds & byerlys": "Lunds & Byerlys",
    "lunds & byerlys": "Lunds & Byerlys",
    "retail lunds byerlys": "Lunds & Byerlys",
    "lunds byerlys": "Lunds & Byerlys",
    
    "holiday market": "Holiday Market",
    "retail holiday market": "Holiday Market",
    
    # Manufacturing
    "manufacturing end policies manufacturing": "End Policies Manufacturing",
    "end policies manufacturing": "End Policies Manufacturing",
    "end policies": "End Policies Manufacturing",
    
    "b&g foods": "B&G Foods",
    "manufacturing b&g foods": "B&G Foods",
    "b&g": "B&G Foods",
    
    # Construction
    "construction kinyon construction": "Kinyon Construction",
    "kinyon construction": "Kinyon Construction",
    "kinyon": "Kinyon Construction",
    
    "tnt construction": "TNT Construction",
    "construction tnt construction": "TNT Construction",
    "tnt": "TNT Construction",
    
    # Hospitality
    "hospitality alta peruvian lodge": "Alta Peruvian Lodge",
    "alta peruvian lodge": "Alta Peruvian Lodge",
    "alta peruvian": "Alta Peruvian Lodge",
    
    "western university hospitality services": "Western University Hospitality Services",
    "hospitality western university hospitality services": "Western University Hospitality Services",
    "western university": "Western University Hospitality Services",
    
    # Logistics
    "logistics o'neill logistics": "O'Neill Logistics",
    "o'neill logistics": "O'Neill Logistics",
    "oneill logistics": "O'Neill Logistics",
    "o'neill": "O'Neill Logistics",
    
    "buchheit logistics": "Buchheit Logistics",
    "logistics buchheit logistics": "Buchheit Logistics",
    "buchheit": "Buchheit Logistics",
    
    # Field Service
    "fieldservicetechnicians jacob heating and cooling": "Jacob Heating and Cooling",
    "jacob heating and cooling": "Jacob Heating and Cooling",
    "jacob heating & air conditioning": "Jacob Heating and Cooling",
    "jacob heating": "Jacob Heating and Cooling",
    "jacob": "Jacob Heating and Cooling",
    
    "cra staffing": "CRA Staffing",
    "fieldservicetechnicians cra staffing": "CRA Staffing",
    "cra": "CRA Staffing",
}

def normalize_metadata_company_name(metadata_company: str, user_company: str) -> bool:
    """
    Check if metadata company matches user's company
    Handles the mismatch between vector DB metadata and database company names
    
    Args:
        metadata_company: Company name from vector DB metadata
        user_company: Company name from user's database record
        
    Returns:
        bool: True if companies match
    """
    if not metadata_company or not user_company:
        return False
    
    # Normalize both for comparison
    meta_normalized = metadata_company.strip().lower()
    user_normalized = user_company.strip().lower()
    
    # Extract key identifying words from user's company
    user_key_words = set(user_normalized.split())
    
    # Remove common words that don't help identification
    stop_words = {'the', 'and', 'of', 'for', 'in', 'services', 'group', 'company', 'inc', 'llc', 'ltd'}
    user_key_words = user_key_words - stop_words
    
    # Extract key words from metadata company
    meta_key_words = set(meta_normalized.split())
    meta_key_words = meta_key_words - stop_words
    
    # Check if there's significant overlap in key words
    overlap = user_key_words & meta_key_words
    
    # Need at least 1 meaningful word match (or 2 for common words)
    if len(overlap) == 0:
        return False
    
    # Special case: If user company has unique identifying word(s), require exact match
    unique_identifiers = {
        'crouse': ['crouse'],
        'lunds': ['lunds'],
        'byerlys': ['byerlys'],
        'kinyon': ['kinyon'],
        'tnt': ['tnt'],
        'alta': ['alta'],
        'peruvian': ['peruvian'],
        'oneill': ['oneill', "o'neill"],
        'buchheit': ['buchheit'],
        'jacob': ['jacob'],
        'aflcleaning': ['afl'],
        'cleanspace': ['clean', 'space'],
        'prestige': ['prestige'],
        'endpolicies': ['end', 'policies'],
        'b&g': ['b&g', 'bg'],
        'oldnational': ['old', 'national'],
        'homebank': ['home', 'bank'],
        'holiday': ['holiday'],
        'western': ['western', 'university'],
        'cra': ['cra'],
    }
    
    # Check for unique identifier matches
    for key, identifiers in unique_identifiers.items():
        user_has_identifier = any(identifier in user_normalized for identifier in identifiers)
        meta_has_identifier = any(identifier in meta_normalized for identifier in identifiers)
        
        if user_has_identifier:
            # User company has this unique identifier, metadata must also have it
            if not meta_has_identifier:
                return False
            # Both have it - this is a match for this identifier
            # But continue checking to make sure there are no conflicting identifiers
    
    # Direct substring match (after passing unique identifier check)
    if user_normalized in meta_normalized or meta_normalized in user_normalized:
        return True
    
    # Check if metadata company maps to user's company via mapping dictionary
    if meta_normalized in METADATA_TO_DB_COMPANY_MAP:
        mapped_company = METADATA_TO_DB_COMPANY_MAP[meta_normalized]
        if mapped_company.lower() == user_normalized:
            return True
    
    # Check reverse - if user's company maps to metadata company
    for meta_key, db_value in METADATA_TO_DB_COMPANY_MAP.items():
        if db_value.lower() == user_normalized:
            if meta_key in meta_normalized or meta_normalized in meta_key:
                return True
    
    # If we have significant overlap (at least 2 key words match)
    if len(overlap) >= 2:
        return True
    
    return False