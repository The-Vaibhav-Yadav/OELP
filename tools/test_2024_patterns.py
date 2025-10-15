#!/usr/bin/env python3
"""
Test the updated 2024 URL patterns with the user-provided examples
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from download_gate_pdfs import get_pdf_url_patterns
import requests

def test_2024_patterns():
    """Test the specific 2024 URLs provided by the user"""
    test_cases = [
        # User-provided 2024 URLs
        ("AR", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/AR24S1.pdf"),
        ("CS", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/CS224S6.pdf"),
        ("AE", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/AE24S5.pdf"),
        ("AG", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/AG24S5.pdf"),
        ("CE", 2024, "http://gate2026.iitg.ac.in/doc/download/2024/CE224S4.pdf"),
        ("XH", 2024, "https://gate2026.iitg.ac.in/doc/download/2024/XHC324S3.pdf"),
    ]
    
    print("🔍 Testing updated 2024 URL patterns...")
    print("=" * 80)
    
    for stream, year, expected_url in test_cases:
        print(f"\n📋 Testing {stream} {year}")
        patterns = get_pdf_url_patterns(year, stream)
        
        # Convert http to https for comparison
        expected_url_https = expected_url.replace("http://", "https://")
        
        print(f"  Expected URL: {expected_url_https}")
        
        # Check if the expected URL is in our generated patterns
        found_pattern = False
        for pattern in patterns:
            if pattern == expected_url_https:
                found_pattern = True
                print(f"  ✅ Expected URL found in patterns!")
                break
        
        if not found_pattern:
            print(f"  ❌ Expected URL NOT found in patterns!")
            print(f"  📝 Generated {len(patterns)} patterns. First few:")
            for i, pattern in enumerate(patterns[:5]):
                print(f"     {i+1}. {pattern}")
            if len(patterns) > 5:
                print(f"     ... and {len(patterns) - 5} more")
        
        # Test if the expected URL actually works
        try:
            response = requests.head(expected_url_https, timeout=10)
            if response.status_code == 200:
                print(f"  ✅ Expected URL is accessible (200)")
            else:
                print(f"  ⚠️  Expected URL returned HTTP {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error testing expected URL: {e}")

if __name__ == "__main__":
    test_2024_patterns()
