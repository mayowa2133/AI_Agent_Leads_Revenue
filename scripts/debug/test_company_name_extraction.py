"""Test company name extraction from the exact pattern we see."""

import re

# Simulate the text we're seeing
test_text = """COMPANY INFORMATION


		Company Name:TX Septic Systems LLCLicense Type:On-Site Sewer Facility Installer


		 


	
	
		TYPE OF WORK


		Selected:YesType of Work being performed:On-site Sewage Facility (OSSF)"""

print("Testing extraction patterns...")
print(f"Original text:\n{test_text}\n")

# Pattern 1: Simple "Company Name:Value" (no space)
pattern1 = r'Company\s+Name\s*:\s*([^:\n]+?)(?:\s*(?:License\s+Type|Type\s+of\s+Work|Address|Location|$|\n))'
match1 = re.search(pattern1, test_text, re.IGNORECASE | re.DOTALL)
if match1:
    print(f"Pattern 1 matched: '{match1.group(1).strip()}'")
else:
    print("Pattern 1 did not match")

# Pattern 2: More flexible - stop at "License Type" or end
pattern2 = r'Company\s+Name\s*:\s*([^:]+?)(?:License\s+Type|$)'
match2 = re.search(pattern2, test_text, re.IGNORECASE)
if match2:
    print(f"Pattern 2 matched: '{match2.group(1).strip()}'")
else:
    print("Pattern 2 did not match")

# Pattern 3: Very simple - just get everything after "Company Name:" until next colon or newline
pattern3 = r'Company\s+Name\s*:\s*([^:\n]+)'
match3 = re.search(pattern3, test_text, re.IGNORECASE)
if match3:
    value = match3.group(1).strip()
    # Clean up - remove "License Type" if it's in there
    value = re.sub(r'License\s+Type.*$', '', value, flags=re.IGNORECASE)
    value = value.strip()
    print(f"Pattern 3 matched: '{value}'")
else:
    print("Pattern 3 did not match")

# Pattern 4: Handle the case where there's no space: "Company Name:TX Septic Systems LLC"
pattern4 = r'Company\s+Name\s*:\s*([A-Z][^:\n]+?)(?:\s*License\s+Type|$)'
match4 = re.search(pattern4, test_text, re.IGNORECASE)
if match4:
    value = match4.group(1).strip()
    print(f"Pattern 4 matched: '{value}'")
else:
    print("Pattern 4 did not match")
