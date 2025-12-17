import os
import sys
import json
import time
import argparse
import csv
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import supabase
from openai import OpenAI
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Get environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
OPENAI_APIKEY = os.environ.get("OPENAI_APIKEY") or os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "o3-mini")

# Rate limiter settings
API_RATE_LIMIT = 0.5  # Time to wait between API calls (seconds)
BATCH_SIZE = 50       # Number of contacts to process at once

# Initialize OpenAI client
def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client."""
    if not OPENAI_APIKEY:
        raise ValueError("OpenAI API key not found in environment variables. Please set OPENAI_APIKEY.")
    return OpenAI(api_key=OPENAI_APIKEY)

# Initialize Supabase client
def create_supabase_client():
    """Create and return a Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase credentials not found in environment variables.")
    return supabase.create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def prepare_job_description(job_title: str, job_description: str) -> str:
    """Format the job details into a structured prompt for matching."""
    return f"""
Job Title: {job_title}
Job Description:
{job_description}
"""

# Define schemas for structured output
class ExperienceRequirement(BaseModel):
    area: str = Field(description="The area of experience required")
    years: Optional[int] = Field(None, description="Number of years of experience required, if specified")
    description: str = Field(description="Detailed description of the experience requirement")

class JobKeywords(BaseModel):
    skills: List[str] = Field(description="Required skills for the job")
    experience: List[ExperienceRequirement] = Field(description="Required experience areas and years")
    education: List[str] = Field(description="Required education qualifications")
    responsibilities: List[str] = Field(description="Key responsibilities of the role")
    industry_knowledge: List[str] = Field(description="Industry knowledge requirements")
    qualifications: List[str] = Field(description="Any specific qualifications mentioned")
    explanation: str = Field(description="Reasoning behind the extracted keywords")

class CandidateEvaluation(BaseModel):
    match_score: int = Field(description="Overall match score from 0-100 (where 100 is perfect match)")
    strengths: List[str] = Field(description="Key strengths that make the candidate a good fit")
    gaps: List[str] = Field(description="Key gaps in the candidate's profile relative to the requirements")
    recommend: bool = Field(description="Whether this candidate should be recommended for the position")
    explanation: str = Field(description="Brief rationale for the recommendation")

def extract_job_keywords(client: OpenAI, job_description: str) -> Dict[str, Any]:
    """Extract key skills, experience, and requirements from a job description using structured output."""
    system_prompt = """
    You are an AI assistant specialized in analyzing job descriptions. Extract the following information from the job description provided and return it in JSON format:
    
    1. Required skills
    2. Required experience (years and type)
    3. Required education
    4. Key responsibilities
    5. Industry knowledge
    6. Any specific qualifications mentioned
    
    Be specific and concise in your extraction. Focus on the most important requirements.
    """
    
    user_prompt = f"""
    Analyze this job description and extract the key requirements as JSON:
    
    {job_description}
    """
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"Error extracting job keywords: {e}")
        # Return empty structure if there's an error
        return {
            "skills": [],
            "experience": [],
            "education": [],
            "responsibilities": [],
            "industry_knowledge": [],
            "qualifications": [],
            "explanation": f"Error during extraction: {str(e)}"
        }

def fetch_candidate_batch(supabase_client, location=None, batch_size=BATCH_SIZE, offset=0):
    """Fetch a batch of candidates from Supabase for processing, with optional location filtering."""
    try:
        # Calculate range for pagination
        range_start = offset
        range_end = offset + batch_size - 1
        
        print(f"Fetching contacts from index {range_start} to {range_end}")
        
        # Build the query with rich profile data
        query = supabase_client.table('contacts').select(
            '''
            id, first_name, last_name, email, work_email, personal_email,
            position, company, headline, summary, location_name,
            summary_experience, company_experience, end_date_experience,
            company_domain_experience, school_name_education, degree_education,
            field_of_study_education, summary_volunteering, role_volunteering,
            company_name_volunteering, taxonomy_classification, linkedin_url
            '''
        )
        
        # Apply location filter if provided
        if location and location.lower() == "bay area":
            print(f"Filtering by Bay Area location")
            
            # Since we can't use OR conditions easily in Supabase, 
            # we'll just query for all contacts and filter locally.
            # This is less efficient but gives us more control
            result = query.range(range_start, range_end).execute()
            
            if not result.data:
                print(f"No contacts found at offset {offset}")
                return []
                
            # Define Bay Area cities within commuting distance of Oakland
            bay_area_cities = [
                "oakland", "alameda", "berkeley", "emeryville", 
                "san francisco", "daly city", "south san francisco",
                "richmond", "el cerrito", "albany", "san pablo",
                "walnut creek", "hayward", "san leandro", "castro valley",
                "orinda", "lafayette", "piedmont", "millbrae", "burlingame",
                "san mateo", "redwood city"
            ]
            
            # Also include general Bay Area terms
            bay_area_terms = [
                "bay area", "east bay", "sf bay", "silicon valley", 
                "northern california", "north bay", "peninsula"
            ]
            
            # Filter contacts locally
            filtered_data = []
            for contact in result.data:
                location_name = (contact.get('location_name') or '').lower()
                
                # Include if any city matches or any general term matches
                if any(city in location_name for city in bay_area_cities) or \
                   any(term in location_name for term in bay_area_terms):
                    filtered_data.append(contact)
            
            print(f"Retrieved {len(result.data)} contacts, filtered to {len(filtered_data)} Bay Area contacts")
            return filtered_data
            
        elif location:
            print(f"Filtering by location: {location}")
            query = query.ilike('location_name', f"%{location}%")
            
            # Apply range for pagination
            result = query.range(range_start, range_end).execute()
            
            if not result.data:
                print(f"No contacts found at offset {offset}")
                return []
            
            print(f"Retrieved {len(result.data)} contacts from database")
            return result.data
        else:
            # No location filter
            result = query.range(range_start, range_end).execute()
            
            if not result.data:
                print(f"No contacts found at offset {offset}")
                return []
            
            print(f"Retrieved {len(result.data)} contacts from database")
            return result.data
        
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        # Try to get more detailed error information
        error_details = str(e)
        print(f"Error details: {error_details}")
        
        # Try again with a delay if it might be a network issue
        if any(term in error_details.lower() for term in ["network", "timeout", "connection"]):
            print("Network issue detected, retrying after delay...")
            time.sleep(2)
            return fetch_candidate_batch(supabase_client, location, batch_size, offset)
        
        # If any other issue, try without location filter
        if location:
            print("Filter issue detected, retrying without location filter...")
            return fetch_candidate_batch(supabase_client, None, batch_size, offset)
        
        return []

def prepare_candidate_profile(contact: Dict[str, Any]) -> str:
    """Format contact data into a string for evaluation."""
    # Get best available email
    best_email = contact.get('work_email') or contact.get('email') or contact.get('personal_email') or ''
    
    profile = [
        f"Name: {contact.get('first_name', '')} {contact.get('last_name', '')}",
        f"Email: {best_email}",
        f"Current Position: {contact.get('position', '')}",
        f"Company: {contact.get('company', '')}",
        f"Location: {contact.get('location_name', '')}",
        f"LinkedIn: {contact.get('linkedin_url', '')}",
        f"Headline: {contact.get('headline', '')}",
    ]
    
    # Add summary if available
    if contact.get('summary'):
        summary = contact.get('summary', '')
        if len(summary) > 500:
            summary = summary[:500] + "..."
        profile.append(f"Summary: {summary}")
    
    # Add experience
    if contact.get('summary_experience'):
        experience = contact.get('summary_experience', '')
        if len(experience) > 300:
            experience = experience[:300] + "..."
        profile.append(f"Experience: {experience}")
    
    # Add company experience
    if contact.get('company_experience'):
        profile.append(f"Company Experience: {contact.get('company_experience', '')}")
    
    # Add education
    if contact.get('school_name_education') or contact.get('degree_education'):
        education = []
        if contact.get('school_name_education'):
            education.append(contact.get('school_name_education'))
        if contact.get('degree_education'):
            education.append(contact.get('degree_education'))
        if contact.get('field_of_study_education'):
            education.append(contact.get('field_of_study_education'))
        profile.append(f"Education: {' - '.join(education)}")
    
    # Add volunteering
    if contact.get('role_volunteering') or contact.get('company_name_volunteering'):
        volunteering = []
        if contact.get('role_volunteering'):
            volunteering.append(contact.get('role_volunteering'))
        if contact.get('company_name_volunteering'):
            volunteering.append(f"at {contact.get('company_name_volunteering')}")
        if contact.get('summary_volunteering'):
            vol_summary = contact.get('summary_volunteering')
            if len(vol_summary) > 200:
                vol_summary = vol_summary[:200] + "..."
            volunteering.append(vol_summary)
        profile.append(f"Volunteering: {' '.join(volunteering)}")
    
    return "\n".join(profile)

def evaluate_candidate_fit(client, candidate_profile, job_keywords, job_description):
    """Use OpenAI o3-mini to evaluate if a candidate is a good fit for a job."""
    return evaluate_with_openai(client, candidate_profile, job_keywords, job_description)

def evaluate_with_openai(client, candidate_profile, job_keywords, job_description):
    """Use OpenAI with structured output to determine candidate-job fit."""
    system_prompt = """
    You are an executive recruiter with expertise in matching candidates to job opportunities.
    Your task is to evaluate how well a candidate matches a job description.
    
    First analyze the job requirements carefully, then the candidate's profile.
    Compare the candidate's experience, skills, and qualifications against the job requirements.
    
    IMPORTANT EVALUATION FACTORS:
    1. Seniority level match: The most important factor is whether the candidate's current role is at an appropriate 
       seniority level for the position. Candidates currently in significantly more senior roles (e.g., C-suite, VP, 
       Senior Director at large organizations) will almost never take a step down for a mid-level role at a smaller 
       organization. This should HEAVILY penalize the match score and recommendation.
       
    2. Organization size match: Candidates from very large organizations (Fortune 500, major tech companies, 
       prestigious consulting firms) are unlikely to move to small organizations unless the role offers a significant 
       step up in seniority/responsibility.
       
    3. Salary compatibility: Consider if the candidate's current role/company likely offers higher compensation 
       than the position's salary range. If the candidate is at a major tech company, prestigious consulting firm, 
       or senior role at a large organization, they may be earning significantly more.
    
    4. Direct relevant experience: Prioritize candidates with specific experience in the exact field (philanthropy, 
       grantmaking, impact evaluation) over those with transferable but indirect experience.
       
    5. Mission alignment: Evaluate whether the candidate's career shows commitment to causes similar to 
       the organization's mission (economic mobility, equity, etc.).
       
    6. Operational experience: Consider experience with the specific operational aspects mentioned in the job 
       description (managing grants, evaluating impact, etc.).
    
    You must provide the following in your analysis as JSON:
    - match_score: An overall match score from 0-100 (where 100 is perfect match)
    - seniority_compatibility: A score from 0-100 on appropriate seniority level (0 = drastically overqualified, 100 = perfect match)
    - organization_size_match: A score from 0-100 on likelihood of moving from current org size to target org size
    - salary_compatibility: A score from 0-100 on likelihood the candidate would accept the offered salary range
    - relevant_experience: A score from 0-100 on direct relevant experience in the field
    - strengths: Key strengths that make the candidate a good fit (focus on relevant experience)
    - gaps: Key gaps in the candidate's profile relative to the requirements
    - recommend: Whether this candidate should be recommended for the position (true/false)
    - explanation: A brief rationale for the recommendation, including practical considerations like seniority and salary
    
    Be objective and fair in your assessment. Consider both hard skills and soft skills.
    """
    
    # Format the job keywords for better readability
    formatted_keywords = json.dumps(job_keywords, indent=2)
    
    user_prompt = f"""
    JOB DESCRIPTION:
    {job_description}
    
    TARGET ROLE CONTEXT: 
    - This is a mid-level Director role at Arrow Impact, a small philanthropy firm
    - The organization has fewer than 20 employees
    - The position's salary range is $165,000-$215,000
    - The role requires specific experience in philanthropy, grantmaking, and/or impact evaluation
    - Direct experience with economic mobility initiatives and equity-focused work is highly valuable
    - The organization values on-the-ground understanding of grantee perspectives
    
    JOB REQUIREMENTS (EXTRACTED):
    {formatted_keywords}
    
    CANDIDATE PROFILE:
    {candidate_profile}
    
    IMPORTANT PRACTICAL CONSIDERATIONS:
    - Candidates currently in C-level, VP, Senior Director roles at large organizations are VERY UNLIKELY to accept this position
    - Current executives at established foundations or large nonprofits are typically overqualified for this mid-level role
    - Individuals from major tech companies (Google, Meta, etc.) and consulting firms will typically require more senior positions
    - Candidates need domain expertise but should be at an appropriate career stage for a mid-level director role
    - The most suitable candidates are likely at the Manager, Director, or Senior Manager level in similar-sized or slightly larger organizations
    
    Evaluate this candidate's fit for the job opportunity and return your analysis as JSON.
    Focus on practical compatibility regarding seniority level, organization size, and salary expectations.
    """
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # If the new fields aren't present (for backward compatibility), add defaults
        if "seniority_compatibility" not in result:
            result["seniority_compatibility"] = 50
        if "organization_size_match" not in result:
            result["organization_size_match"] = 50
        if "salary_compatibility" not in result:
            result["salary_compatibility"] = 50
        if "relevant_experience" not in result:
            result["relevant_experience"] = 50
            
        # Adjust the match score to more heavily weight seniority and organization size compatibility
        result["match_score"] = int((result["match_score"] * 0.2) + 
                                  (result["seniority_compatibility"] * 0.3) + 
                                  (result["organization_size_match"] * 0.2) +
                                  (result["salary_compatibility"] * 0.15) + 
                                  (result["relevant_experience"] * 0.15))
        
        # Set recommendation based on adjusted score and strict seniority thresholds
        if (result["match_score"] >= 75 and 
            result["seniority_compatibility"] >= 70 and 
            result["organization_size_match"] >= 60 and
            result["salary_compatibility"] >= 60 and 
            result["relevant_experience"] >= 70):
            result["recommend"] = True
        else:
            result["recommend"] = False
            
        return result
    
    except Exception as e:
        print(f"Error evaluating candidate: {e}")
        # Return default low match if error
        return {
            "match_score": 0,
            "seniority_compatibility": 0,
            "organization_size_match": 0,
            "salary_compatibility": 0,
            "relevant_experience": 0,
            "strengths": [],
            "gaps": ["Error evaluating candidate"],
            "recommend": False,
            "explanation": f"Error during evaluation: {str(e)}"
        }

def format_recommendation_table(recommendations):
    """Format the recommendations into a readable table."""
    if not recommendations:
        return "No candidates found."
    
    # Sort recommendations by match score (highest first)
    sorted_recs = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)
    
    # Create table header
    table = "CANDIDATE MATCHES\n"
    table += "=" * 120 + "\n"
    table += f"{'Name':<25} {'Match':<7} {'Senr':<7} {'Org':<7} {'Salary':<7} {'Exp':<7} {'Recommended':<12} {'Email':<30} {'Position':<20}\n"
    table += "-" * 120 + "\n"
    
    # Add each recommendation to the table
    for rec in sorted_recs:
        name = f"{rec['first_name']} {rec['last_name']}"
        match = f"{rec['match_score']}%"
        seniority = f"{rec.get('seniority_compatibility', 'N/A')}%"
        org_size = f"{rec.get('organization_size_match', 'N/A')}%"
        salary = f"{rec.get('salary_compatibility', 'N/A')}%"
        exp = f"{rec.get('relevant_experience', 'N/A')}%"
        recommended = "YES" if rec['recommend'] else "NO"
        email = rec.get('email', 'N/A')
        position = rec.get('position', 'N/A')[:20]
        
        table += f"{name:<25} {match:<7} {seniority:<7} {org_size:<7} {salary:<7} {exp:<7} {recommended:<12} {email:<30} {position:<20}\n"
    
    return table

def save_recommendations_to_json(recommendations, output_file):
    """Save the recommendations to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(recommendations, f, indent=2)
    print(f"Recommendations saved to {output_file}")

def save_recommendations_to_csv(recommendations, output_file):
    """Save the recommendations to a CSV file."""
    if not recommendations:
        print("No candidates to export to CSV.")
        return
        
    # Define CSV headers
    fieldnames = ['first_name', 'last_name', 'match_score', 'seniority_compatibility', 'organization_size_match',
                 'salary_compatibility', 'relevant_experience', 'recommend', 'email', 'position', 
                 'company', 'linkedin_url', 'strengths', 'gaps', 'explanation']
    
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for rec in recommendations:
            # Join lists with semicolons for better CSV compatibility
            strengths = "; ".join(rec.get('strengths', []))
            gaps = "; ".join(rec.get('gaps', []))
            
            writer.writerow({
                'first_name': rec.get('first_name', ''),
                'last_name': rec.get('last_name', ''),
                'match_score': rec.get('match_score', 0),
                'seniority_compatibility': rec.get('seniority_compatibility', 'N/A'),
                'organization_size_match': rec.get('organization_size_match', 'N/A'),
                'salary_compatibility': rec.get('salary_compatibility', 'N/A'),
                'relevant_experience': rec.get('relevant_experience', 'N/A'),
                'recommend': 'Yes' if rec.get('recommend', False) else 'No',
                'email': rec.get('email', ''),
                'position': rec.get('position', ''),
                'company': rec.get('company', ''),
                'linkedin_url': rec.get('linkedin_url', ''),
                'strengths': strengths,
                'gaps': gaps,
                'explanation': rec.get('explanation', '')
            })
    
    print(f"Recommendations saved to CSV: {output_file}")

def create_html_report(recommendations, job_title, job_description, output_file):
    """Create an HTML report of the candidate recommendations."""
    if not recommendations:
        return "No candidates found."
    
    # Sort recommendations by match score (highest first)
    sorted_recs = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)
    
    # Pre-process job description to replace newlines with <br> tags
    job_description_html = job_description.replace('\n', '<br>')
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Match Report - {job_title}</title>
    <style>
        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            padding: 30px;
            margin-bottom: 30px;
        }}
        h1, h2, h3 {{
            color: #2d3748;
            font-weight: 600;
        }}
        h1 {{
            font-size: 28px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
        }}
        h2 {{
            font-size: 22px;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        h3 {{
            font-size: 18px;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        .job-details {{
            background-color: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4299e1;
            margin-bottom: 30px;
        }}
        .candidate {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #4299e1;
            position: relative;
        }}
        .candidate.recommended {{
            border-left: 4px solid #48bb78;
        }}
        .score {{
            position: absolute;
            top: 15px;
            right: 15px;
            background-color: #4299e1;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: 600;
        }}
        .score.high {{
            background-color: #48bb78;
        }}
        .score.medium {{
            background-color: #ed8936;
        }}
        .score.low {{
            background-color: #e53e3e;
        }}
        .metrics-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 15px 0;
        }}
        .metric {{
            background-color: #f7fafc;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 0.9em;
            display: inline-flex;
            align-items: center;
        }}
        .metric-label {{
            font-weight: 600;
            margin-right: 8px;
            color: #4a5568;
        }}
        .metric-value {{
            font-weight: 600;
        }}
        .metric-value.high {{
            color: #2f855a;
        }}
        .metric-value.medium {{
            color: #c05621;
        }}
        .metric-value.low {{
            color: #c53030;
        }}
        .section {{
            margin-top: 15px;
        }}
        .section-title {{
            font-weight: 600;
            margin-bottom: 5px;
            color: #4a5568;
        }}
        .strengths-list, .gaps-list {{
            list-style-type: none;
            padding-left: 0;
            margin-bottom: 0;
        }}
        .strengths-list li {{
            padding: 4px 0;
            position: relative;
            padding-left: 20px;
        }}
        .strengths-list li:before {{
            content: "✓";
            color: #48bb78;
            position: absolute;
            left: 0;
        }}
        .gaps-list li {{
            padding: 4px 0;
            position: relative;
            padding-left: 20px;
        }}
        .gaps-list li:before {{
            content: "!";
            color: #e53e3e;
            position: absolute;
            left: 0;
            font-weight: bold;
        }}
        .candidate-info {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .primary-info {{
            flex: 3;
        }}
        .secondary-info {{
            flex: 2;
        }}
        .info-row {{
            margin-bottom: 8px;
        }}
        .info-label {{
            font-weight: 600;
            color: #718096;
        }}
        .explanation {{
            margin-top: 15px;
            padding: 10px;
            background-color: #f7fafc;
            border-radius: 6px;
            font-style: italic;
            color: #4a5568;
        }}
        .recommendation-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-left: 10px;
        }}
        .recommendation-yes {{
            background-color: #c6f6d5;
            color: #2f855a;
        }}
        .recommendation-no {{
            background-color: #fed7d7;
            color: #c53030;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Job Match Report</h1>
        
        <!-- Job Description Section -->
        <div class="job-details">
            <h2>{job_title}</h2>
            <p><strong>Job Description:</strong></p>
            <p>{job_description_html}</p>
            <p><strong>Role Context:</strong> Mid-level Director at Arrow Impact (small philanthropy firm, <20 employees)</p>
        </div>
        
        <!-- Candidates Section -->
        <h2>Matched Candidates ({len(sorted_recs)})</h2>
"""
    
    for rec in sorted_recs:
        # Determine score class
        score_class = "high" if rec['match_score'] >= 75 else "medium" if rec['match_score'] >= 50 else "low"
        candidate_class = "recommended" if rec['recommend'] else ""
        
        # Get metrics and determine their classes
        seniority_score = rec.get('seniority_compatibility', 50)
        seniority_class = "high" if seniority_score >= 70 else "medium" if seniority_score >= 40 else "low"
        
        org_size_score = rec.get('organization_size_match', 50)
        org_size_class = "high" if org_size_score >= 70 else "medium" if org_size_score >= 40 else "low"
        
        salary_score = rec.get('salary_compatibility', 50)
        salary_class = "high" if salary_score >= 70 else "medium" if salary_score >= 40 else "low"
        
        experience_score = rec.get('relevant_experience', 50)
        experience_class = "high" if experience_score >= 70 else "medium" if experience_score >= 40 else "low"
        
        # Generate list items for strengths
        strengths_items = ""
        for strength in rec.get('strengths', []):
            strengths_items += f"<li>{strength}</li>"
            
        # Generate list items for gaps
        gaps_items = ""
        for gap in rec.get('gaps', []):
            gaps_items += f"<li>{gap}</li>"
            
        # Create recommendation badge class and text
        badge_class = "recommendation-yes" if rec['recommend'] else "recommendation-no"
        badge_text = "Recommended" if rec['recommend'] else "Not Recommended"
            
        html += f"""
        <div class="candidate {candidate_class}">
            <div class="score {score_class}">{rec['match_score']}%</div>
            <h3>
                {rec['first_name']} {rec['last_name']}
                <span class="recommendation-badge {badge_class}">
                    {badge_text}
                </span>
            </h3>
            
            <div class="metrics-container">
                <div class="metric">
                    <span class="metric-label">Seniority Match:</span> 
                    <span class="metric-value {seniority_class}">{seniority_score}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Org Size Match:</span> 
                    <span class="metric-value {org_size_class}">{org_size_score}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Salary Match:</span> 
                    <span class="metric-value {salary_class}">{salary_score}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Experience:</span> 
                    <span class="metric-value {experience_class}">{experience_score}%</span>
                </div>
            </div>
            
            <div class="candidate-info">
                <div class="primary-info">
                    <div class="info-row">
                        <span class="info-label">Current Position:</span> {rec.get('position', 'N/A')}
                    </div>
                    <div class="info-row">
                        <span class="info-label">Company:</span> {rec.get('company', 'N/A')}
                    </div>
                    <div class="info-row">
                        <span class="info-label">Email:</span> {rec.get('email', 'N/A')}
                    </div>
                    <div class="info-row">
                        <span class="info-label">LinkedIn:</span> 
                        <a href="{rec.get('linkedin_url', '#')}" target="_blank">{rec.get('linkedin_url', 'N/A')}</a>
                    </div>
                </div>
                
                <div class="secondary-info">
                    <div class="section">
                        <div class="section-title">Key Strengths:</div>
                        <ul class="strengths-list">
                            {strengths_items}
                        </ul>
                    </div>
                    
                    <div class="section">
                        <div class="section-title">Gaps:</div>
                        <ul class="gaps-list">
                            {gaps_items}
                        </ul>
                    </div>
                </div>
            </div>
            
            <div class="explanation">
                <strong>Analysis:</strong> {rec.get('explanation', 'No explanation provided.')}
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"HTML report saved to {output_file}")
    return output_file

def job_matching_workflow(job_title, job_description, location=None, min_score=60, batch_size=50, max_candidates=None, output_format="all"):
    """Main workflow for job matching."""
    print(f"\nStarting job matching workflow for: {job_title}")
    print("=" * 80)
    
    # Initialize clients
    openai_client = create_openai_client()
    supabase_client = create_supabase_client()
    
    # Process job description
    print("\nAnalyzing job description...")
    job_keywords = extract_job_keywords(openai_client, job_description)
    print("Job keywords extracted successfully.")
    
    # Process candidates
    recommendations = []
    offset = 0
    total_processed = 0
    consecutive_empty_batches = 0
    max_empty_batches = 3  # Allow up to 3 consecutive empty batches before stopping
    
    # Get an estimate of how many contacts we might process (for logging purposes)
    if location and location.lower() == "bay area":
        try:
            count_result = supabase_client.table('contacts').select('count').filter('location_name', 'ilike', '%Bay Area%').execute()
            total_candidates = count_result.data[0]['count'] if count_result.data else "unknown"
            print(f"Found approximately {total_candidates} contacts in the Bay Area")
        except Exception as e:
            print(f"Could not count total candidates: {e}")
            total_candidates = "unknown"
    
    print("\nFetching and evaluating candidates...")
    while True:
        # Fetch a batch of candidates
        candidates = fetch_candidate_batch(supabase_client, location, batch_size, offset)
        
        if not candidates:
            consecutive_empty_batches += 1
            if consecutive_empty_batches >= max_empty_batches:
                print(f"Received {max_empty_batches} consecutive empty batches. Stopping search.")
                break
            
            # Try next batch anyway
            offset += batch_size
            continue
        else:
            consecutive_empty_batches = 0  # Reset counter when we get results
        
        batch_matches = 0  # Track matches in this batch
        
        for candidate in candidates:
            # Prepare candidate profile
            profile = prepare_candidate_profile(candidate)
            
            # Evaluate candidate fit
            print(f"Evaluating: {candidate.get('first_name', '')} {candidate.get('last_name', '')}")
            evaluation = evaluate_candidate_fit(openai_client, profile, job_keywords, job_description)
            
            # Add candidate info to evaluation
            evaluation.update({
                'id': candidate.get('id'),
                'first_name': candidate.get('first_name', ''),
                'last_name': candidate.get('last_name', ''),
                'email': candidate.get('work_email') or candidate.get('email') or candidate.get('personal_email') or '',
                'position': candidate.get('position', ''),
                'company': candidate.get('company', ''),
                'linkedin_url': candidate.get('linkedin_url', '')
            })
            
            # Add to recommendations if above threshold
            if evaluation['match_score'] >= min_score:
                recommendations.append(evaluation)
                batch_matches += 1
                print(f"  Match score: {evaluation['match_score']}% - {'RECOMMENDED' if evaluation['recommend'] else 'NOT RECOMMENDED'}")
            else:
                print(f"  Match score: {evaluation['match_score']}% - BELOW THRESHOLD")
            
            total_processed += 1
            
            # Check if we've reached max candidates
            if max_candidates and total_processed >= max_candidates:
                print(f"Reached maximum candidate limit ({max_candidates})")
                break
            
            # API rate limiting
            time.sleep(API_RATE_LIMIT)
        
        # Check if we've reached max candidates
        if max_candidates and total_processed >= max_candidates:
            break
        
        # Report on this batch
        print(f"Batch complete: Found {batch_matches} matches from {len(candidates)} candidates (total processed: {total_processed})")
        
        # Move to next batch
        offset += batch_size
        print(f"Moving to next batch at offset {offset}")
    
    print(f"\nProcessed {total_processed} candidates.")
    print(f"Found {len(recommendations)} matches above the {min_score}% threshold.")
    
    # Sort recommendations by match score (highest first)
    recommendations = sorted(recommendations, key=lambda x: x['match_score'], reverse=True)
    
    # Output based on format preference
    if output_format in ['all', 'table']:
        print("\n" + format_recommendation_table(recommendations))
    
    if output_format in ['all', 'json']:
        output_file = f"job_matches_{job_title.replace(' ', '_').lower()}_{time.strftime('%Y%m%d')}.json"
        save_recommendations_to_json(recommendations, output_file)
    
    if output_format in ['all', 'csv']:
        output_file = f"job_matches_{job_title.replace(' ', '_').lower()}_{time.strftime('%Y%m%d')}.csv"
        save_recommendations_to_csv(recommendations, output_file)
    
    if output_format in ['all', 'html']:
        output_file = f"job_matches_{job_title.replace(' ', '_').lower()}_{time.strftime('%Y%m%d')}.html"
        create_html_report(recommendations, job_title, job_description, output_file)
    
    return recommendations

def main():
    parser = argparse.ArgumentParser(description="Match job descriptions to your professional network")
    parser.add_argument("--title", type=str, help="Job title")
    parser.add_argument("--description_file", type=str, help="File containing job description")
    parser.add_argument("--location", type=str, help="Location to filter candidates (e.g. 'Bay Area', 'New York')")
    parser.add_argument("--min_score", type=int, default=60, help="Minimum match score (0-100)")
    parser.add_argument("--batch_size", type=int, default=50, help="Batch size for processing candidates")
    parser.add_argument("--max_candidates", type=int, help="Maximum number of candidates to process")
    parser.add_argument("--output", type=str, default="all", choices=["all", "table", "json", "html", "csv"], 
                        help="Output format(s)")
    
    args = parser.parse_args()
    
    # If no arguments provided, prompt for job details
    if len(sys.argv) == 1:
        print("\nJob Opportunity Matcher")
        print("======================")
        args.title = input("Enter job title: ")
        
        location_input = input("Enter location filter (optional, press Enter to skip): ")
        args.location = location_input if location_input.strip() else None
        
        print("\nEnter job description (type 'DONE' on a new line when finished):")
        job_description_lines = []
        while True:
            line = input()
            if line == "DONE":
                break
            job_description_lines.append(line)
        
        job_description = "\n".join(job_description_lines)
    else:
        # Read job description from file
        if args.description_file:
            with open(args.description_file, 'r') as f:
                job_description = f.read()
        else:
            print("Error: Job description file is required")
            parser.print_help()
            return
    
    # Run the job matching workflow
    job_matching_workflow(
        args.title, 
        job_description,
        location=args.location,
        min_score=args.min_score,
        batch_size=args.batch_size,
        max_candidates=args.max_candidates,
        output_format=args.output
    )

if __name__ == "__main__":
    main() 