from typing import Dict, List

# Complaint categories and their sub-issues
COMPLAINT_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "sewage_potholes_roads": {
        "name": "Sewage/Potholes/Roads",
        "sub_issues": [
            "Blocked Drainage",
            "Sewage Overflow",
            "Pothole on Road",
            "Road Damage",
            "Waterlogging",
            "Other"
        ],
        "solutions": {
            "Blocked Drainage": "1. Check if the blockage is near your property\n2. Try using a plunger or drain cleaner\n3. If severe, avoid using water in that area\n4. Our team will inspect within 24 hours",
            "Sewage Overflow": "1. Avoid contact with sewage water\n2. Keep children and pets away\n3. Do not flush toilets if possible\n4. Emergency team will be dispatched immediately",
            "Pothole on Road": "1. Mark the pothole if possible for safety\n2. Avoid that area while driving\n3. Report exact location\n4. Repair will be done within 48 hours",
            "Road Damage": "1. Note the extent of damage\n2. Take photos for reference\n3. Avoid the damaged area\n4. Repair work will begin within 3 days",
            "Waterlogging": "1. Clear nearby drains if safe\n2. Avoid walking through waterlogged areas\n3. Check for electrical hazards\n4. Drainage team will clear within 12 hours"
        }
    },
    "garbage_cleanliness": {
        "name": "Garbage/Cleanliness",
        "sub_issues": [
            "Garbage Not Collected",
            "Dumpster Overflow",
            "Stray Animals",
            "Littering in Public Areas",
            "Dirty Streets",
            "Other"
        ],
        "solutions": {
            "Garbage Not Collected": "1. Ensure garbage is placed in designated bins\n2. Check collection schedule\n3. Separate wet and dry waste\n4. Collection will be done within 24 hours",
            "Dumpster Overflow": "1. Do not add more garbage to full dumpster\n2. Use alternative collection point if available\n3. Report exact location\n4. Additional collection will be arranged within 12 hours",
            "Stray Animals": "1. Do not feed stray animals in public areas\n2. Keep food waste properly sealed\n3. Report location and number of animals\n4. Animal control team will handle within 48 hours",
            "Littering in Public Areas": "1. Use nearby dustbins\n2. Report frequent littering spots\n3. Take photos if possible\n4. Cleanup drive will be conducted",
            "Dirty Streets": "1. Avoid the area if possible\n2. Report exact location\n3. Note the type of waste\n4. Street cleaning will be done within 24 hours"
        }
    },
    "electricity_issues": {
        "name": "Electricity Issues",
        "sub_issues": [
            "Power Cut",
            "Voltage Fluctuation",
            "Street Light Not Working",
            "Electric Pole Damage",
            "Exposed Wires",
            "Other"
        ],
        "solutions": {
            "Power Cut": "1. Check if neighbors have power\n2. Check your circuit breaker\n3. Report exact location and time\n4. Power restoration team will respond within 2 hours",
            "Voltage Fluctuation": "1. Unplug sensitive appliances\n2. Check if issue is building-wide\n3. Report to building maintenance\n4. Electrical team will inspect within 6 hours",
            "Street Light Not Working": "1. Note the pole number if visible\n2. Report exact location\n3. Check if multiple lights are affected\n4. Repair will be done within 48 hours",
            "Electric Pole Damage": "1. Stay away from damaged pole\n2. Do not touch any wires\n3. Report exact location immediately\n4. Emergency team will respond within 1 hour",
            "Exposed Wires": "1. Do not approach exposed wires\n2. Keep children and pets away\n3. Report exact location immediately\n4. Emergency repair team will respond within 30 minutes"
        }
    }
}

def get_category_name(category_key: str) -> str:
    """Get display name for category"""
    return COMPLAINT_TEMPLATES.get(category_key, {}).get("name", category_key)

def get_sub_issues(category_key: str) -> List[str]:
    """Get sub-issues for a category"""
    return COMPLAINT_TEMPLATES.get(category_key, {}).get("sub_issues", [])

def get_solution(sub_issue: str, category_key: str) -> str:
    """Get solution for a sub-issue"""
    return COMPLAINT_TEMPLATES.get(category_key, {}).get("solutions", {}).get(sub_issue, "Our team will look into this issue and get back to you.")

def is_other_option(sub_issue: str) -> bool:
    """Check if sub-issue is 'Other'"""
    return sub_issue.lower() == "other"
