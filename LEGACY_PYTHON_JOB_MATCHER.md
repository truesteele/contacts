# Job Opportunity Matcher

A tool to efficiently search your professional network from Supabase for suitable candidates when you receive job opportunities. The system uses OpenAI's o3-mini model with structured output to analyze job descriptions and determine which contacts would be a good fit based on their skills, experience, and qualifications.

## Features

- Extract key requirements from job descriptions using structured JSON output
- Filter candidates by location before evaluation to save API costs
- Match requirements against your contacts' LinkedIn profiles
- Score each candidate based on fit, with advanced compatibility metrics:
  - **Seniority level compatibility**: Evaluates whether a candidate's current role is at an appropriate seniority level
  - **Organization size match**: Assesses the likelihood of a candidate moving from their current organization size
  - **Salary compatibility**: Estimates if the position's compensation is attractive to the candidate
  - **Relevant experience**: Measures the candidate's direct experience in the required field
- Generate detailed reports in multiple formats
- Beautiful, modern HTML reports with strengths and gaps analysis

## API Costs

The job matcher uses OpenAI's o3-mini model, which offers an excellent balance of intelligence and cost-effectiveness:

### Price Structure
- **Input tokens**: $1.10 per million tokens
- **Output tokens**: $4.40 per million tokens

### Cost Estimation for a Bay Area Job Search
For a typical search of Bay Area contacts (approximately 700 candidates):

| Cost Component | Calculation | Amount |
|----------------|-------------|--------|
| Input Tokens | ~2,500 tokens/candidate × 700 candidates × $1.10/M tokens | ~$1.93 |
| Output Tokens | ~750 tokens/candidate × 700 candidates × $4.40/M tokens | ~$2.31 |
| **Total Cost** | | **~$4.24** |

This represents a very cost-effective solution compared to using more expensive models like GPT-4 or o1, which would cost 10-15 times more for the same operation.

### Cost Optimization
The job matcher implements several strategies to minimize API costs:
- Location-based pre-filtering before sending to the API
- Efficient pagination with batch processing
- Intelligent handling of empty result sets
- Configurable maximum candidate limit

You can further control costs by adjusting:
- The batch size parameter (`-b`)
- The maximum number of candidates to process (`-m`)
- The geographic filtering (`-l`)

## Setup

1. Ensure your Supabase contacts database is set up and has LinkedIn profile data
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Make sure your `.env` file contains the necessary API keys:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   OPENAI_APIKEY=your_openai_api_key
   OPENAI_MODEL=o3-mini  # Using o3-mini for structured JSON output
   ```

## Usage

### Interactive Mode

Run the script without arguments to use interactive mode:

```bash
python job_matcher.py
```

Or use the helper script:

```bash
./run_job_matcher.sh -i
```

### Command Line Mode

```bash
python job_matcher.py --title "Job Title" --description_file path/to/job_description.txt --location "Location"
```

Or use the helper script:

```bash
./run_job_matcher.sh -t "Job Title" -f path/to/job_description.txt -l "Location"
```

### Options

- `--title`: Job title
- `--description_file`: File containing job description
- `--location`: Location to filter candidates (e.g., "Bay Area", "New York")
- `--min_score`: Minimum match score (0-100, default: 60)
- `--batch_size`: Batch size for processing candidates (default: 50)
- `--max_candidates`: Maximum number of candidates to process
- `--output`: Output format(s): "all", "table", "json", "csv", or "html" (default: "all")

### Example

```bash
./run_job_matcher.sh -t "Director" -f arrow_impact_director.txt -l "Bay Area" -s 70 -m 100
```

This will:
1. Search for candidates for the "Director" position
2. Use the job description from the file "arrow_impact_director.txt"
3. Filter to only consider candidates in the Bay Area
4. Only include candidates with a match score of 70% or higher
5. Process a maximum of 100 candidates

## Output

By default, the job matcher produces four types of output:

1. **Console table**: Quick overview of matched candidates with key metrics
2. **JSON file**: Complete data for further analysis
3. **CSV file**: Spreadsheet format for easy filtering and sorting
4. **HTML report**: Beautiful, modern UI for reviewing candidates

The HTML report includes:
- Clear visual indicators for match scores
- Detailed compatibility metrics for seniority, organization size, salary, and experience
- Candidate details and contact information
- Key strengths and gaps analysis
- Explanations of why each candidate is a good fit

## How It Works

### Smart Matching Algorithm

The job matcher uses a sophisticated algorithm that considers multiple factors when evaluating candidates:

1. **Seniority Level Compatibility (30%)**: 
   - Evaluates if the candidate's current role is at an appropriate seniority level for the position
   - Heavily penalizes candidates who are significantly overqualified (e.g., C-suite executives for mid-level roles)
   - Prevents recommendations that would require a step down in seniority

2. **Organization Size Match (20%)**:
   - Assesses the likelihood of a candidate moving from their current organization size
   - Recognizes that people at large organizations rarely move to small organizations unless it's a step up
   - Accounts for organizational culture differences between large and small companies

3. **Salary Compatibility (15%)**:
   - Estimates if the position's compensation would be attractive to the candidate
   - Considers industry norms and typical salary differentials between company types

4. **Relevant Experience (15%)**:
   - Evaluates the candidate's direct experience in the required field
   - Values domain-specific expertise over transferable skills

5. **Overall Match (20%)**:
   - Considers skills, qualifications, and other factors
   - Captures aspects not covered by the specialized metrics

This weighted approach ensures that candidates aren't just matched on skills, but on practical considerations that impact whether they would realistically accept the position.

### Smart Location Filtering

The job matcher specifically handles the Bay Area region by including a comprehensive list of cities within commuting distance. For Bay Area searches, it looks for:

- Specific cities: Oakland, San Francisco, Berkeley, Alameda, etc.
- Regional terms: "Bay Area", "East Bay", "Peninsula", etc.
- General regional markers: "Northern California", "SF Bay", etc.

This ensures you don't miss good candidates due to how they've listed their location.

### Matching Workflow

1. The job description is analyzed to extract key requirements using o3-mini with structured JSON output
2. Location-based filtering is applied to Supabase query to reduce the number of candidates evaluated
3. Each contact's LinkedIn profile data is formatted for analysis
4. AI evaluates the candidate against each compatibility factor
5. Candidates are scored on a scale of 0-100 for each factor, with a weighted overall score
6. Additional analysis identifies specific strengths and gaps
7. Results are formatted into reports with clear visual indicators for each compatibility metric

## Technical Details

### Structured JSON Schema

The job matcher uses Pydantic models with OpenAI's structured output feature to ensure consistent, well-structured data. This provides several benefits:

- Strict schema enforcement ensures consistent data structures
- Reduces hallucinations by constraining AI outputs
- Improves processing efficiency by eliminating malformed responses
- Makes the system more robust to API changes

### Candidate Filtering Process

The matcher employs a multi-stage filtering process:

1. **Geographic Filtering**: Applies location-based filters at the database level
2. **Compatibility Scoring**: Evaluates candidates against multiple compatibility metrics
3. **Threshold Filtering**: Only includes candidates with scores above the minimum threshold
4. **Recommendation Logic**: Applies strict criteria for final recommendations:
   - Overall score ≥ 75%
   - Seniority compatibility ≥ 70%
   - Organization size match ≥ 60%
   - Salary compatibility ≥ 60%
   - Relevant experience ≥ 70%

### Customizing Match Thresholds

You can adjust the minimum match score to be more or less selective:

```bash
./run_job_matcher.sh -t "Director" -f job_description.txt -l "Bay Area" -s 80  # Very selective
./run_job_matcher.sh -t "Director" -f job_description.txt -l "Bay Area" -s 50  # More inclusive
```

### Processing Large Contact Databases

For very large contact databases, the system handles pagination intelligently:

- Processes candidates in batches (default: 50)
- Continues fetching until it reaches the maximum specified or exhausts the database
- Allows up to 3 consecutive empty batches before stopping (handles sparse data)
- Reports progress after each batch

Example for processing in smaller batches:

```bash
./run_job_matcher.sh -t "Director" -f job_description.txt -l "Bay Area" -b 20 -m 100
```

This will process 20 candidates at a time, up to a maximum of 100 candidates.

## Filtering and Post-Processing Tools

After generating matches, you can use additional tools to refine your selection:

### Extracting Selected Candidates

For presentations or sharing with hiring managers, you can extract just the candidates you're interested in:

```bash
python extract_selected_candidates.py
```

This script creates a new HTML file containing only the specified candidates. You can customize the list of selected candidates in the script. 