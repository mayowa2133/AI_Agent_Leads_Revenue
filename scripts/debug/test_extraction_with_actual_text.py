"""Test extraction with the actual text format we're seeing."""

import re

# This is the actual text we see in the address field
actual_text = """COMPANY INFORMATION


		Company Name:TX Septic Systems LLCLicense Type:On-Site Sewer Facility Installer


		 


	
	
		TYPE OF WORK


		Selected:YesType of Work being performed:On-site Sewage Facility (OSSF)


		 


	
	
		
		CASHIER PAYMENTS


		Credit Card Type:null"""

print("Testing with actual text format...")
print(f"Text length: {len(actual_text)}")
print(f"Contains 'Company Name': {'Company Name' in actual_text}")
print()

# Test the exact patterns we're using
patterns = [
    (r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*License\s+Type|License\s+Type|$)', "Pattern 1 (with License Type stop)"),
    (r'Company\s+Name\s*:\s*([^:\n]+)', "Pattern 2 (simple, stop at colon or newline)"),
]

for pattern, name in patterns:
    match = re.search(pattern, actual_text, re.IGNORECASE | re.DOTALL)
    if match:
        value = match.group(1).strip()
        value = ' '.join(value.split())
        value = re.sub(r'\s*License\s+Type.*$', '', value, flags=re.IGNORECASE)
        value = value.strip()
        print(f"{name}: Matched '{value}' (length: {len(value)})")
        
        # Check validation
        is_label = value.lower() in ['individual', 'person', 'n/a', 'none', 'tbd', 'company information']
        print(f"  Would be filtered as label: {is_label}")
        print(f"  Length check (2-100): {2 <= len(value) <= 100}")
    else:
        print(f"{name}: No match")
