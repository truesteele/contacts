#!/bin/bash

# Run Job Matcher Script
# Usage: ./run_job_matcher.sh [OPTIONS]

# Default values
JOB_TITLE=""
JOB_DESC_FILE=""
LOCATION=""
MIN_SCORE=60
BATCH_SIZE=50
MAX_CANDIDATES=""
OUTPUT_FORMAT="all"

# Function to display usage information
function show_usage {
  echo "Usage: ./run_job_matcher.sh [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  -t, --title TITLE        Job title"
  echo "  -f, --file FILE          File containing job description"
  echo "  -l, --location LOCATION  Location to filter candidates (e.g. 'Bay Area')"
  echo "  -s, --score SCORE        Minimum match score (0-100, default: 60)"
  echo "  -b, --batch BATCH        Batch size for processing candidates (default: 50)"
  echo "  -m, --max MAX            Maximum number of candidates to process"
  echo "  -o, --output FORMAT      Output format: all, table, json, html, csv (default: all)"
  echo "  -i, --interactive        Run in interactive mode (prompt for job details)"
  echo "  -h, --help               Show this help message"
  echo ""
  echo "Example:"
  echo "  ./run_job_matcher.sh -t \"Director\" -f arrow_impact_director.txt -l \"Bay Area\" -s 70"
  echo "  ./run_job_matcher.sh -t \"Developer\" -f job_desc.txt -o csv"
  echo ""
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--title)
      JOB_TITLE="$2"
      shift 2
      ;;
    -f|--file)
      JOB_DESC_FILE="$2"
      shift 2
      ;;
    -l|--location)
      LOCATION="$2"
      shift 2
      ;;
    -s|--score)
      MIN_SCORE="$2"
      shift 2
      ;;
    -b|--batch)
      BATCH_SIZE="$2"
      shift 2
      ;;
    -m|--max)
      MAX_CANDIDATES="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_FORMAT="$2"
      shift 2
      ;;
    -i|--interactive)
      # Will run Python script with no args to trigger interactive mode
      JOB_TITLE=""
      JOB_DESC_FILE=""
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Check if running in interactive mode
if [ -z "$JOB_TITLE" ] && [ -z "$JOB_DESC_FILE" ]; then
  # Interactive mode
  python3 job_matcher.py
else
  # Command-line mode
  CMD="python3 job_matcher.py"
  
  if [ ! -z "$JOB_TITLE" ]; then
    CMD="$CMD --title \"$JOB_TITLE\""
  fi
  
  if [ ! -z "$JOB_DESC_FILE" ]; then
    CMD="$CMD --description_file \"$JOB_DESC_FILE\""
  fi

  if [ ! -z "$LOCATION" ]; then
    CMD="$CMD --location \"$LOCATION\""
  fi
  
  CMD="$CMD --min_score $MIN_SCORE --batch_size $BATCH_SIZE"
  
  if [ ! -z "$MAX_CANDIDATES" ]; then
    CMD="$CMD --max_candidates $MAX_CANDIDATES"
  fi
  
  CMD="$CMD --output $OUTPUT_FORMAT"
  
  # Execute the command
  eval $CMD
fi 