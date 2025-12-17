import csv
import json
import os
import time
from openai import OpenAI
from typing import Dict, List, Any, Optional
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define our contact taxonomy with normalized keys for the schema
TAXONOMY_MAP = {
    "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_IMPACT_LEADERS": "Strategic Business Prospects: Corporate Impact Leaders",
    "STRATEGIC_BUSINESS_PROSPECTS__FOUNDATION_EXECUTIVES": "Strategic Business Prospects: Foundation Executives",
    "STRATEGIC_BUSINESS_PROSPECTS__NONPROFIT_EXECUTIVES": "Strategic Business Prospects: Nonprofit Executives",
    "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_PARTNERS": "Strategic Business Prospects: Corporate Partners",
    
    "KNOWLEDGE_NETWORK__AI_TECH_INNOVATORS": "Knowledge & Industry Network: AI/Tech Innovators",
    "KNOWLEDGE_NETWORK__SOCIAL_IMPACT_PRACTITIONERS": "Knowledge & Industry Network: Social Impact Practitioners",
    "KNOWLEDGE_NETWORK__ENVIRONMENTAL_CHAMPIONS": "Knowledge & Industry Network: Environmental Champions",
    "KNOWLEDGE_NETWORK__THOUGHT_LEADERS": "Knowledge & Industry Network: Thought Leaders",
    "KNOWLEDGE_NETWORK__PHILANTHROPY_PROFESSIONALS": "Knowledge & Industry Network: Philanthropy Professionals",
    
    "NEWSLETTER_AUDIENCE__SOCIAL_IMPACT_PROFESSIONALS": "Newsletter Audience: Social Impact Professionals",
    "NEWSLETTER_AUDIENCE__DEI_PRACTITIONERS": "Newsletter Audience: DEI Practitioners",
    "NEWSLETTER_AUDIENCE__POTENTIAL_SUBSCRIBERS": "Newsletter Audience: Potential Subscribers",
    
    "SUPPORT_NETWORK__INVESTORS_FUNDERS": "Support Network: Investors/Funders",
    "SUPPORT_NETWORK__MENTORS_ADVISORS": "Support Network: Mentors/Advisors",
    "SUPPORT_NETWORK__CONNECTORS": "Support Network: Connectors",
    "SUPPORT_NETWORK__FORMER_COLLEAGUES": "Support Network: Former Colleagues",
    
    "PERSONAL_NETWORK__FRIENDS_FAMILY": "Personal Network: Friends/Family",
    "PERSONAL_NETWORK__OUTDOORITHM_COMMUNITY": "Personal Network: Outdoorithm Community",
    
    "LOW_PRIORITY__OUT_OF_SCOPE": "Low Priority: Out of Scope",
    "LOW_PRIORITY__WEAK_CONNECTION": "Low Priority: Weak Connection"
}

# Extract the enum values (keys) for the schema
FLAT_TAXONOMY = list(TAXONOMY_MAP.keys())

# Define the JSON schema for structured output
CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": FLAT_TAXONOMY,
            "description": "The single best-fit taxonomy label for this contact"
        }
    },
    "required": ["category"],
    "additionalProperties": False
}

def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client."""
    # Try different variations of the API key environment variable
    api_key = os.environ.get("OPENAI_APIKEY") or os.environ.get("OPENAI_API_KEY")
    
    # Print debug information
    print(f"Environment variables: {[k for k in os.environ.keys() if 'OPENAI' in k]}")
    
    # If API key not found in environment, try to read directly from .env file
    if not api_key:
        try:
            print("Attempting to read API key directly from .env file...")
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('OPENAI_APIKEY='):
                        api_key = line.strip().split('=', 1)[1].strip()
                        print("Found API key in .env file")
                        break
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables or .env file. Please set OPENAI_APIKEY.")
    
    # Remove any quotes that might be in the API key
    api_key = api_key.strip('\'"')
    
    return OpenAI(api_key=api_key)

def prepare_contact_for_classification(contact: Dict[str, str]) -> str:
    """Format contact data into a string for classification."""
    relevant_fields = [
        f"Name: {contact.get('First Name', '')} {contact.get('Last Name', '')}",
        f"Position: {contact.get('Position', '')}",
        f"Company: {contact.get('Company', '')}",
        f"Headline: {contact.get('Headline', '')}",
    ]
    
    # Add summary if it exists and isn't too long
    summary = contact.get('Summary', '')
    if summary and len(summary) > 0:
        # Truncate very long summaries
        if len(summary) > 500:
            summary = summary[:500] + "..."
        relevant_fields.append(f"Summary: {summary}")
    
    # Add experience if available
    experience = contact.get('Summary - Experience', '')
    if experience:
        # Truncate very long experience
        if len(experience) > 300:
            experience = experience[:300] + "..."
        relevant_fields.append(f"Experience: {experience}")
    
    # Include education
    education = []
    school = contact.get('School Name - Education', '')
    degree = contact.get('Degree - Education', '')
    field = contact.get('Field Of Study - Education', '')
    if school or degree or field:
        edu_str = f"Education: {school} {degree} {field}".strip()
        relevant_fields.append(edu_str)
    
    # Include volunteering if available
    volunteering = contact.get('Summary - Volunteering', '')
    volunteering_role = contact.get('Role - Volunteering', '')
    volunteering_company = contact.get('Company Name - Volunteering', '')
    if volunteering or volunteering_role or volunteering_company:
        vol_info = f"Volunteering: {volunteering_role} at {volunteering_company}".strip()
        relevant_fields.append(vol_info)
        if volunteering and len(volunteering) > 0:
            vol_summary = volunteering
            if len(vol_summary) > 200:
                vol_summary = vol_summary[:200] + "..."
            relevant_fields.append(f"Volunteering Summary: {vol_summary}")
    
    return "\n".join(relevant_fields)

def classify_contact(client: OpenAI, contact_data: str) -> str:
    """Use OpenAI with structured output to classify the contact based on the taxonomy."""
    
    # Format enum values for system prompt
    enum_values = "\n".join([f"- {key}" for key in FLAT_TAXONOMY])
    
    system_prompt = f"""You are an AI assistant categorizing professional contacts for True Steele's business.
True Steele focuses on:
• Fractional Chief Impact Officer & strategic advisory (social impact + ROI)
• Outdoorithm nonprofit for outdoor equity
• A social impact newsletter ("The Long Arc")
• Startup ideas (Kindora, Proximity AI Lab) in philanthropic tech

You must return valid JSON that matches the schema with exactly one property: "category".
The "category" value MUST be one of these exact enum values:

{enum_values}

No extra keys or explanations. Only pure JSON.
If multiple categories apply, choose the single best fit.
If you are unsure, choose LOW_PRIORITY__OUT_OF_SCOPE.
"""
    
    user_prompt = f"""Contact info:

{contact_data}

Return only valid JSON with a single property "category". The value for category must be one of the enum values specified.
Example: {{"category": "STRATEGIC_BUSINESS_PROSPECTS__CORPORATE_IMPACT_LEADERS"}}
"""
    
    try:
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={
                "type": "json_object"
            }
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        category_key = result.get("category")
        
        # Convert the enum key to the display format
        display_category = TAXONOMY_MAP.get(category_key)
        
        if not display_category:
            print(f"Warning: Unexpected enum or parsing error: {category_key}")
            return "Low Priority: Out of Scope"  # Default fallback
        
        return display_category
    
    except Exception as e:
        print(f"Error classifying contact: {e}")
        return "Low Priority: Out of Scope"  # Default fallback

def process_csv(
    input_file: str, 
    output_file: str, 
    client: OpenAI, 
    sample_size: Optional[int] = None,
    start_index: int = 0
) -> None:
    """Process the CSV file and add classifications."""
    
    # Read the input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
    
    # Determine which rows to process
    if sample_size:
        end_index = min(start_index + sample_size, len(all_rows))
        rows_to_process = all_rows[start_index:end_index]
    else:
        rows_to_process = all_rows[start_index:]
    
    # Prepare the output
    fieldnames = reader.fieldnames + ['Taxonomy Classification']
    
    # Check if the output file exists and has content
    file_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0
    
    # Open the output file in the appropriate mode
    with open(output_file, 'a' if file_exists else 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write the header if the file is new
        if not file_exists:
            writer.writeheader()
        
        # Process each contact
        for i, row in enumerate(rows_to_process):
            contact_data = prepare_contact_for_classification(row)
            classification = classify_contact(client, contact_data)
            
            # Add the classification to the row
            row['Taxonomy Classification'] = classification
            
            # Write the row to the output file
            writer.writerow(row)
            
            # Print progress
            print(f"Processed {i+1}/{len(rows_to_process)}: {row['First Name']} {row['Last Name']} -> {classification}")
            
            # Sleep to avoid rate limits
            time.sleep(0.5)
    
    print(f"Processed {len(rows_to_process)} contacts. Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Classify contacts using OpenAI")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file path")
    parser.add_argument("--sample", type=int, help="Number of contacts to process (for testing)")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV (for resuming)")
    
    args = parser.parse_args()
    
    client = create_openai_client()
    process_csv(args.input, args.output, client, args.sample, args.start)

if __name__ == "__main__":
    main() 