#!/usr/bin/env python3
import json
import os
from bs4 import BeautifulSoup

# List of candidates to include
selected_candidates = [
    "Samantha Sandoval",
    "Kavitha Sreeharsha",
    "Lara Fox",
    "Landon Dickey",
    "Evan Schwartz",
    "J. M. Johnson"
]

# Path to the original HTML file
original_html_path = "job_matches_director_20250421.html"
output_html_path = "selected_candidates.html"

def extract_selected_candidates():
    # Check if the original HTML file exists
    if not os.path.exists(original_html_path):
        print(f"Error: Could not find {original_html_path}")
        return False
    
    try:
        # Read the original HTML file
        with open(original_html_path, 'r') as file:
            html_content = file.read()
        
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get all candidate divs
        all_candidates = soup.find_all('div', class_='candidate')
        
        # Filter candidates to include only the selected ones
        filtered_candidates = []
        found_candidates = set()  # Track unique candidates
        
        for candidate in all_candidates:
            # Get the candidate name from the h3 tag
            name_element = candidate.find('h3')
            if name_element:
                # Extract the name (removing the recommendation badge)
                name = name_element.text.strip().split('\n')[0].strip()
                
                # Check if this candidate is in our selected list
                for selected_name in selected_candidates:
                    # Check if the selected name is in the candidate name and not already found
                    if selected_name.lower() in name.lower() and selected_name not in found_candidates:
                        filtered_candidates.append(candidate)
                        found_candidates.add(selected_name)  # Mark this candidate as found
                        break
        
        # Create a new HTML with only the selected candidates
        new_soup = BeautifulSoup('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Selected Candidates</title>
    <style>
        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            padding: 30px;
            margin-bottom: 30px;
        }
        h1, h2, h3 {
            color: #2d3748;
            font-weight: 600;
        }
        h1 {
            font-size: 28px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
        }
        h2 {
            font-size: 22px;
            margin-top: 30px;
            margin-bottom: 15px;
        }
        h3 {
            font-size: 18px;
            margin-top: 25px;
            margin-bottom: 10px;
        }
        .candidate {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #4299e1;
            position: relative;
        }
        .candidate.recommended {
            border-left: 4px solid #48bb78;
        }
        .score {
            position: absolute;
            top: 15px;
            right: 15px;
            background-color: #4299e1;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: 600;
        }
        .score.high {
            background-color: #48bb78;
        }
        .score.medium {
            background-color: #ed8936;
        }
        .score.low {
            background-color: #e53e3e;
        }
        .section {
            margin-top: 15px;
        }
        .section-title {
            font-weight: 600;
            margin-bottom: 5px;
            color: #4a5568;
        }
        .strengths-list, .gaps-list {
            list-style-type: none;
            padding-left: 0;
            margin-bottom: 0;
        }
        .strengths-list li {
            padding: 4px 0;
            position: relative;
            padding-left: 20px;
        }
        .strengths-list li:before {
            content: "✓";
            color: #48bb78;
            position: absolute;
            left: 0;
        }
        .gaps-list li {
            padding: 4px 0;
            position: relative;
            padding-left: 20px;
        }
        .gaps-list li:before {
            content: "!";
            color: #e53e3e;
            position: absolute;
            left: 0;
            font-weight: bold;
        }
        .candidate-info {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }
        .primary-info {
            flex: 3;
        }
        .secondary-info {
            flex: 2;
        }
        .info-row {
            margin-bottom: 8px;
        }
        .info-label {
            font-weight: 600;
            color: #718096;
        }
        .explanation {
            margin-top: 15px;
            padding: 10px;
            background-color: #f7fafc;
            border-radius: 6px;
            font-style: italic;
            color: #4a5568;
        }
        .recommendation-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-left: 10px;
        }
        .recommendation-yes {
            background-color: #c6f6d5;
            color: #2f855a;
        }
        .recommendation-no {
            background-color: #fed7d7;
            color: #c53030;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Selected Candidates</h1>
    </div>
</body>
</html>''', 'html.parser')
        
        # Get the container div in the new HTML
        container = new_soup.find('div', class_='container')
        
        # Add a candidates section header
        candidates_header = new_soup.new_tag('h2')
        candidates_header.string = f'Selected Candidates ({len(filtered_candidates)})'
        container.append(candidates_header)
        
        # Add each selected candidate to the new HTML
        for candidate in filtered_candidates:
            container.append(candidate)
        
        # Write the new HTML to a file
        with open(output_html_path, 'w') as file:
            file.write(str(new_soup))
        
        print(f"Created {output_html_path} with {len(filtered_candidates)} unique selected candidates")
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    extract_selected_candidates() 