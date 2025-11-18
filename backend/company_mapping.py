"""
Company domain mapping for authentication
"""

COMPANIES = [
    {
        "domain": "Healthcare",
        "company": "Crouse Medical Practice",
        "url": "https://crousemed.com/media/1449/cmp-employee-handbook.pdf",
        "email_domain": "crousemedical.com"
    },
    {
        "domain": "Healthcare",
        "company": "Healthcare Services Group",
        "url": "https://www.hcsgcorp.com/wp-content/uploads/2023/01/Employee-Handbook-Healthcare-Services-Group-January-2023.pdf",
        "email_domain": "healthcareservices.com"
    },
    {
        "domain": "Retail",
        "company": "Lunds & Byerlys",
        "url": "https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf",
        "email_domain": "lundsbyerlys.com"
    },
    {
        "domain": "Retail",
        "company": "Holiday Market",
        "url": "https://holiday-market.com/schedules/handbook.pdf",
        "email_domain": "holidaymarket.com"
    },
    {
        "domain": "Manufacturing",
        "company": "End Policies Manufacturing",
        "url": "https://endpolicies.com/wp-content/uploads/2021/08/employee-handbook-2021-updated-1.pdf",
        "email_domain": "endpolicies.com"
    },
    {
        "domain": "Manufacturing",
        "company": "B&G Foods",
        "url": "https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf",
        "email_domain": "bgfoods.com"
    },
    {
        "domain": "Construction",
        "company": "Kinyon Construction",
        "url": "https://www.kinyonconstruction.com/files/132869525.pdf",
        "email_domain": "kinyonconstruction.com"
    },
    {
        "domain": "Construction",
        "company": "TNT Construction",
        "url": "https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf",
        "email_domain": "tntconstruction.com"
    },
    {
        "domain": "Hospitality",
        "company": "Alta Peruvian Lodge",
        "url": "https://www.altaperuvian.com/wp-content/uploads/2017/01/APL-Empl-Manual-Revised-12-22-16-fixed.pdf",
        "email_domain": "altaperuvian.com"
    },
    {
        "domain": "Hospitality",
        "company": "Western University Hospitality Services",
        "url": "https://www.hospitalityservices.uwo.ca/staff/handbook.pdf",
        "email_domain": "westernhospitality.com"
    },
    {
        "domain": "Finance",
        "company": "Old National Bank",
        "url": "https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf",
        "email_domain": "oldnational.com"
    },
    {
        "domain": "Finance",
        "company": "Home Bank",
        "url": "https://cdn.firstbranchcms.com/kcms-doc/472/88717/2025-Home-Bank-Employee-Handbook.25.02.24.13.53.40.pdf",
        "email_domain": "homebank.com"
    },
    {
        "domain": "Cleaning&Maintenance",
        "company": "The Clean Space",
        "url": "https://thecleanspace.com/wp-content/uploads/2024/09/8.-Employee-Handbook-v4.8.pdf",
        "email_domain": "cleanspace.com"
    },
    {
        "domain": "Cleaning&Maintenance",
        "company": "AFL Cleaning Services",
        "url": "https://www.aflcleaningservices.com/resources/AFL_EmployeeHandbook_new.pdf",
        "email_domain": "aflcleaning.com"
    },
    {
        "domain": "Logistics",
        "company": "O'Neill Logistics",
        "url": "https://www.oneilllogistics.com/wp-content/uploads/2023/06/NJ-Warehouse-2022-Employee-Handbook.pdf",
        "email_domain": "oneilllogistics.com"
    },
    {
        "domain": "Logistics",
        "company": "Buchheit Logistics",
        "url": "https://driver.buchheitlogistics.com/wp-content/uploads/2021/06/Logistics-Team-Member-Handbook.pdf",
        "email_domain": "buchheitlogistics.com"
    },
    {
        "domain": "FieldServiceTechnicians",
        "company": "Jacob Heating and Cooling",
        "url": "https://www.jacobhac.com/wp-content/uploads/2021/01/Jacob-HAC-Employee-Handbook.pdf",
        "email_domain": "jacobhac.com"
    },
    {
        "domain": "FieldServiceTechnicians",
        "company": "CRA Staffing",
        "url": "https://www.crastaffing.com/wp-content/uploads/2020/01/2018-Field-Staff-Handbook-PDF.pdf",
        "email_domain": "crastaffing.com"
    },
    {
        "domain": "Cleaning&Maintenance",
        "company": "Prestige Janitorial Service",
        "url": "https://www.phoenixjanitorialservice.net/wp-content/uploads/2017/05/2018-Employee-Handbook.pdf",
        "email_domain": "prestigejanitorial.com"
    }
]

# Create reverse mapping: email_domain -> company
EMAIL_TO_COMPANY = {
    company["email_domain"]: company["company"] 
    for company in COMPANIES
}

# Create company -> email_domain mapping
COMPANY_TO_EMAIL = {
    company["company"]: company["email_domain"] 
    for company in COMPANIES
}

# Simple user database (in production, use a real database)
# Format: email -> password
USERS = {
    # Crouse Medical Practice
    "admin@crousemedical.com": "password123",
    "user@crousemedical.com": "password123",
    
    # Healthcare Services Group
    "admin@healthcareservices.com": "password123",
    
    # Add more users as needed...
}

def get_company_from_email(email: str) -> str:
    """Extract company name from email domain"""
    if "@" not in email:
        return None
    
    domain = email.split("@")[1].lower()
    return EMAIL_TO_COMPANY.get(domain)

def validate_credentials(email: str, password: str) -> tuple:
    """Validate user credentials and return (success, company_name)"""
    email = email.lower()
    
    # Check if user exists
    if email not in USERS:
        return False, None
    
    # Check password
    if USERS[email] != password:
        return False, None
    
    # Get company from email
    company = get_company_from_email(email)
    if not company:
        return False, None
    
    return True, company

def get_email_domain(company: str) -> str:
    """Get email domain for a company"""
    return COMPANY_TO_EMAIL.get(company)

def validate_email_domain(email: str) -> bool:
    """Check if email domain is registered"""
    if "@" not in email:
        return False
    domain = email.split("@")[1].lower()
    return domain in EMAIL_TO_COMPANY