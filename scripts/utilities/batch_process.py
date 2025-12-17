#!/usr/bin/env python3
"""
Batch processing script for contact categorization.
This helps process a large CSV file in manageable chunks to avoid timeouts and manage API usage.
"""

import argparse
import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Process contacts in batches")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file path")
    parser.add_argument("--output", type=str, required=True, help="Output CSV file path")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of contacts per batch")
    parser.add_argument("--start", type=int, default=0, help="Starting index in the CSV file")
    parser.add_argument("--end", type=int, help="Ending index in the CSV file (optional)")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds between batches")
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist")
        return
    
    current_index = args.start
    batch_number = 1
    
    print(f"Starting batch processing at index {current_index}")
    print(f"Batch size: {args.batch_size}")
    print(f"Output file: {args.output}")
    print(f"Input file: {args.input}")
    print("-" * 60)
    
    # Get OpenAI API key from environment
    openai_apikey = os.environ.get("OPENAI_APIKEY")
    if not openai_apikey:
        print("Error: OPENAI_APIKEY environment variable not set")
        return
    
    # Create a custom environment with the API key
    env = os.environ.copy()
    
    try:
        while True:
            # Check if we've reached the end index if specified
            if args.end is not None and current_index >= args.end:
                print(f"Reached specified end index {args.end}. Processing complete.")
                break
                
            # Print batch info
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing batch #{batch_number}")
            print(f"Starting at index {current_index}, processing {args.batch_size} contacts")
            
            # Build the command
            cmd = [
                "python3", "categorize_contacts.py",
                "--input", args.input,
                "--output", args.output,
                "--start", str(current_index),
                "--sample", str(args.batch_size)
            ]
            
            # Run the batch process with the custom environment
            process = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # Check for errors
            if process.returncode != 0:
                print(f"Error in batch #{batch_number}:")
                print(process.stderr)
                
                # Ask user if they want to continue
                user_input = input("Continue processing? (y/n): ").strip().lower()
                if user_input != 'y':
                    print("Batch processing halted by user.")
                    break
            else:
                # Print output
                print(process.stdout)
            
            # Update for next batch
            current_index += args.batch_size
            batch_number += 1
            
            # Add delay between batches
            if args.delay > 0:
                print(f"Waiting {args.delay} seconds before next batch...")
                time.sleep(args.delay)
            
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        print(f"Last processed index: {current_index - 1}")
        print("You can resume processing with:")
        print(f"python batch_process.py --input {args.input} --output {args.output} --start {current_index} --batch-size {args.batch_size}")
    
    print("\nBatch processing complete.")
    print(f"Final results saved to: {args.output}")

if __name__ == "__main__":
    main() 