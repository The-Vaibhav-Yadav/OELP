#!/usr/bin/env python3
"""
GATE PDF Downloader Script

This script automatically downloads GATE previous year question papers
from the official website for all 30 streams across the past 5 years.
Files are saved with proper naming convention for the data pipeline.

Usage:
  python tools/download_gate_pdfs.py           # Download all PDFs
  python tools/download_gate_pdfs.py --list    # List existing files
  python tools/download_gate_pdfs.py --help    # Show help
"""

import os
import requests
import time
from pathlib import Path
from urllib.parse import urljoin
import sys

# All 30 GATE streams as per the website
GATE_STREAMS = [
    "AE", "AG", "AR", "BM", "BT", "CE", "CH", "CS", "CY", "DA",
    "EC", "EE", "EN", "ES", "EY", "GE", "GG", "IN", "MA", "ME",
    "MN", "MT", "NM", "PE", "PH", "PI", "ST", "TF", "XE", "XL"
]

# Years to download (past 5 years)
YEARS = [2025, 2024, 2023, 2022, 2021]

# Base URL patterns observed from the website
BASE_URL = "https://gate2026.iitg.ac.in/doc/download/"

def get_pdf_url_patterns(year, stream):
    """
    Generate possible PDF URL patterns based on the website structure.
    Returns a list of potential URLs to try based on actual URL patterns observed.
    """
    patterns = []
    
    if year == 2025:
        # For 2025: STREAM2025.pdf format (uppercase)
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")
    elif year == 2024:
        # For 2024: Complex patterns with different session/set numbers
        # Based on observed patterns: AR24S1, CS224S6, AE24S5, AG24S5, CE224S4, XHC324S3
        
        # Try multiple session numbers (S1 through S6)
        for session in range(1, 7):
            # Pattern 1: Stream + 24 + S + Number (e.g., AR24S1, AE24S5)
            patterns.append(f"{BASE_URL}{year}/{stream}24S{session}.pdf")
            
            # Pattern 2: Stream + 224 + S + Number (e.g., CS224S6, CE224S4)
            patterns.append(f"{BASE_URL}{year}/{stream}224S{session}.pdf")
            
            # Special cases for XH and XL streams (with specialty codes)
            if stream in ["XH", "XL"]:
                # XH has specialties like XHC3 (Linguistics)
                for specialty in ["C1", "C2", "C3", "C4", "C5", "C6"]:
                    patterns.append(f"{BASE_URL}{year}/{stream}{specialty}24S{session}.pdf")
                    patterns.append(f"{BASE_URL}{year}/{stream}{specialty}224S{session}.pdf")
        
        # Fallback patterns
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")  # CS2024.pdf fallback
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}{year}.pdf")  # cs2024.pdf fallback
    elif year == 2023:
        # For 2023: stream_2023.pdf format (lowercase with underscore)
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}_{year}.pdf")  # ee_2023.pdf
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")  # EE2023.pdf fallback
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}{year}.pdf")  # ee2023.pdf fallback
    elif year == 2022:
        # For 2022: stream_2022.pdf format (lowercase with underscore)
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}_{year}.pdf")  # ag_2022.pdf
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")  # AG2022.pdf fallback
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}{year}.pdf")  # ag2022.pdf fallback
    elif year == 2021:
        # For 2021: stream_2021.pdf format (lowercase with underscore)
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}_{year}.pdf")  # ch_2021.pdf
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")  # CH2021.pdf fallback
    
    return patterns

def download_file(url, local_path, max_retries=3):
    """
    Download a file from URL to local path with retry logic.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            print(f"  Attempting to download: {url}")
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                # Check if it's actually a PDF by looking at content type or first few bytes
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type:
                    # Check first few bytes for PDF signature
                    response.content  # Load content
                    if not response.content.startswith(b'%PDF'):
                        print(f"  ❌ Not a valid PDF file")
                        return False
                
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = os.path.getsize(local_path)
                if file_size > 1000:  # At least 1KB
                    print(f"  ✅ Downloaded successfully ({file_size:,} bytes)")
                    return True
                else:
                    print(f"  ❌ File too small ({file_size} bytes), likely not a valid PDF")
                    os.remove(local_path)
                    return False
                    
            elif response.status_code == 404:
                print(f"  ❌ File not found (404)")
                return False
            else:
                print(f"  ⚠️  HTTP {response.status_code} - Retrying...")
                
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Request failed: {e} - Retrying...")
        
        if attempt < max_retries - 1:
            time.sleep(2)  # Wait before retry
    
    print(f"  ❌ Failed after {max_retries} attempts")
    return False

def generate_local_filename(stream, year, session=1):
    """
    Generate the local filename following our naming convention.
    Format: GATE-YYYY-STREAM-Session-N.pdf
    """
    return f"GATE-{year}-{stream}-Session-{session}.pdf"

def download_gate_pdfs():
    """
    Main function to download all GATE PDFs.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from tools/
    output_dir = os.path.join(project_root, "data_pipeline", "source_pdfs", "GATE")
    
    print(f"🚀 Starting GATE PDF Download")
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Downloading {len(GATE_STREAMS)} streams × {len(YEARS)} years = {len(GATE_STREAMS) * len(YEARS)} files")
    print("=" * 80)
    
    successful_downloads = 0
    failed_downloads = 0
    
    for year in YEARS:
        print(f"\n📅 Processing Year: {year}")
        print("-" * 50)
        
        for stream in GATE_STREAMS:
            print(f"\n📋 Stream: {stream}")
            
            # Generate possible URLs to try
            url_patterns = get_pdf_url_patterns(year, stream)
            
            # Generate local filename
            local_filename = generate_local_filename(stream, year)
            local_path = os.path.join(output_dir, local_filename)
            
            # Skip if file already exists
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                print(f"  ✅ Already exists ({file_size:,} bytes) - Skipping")
                successful_downloads += 1
                continue
            
            # Try each URL pattern until one works
            download_success = False
            for url in url_patterns:
                if download_file(url, local_path):
                    download_success = True
                    successful_downloads += 1
                    break
            
            if not download_success:
                failed_downloads += 1
                print(f"  ❌ Failed to download {stream} {year}")
            
            # Small delay to be respectful to the server
            time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print(f"📊 Download Summary:")
    print(f"✅ Successful: {successful_downloads}")
    print(f"❌ Failed: {failed_downloads}")
    print(f"📁 Files saved to: {output_dir}")
    
    if successful_downloads > 0:
        print(f"\n🎉 Downloaded {successful_downloads} GATE PDF files!")
        print("Next steps:")
        print("1. Run: uv run python -m data_pipeline.scripts.parse_pdfs")
        print("2. Run: uv run python -m data_pipeline.scripts.build_vector_db") 
        print("3. Test GATE exam generation via API")
    else:
        print("\n⚠️  No files were downloaded. Please check:")
        print("1. Internet connection")
        print("2. Website availability")
        print("3. URL patterns (may have changed)")

def list_existing_files():
    """
    List already downloaded GATE PDF files.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "data_pipeline", "source_pdfs", "GATE")
    
    if not os.path.exists(output_dir):
        print(f"Directory {output_dir} does not exist.")
        return
    
    pdf_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
    
    if pdf_files:
        print(f"📁 Found {len(pdf_files)} GATE PDF files in {output_dir}:")
        for filename in sorted(pdf_files):
            file_path = os.path.join(output_dir, filename)
            file_size = os.path.getsize(file_path)
            print(f"  📄 {filename} ({file_size:,} bytes)")
    else:
        print(f"📁 No GATE PDF files found in {output_dir}")

def main():
    """
    Main entry point with command line options.
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_existing_files()
            return
        elif sys.argv[1] == "--help":
            print("GATE PDF Downloader")
            print("Usage:")
            print("  python tools/download_gate_pdfs.py           # Download all PDFs")
            print("  python tools/download_gate_pdfs.py --list    # List existing files")
            print("  python tools/download_gate_pdfs.py --help    # Show this help")
            return
    
    download_gate_pdfs()

if __name__ == "__main__":
    main()
