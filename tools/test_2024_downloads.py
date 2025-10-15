#!/usr/bin/env python3
"""
Test downloading a few 2024 GATE PDFs with the corrected patterns
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from download_gate_pdfs import get_pdf_url_patterns, download_file, generate_local_filename

def test_2024_downloads():
    """Test downloading a few 2024 PDFs"""
    test_downloads = [
        ("AR", 2024),
        ("AE", 2024), 
        ("AG", 2024)
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(script_dir, "test_2024_downloads")
    os.makedirs(test_dir, exist_ok=True)
    
    print("🔍 Testing 2024 downloads...")
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
            else:
                # Only try the first working pattern for testing
                continue
        
        if not success:
            print(f"  ❌ Failed to download {stream} {year}")
    
    print(f"\n📊 Test downloads completed. Check {test_dir} for files.")

if __name__ == "__main__":
    test_2024_downloads()
