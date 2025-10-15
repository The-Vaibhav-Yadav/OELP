#!/usr/bin/env python3
"""
Test the corrected URL patterns for GATE PDFs
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from download_gate_pdfs import get_pdf_url_patterns
import requests

def test_url_patterns():
    """Test specific URLs that we know should work"""
    test_cases = [
        # Known working URLs from user examples
        ("AG", 2022, "https://gate2026.iitg.ac.in/doc/download/2022/ag_2022.pdf"),
        ("CH", 2021, "https://gate2026.iitg.ac.in/doc/download/2021/ch_2021.pdf"),
        ("EE", 2023, "https://gate2026.iitg.ac.in/doc/download/2023/ee_2023.pdf"),
        ("CS", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/CS224S6.pdf"),
    ]
    
    print("🔍 Testing corrected URL patterns...")
    print("=" * 60)
    
    for stream, year, expected_url in test_cases:
        print(f"\n📋 Testing {stream} {year}")
        patterns = get_pdf_url_patterns(year, stream)
        
        print(f"  Generated patterns: {patterns}")
        print(f"  Expected URL: {expected_url}")
        
        if expected_url in patterns:
            print("  ✅ Expected URL found in patterns!")
        else:
            print("  ❌ Expected URL NOT found in patterns!")
        
        # Test if any of the patterns actually work
        working_pattern = None
        for url in patterns:
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    working_pattern = url
                    break
            except:
                pass
        
        if working_pattern:
            print(f"  ✅ Working pattern: {working_pattern}")
        else:
            print("  ❌ No working patterns found")

if __name__ == "__main__":
    test_url_patterns()
