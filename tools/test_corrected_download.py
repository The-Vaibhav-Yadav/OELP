#!/usr/bin/env python3
"""
Test downloading a few PDFs with the corrected patterns
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from download_gate_pdfs import get_pdf_url_patterns, download_file, generate_local_filename

def test_download_corrected():
    """Test downloading a few PDFs with corrected patterns"""
    test_downloads = [
        ("AG", 2022),
        ("EE", 2023), 
        ("CS", 2024),
        ("CH", 2021)
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(script_dir, "test_downloads_corrected")
    os.makedirs(test_dir, exist_ok=True)
    
    print("🔍 Testing corrected download patterns...")
    print(f"📁 Test directory: {test_dir}")
    print("=" * 60)
    
    for stream, year in test_downloads:
        print(f"\n📋 Testing download: {stream} {year}")
        
        patterns = get_pdf_url_patterns(year, stream)
        local_filename = generate_local_filename(stream, year)
        local_path = os.path.join(test_dir, local_filename)
        
        # Try each pattern until one works
        success = False
        for url in patterns:
            print(f"  🔄 Trying: {url}")
            if download_file(url, local_path):
                success = True
                print(f"  ✅ Downloaded: {local_filename}")
                break
        
        if not success:
            print(f"  ❌ Failed to download {stream} {year}")
    
    print(f"\n📊 Test downloads completed. Check {test_dir} for files.")

if __name__ == "__main__":
    test_download_corrected()
