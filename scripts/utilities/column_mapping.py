"""
Column mapping for Bay Area Philanthropy Leads CSV to match our expected format.
"""

# Map from source CSV columns to our expected format
COLUMN_MAPPING = {
    'firstName': 'First Name',
    'lastName': 'Last Name',
    'email': 'Email',
    'url': 'LinkedIn URL',
    'Title': 'Position',
    'Org': 'Company',
    'Connections': 'Connections',
    'Num Followers': 'Num Followers',
    'Headline': 'Headline',
    'Summary': 'Summary',
    'Company - Experience': 'Company - Experience',
    'Summary - Experience': 'Summary - Experience',
    'End Date - Experience': 'End Date - Experience',
    'Company Domain - Experience': 'Company Domain - Experience',
    'Degree - Education': 'Degree - Education',
    'End Date - Education': 'End Date - Education',
    'Start Date - Education': 'Start Date - Education',
    'Activities - Education': 'Activities - Education',
    'School Name - Education': 'School Name - Education',
    'Field Of Study - Education': 'Field Of Study - Education',
    'Country': 'Country',
    'Location Name': 'Location Name',
    'Title - Awards': 'Title - Awards',
    'Summary - Awards': 'Summary - Awards',
    'Company Name - Awards': 'Company Name - Awards',
    'Title - Projects': 'Title - Projects',
    'Summary - Projects': 'Summary - Projects',
    'End Date - Projects': 'End Date - Projects',
    'Start Date - Projects': 'Start Date - Projects',
    'Summary - Volunteering': 'Summary - Volunteering',
    'Role - Volunteering': 'Role - Volunteering',
    'Company Name - Volunteering': 'Company Name - Volunteering',
    'Company Domain - Volunteering': 'Company Domain - Volunteering',
    'Title - Publications': 'Title - Publications',
    'Summary - Publications': 'Summary - Publications',
    'Publisher - Publications': 'Publisher - Publications',
    'Url - Publications': 'Url - Publications',
    # Add any other relevant mappings here
}

def convert_row(row):
    """Convert a row from the Bay Area Philanthropy Leads CSV to our expected format."""
    converted_row = {}
    for source_col, target_col in COLUMN_MAPPING.items():
        if source_col in row:
            converted_row[target_col] = row[source_col]
    return converted_row 