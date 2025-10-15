#!/usr/bin/env python3
"""
Test script to verify GATE PDF download functionality.
Downloads just a few samples to test URL patterns and functionality.

Usage:
  python tools/test_gate_download.py           # Test URL patterns
  python tools/test_gate_download.py --download # Test actual downloads
"""

import requests
import os
import sys

# Test with a few streams and years
TEST_STREAMS = ["CS", "EE", "ME", "EC", "CE"]
TEST_YEARS = [2025, 2024, 2021]

BASE_URL = "https://gate2026.iitg.ac.in/doc/download/"

def get_pdf_url_patterns(year, stream):
    """Generate URL patterns for testing."""
    patterns = []
    
    if year == 2025:
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")
    elif year in [2024, 2023, 2022]:
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}{year}.pdf")
        patterns.append(f"{BASE_URL}{year}/{stream.upper()}{year}.pdf")
    elif year == 2021:
        patterns.append(f"{BASE_URL}{year}/{stream.lower()}_{year}.pdf")
        patterns.append(f"{BASE_URL}{year}/{stream}{year}.pdf")
    
    return patterns

def test_url_patterns():
    """Test different URL patterns to understand the website structure."""
    print("🔍 Testing GATE PDF URL patterns...")
    print("=" * 60)
    
    accessible_count = 0
    total_count = 0
    
    for year in TEST_YEARS:
        print(f"\n📅 Testing Year: {year}")
        print("-" * 40)
        
        for stream in TEST_STREAMS:
            print(f"  📋 Stream: {stream}")
            
            # Try different URL patterns
            patterns = get_pdf_url_patterns(year, stream)
            
            found_working_url = False
            for url in patterns:
                try:
                    response = requests.head(url, timeout=10)
                    total_count += 1
                    
                    if response.status_code == 200:
                        content_length = response.headers.get('content-length', 'Unknown')
                        print(f"    ✅ Found: {url}")
                        print(f"       Size: {content_length} bytes")
                        accessible_count += 1
                        found_working_url = True
                        break
                    elif response.status_code == 403:
                        print(f"    🔒 Forbidden: {url}")
                    elif response.status_code == 404:
                        print(f"    ❌ Not found: {url}")
                    else:
                        print(f"    ⚠️  Status {response.status_code}: {url}")
                        
                except Exception as e:
                    print(f"    ❌ Error: {url} - {str(e)[:50]}...")
            
            if not found_working_url:
                print(f"    ❌ No working URL found for {stream} {year}")
    
    print(f"\n📊 Summary: {accessible_count}/{len(TEST_STREAMS) * len(TEST_YEARS)} stream-year combinations accessible")
    return accessible_count > 0

def test_download_samples():
    """Test downloading a few sample files."""
    print("📥 Testing sample downloads...")
    print("=" * 40)
    
    # Find accessible URLs first
    accessible_urls = []
    
    for year in TEST_YEARS:
        for stream in TEST_STREAMS:
            patterns = get_pdf_url_patterns(year, stream)
            
            for url in patterns:
                try:
                    response = requests.head(url, timeout=10)
                    if response.status_code == 200:
                        accessible_urls.append((stream, year, url))
                        break
                except:
                    continue
    
    if not accessible_urls:
        print("❌ No accessible URLs found for testing downloads")
        return False
    
    print(f"Found {len(accessible_urls)} accessible URLs")
    
    # Test downloading first 2 files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(script_dir, "test_downloads")
    os.makedirs(test_dir, exist_ok=True)
    
    success_count = 0
    
    for i, (stream, year, url) in enumerate(accessible_urls[:2]):
        print(f"\n📥 Testing download {i+1}: {stream} {year}")
        
        try:
            response = requests.get(url, timeout=30, stream=True)
            
            if response.status_code == 200:
                filename = f"TEST_GATE-{year}-{stream}-Session-1.pdf"
                filepath = os.path.join(test_dir, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = os.path.getsize(filepath)
                
                if file_size > 1000:  # At least 1KB
                    print(f"  ✅ Downloaded successfully: {file_size:,} bytes")
                    print(f"     Saved to: {filepath}")
                    success_count += 1
                else:
                    print(f"  ❌ File too small: {file_size} bytes")
                    os.remove(filepath)
            else:
                print(f"  ❌ Download failed: Status {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Download error: {e}")
    
    print(f"\n📊 Download test: {success_count}/2 files downloaded successfully")
    
    if success_count > 0:
        print(f"\n🗂️  Test files saved in: {test_dir}")
        print("🧹 Remember to delete test files when done!")
    
    return success_count > 0

def cleanup_test_files():
    """Remove test download files."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(script_dir, "test_downloads")
    
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
        print(f"🧹 Cleaned up test files from: {test_dir}")
    else:
        print("📁 No test files to clean up")

def main():
    """Main test function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--download":
            print("🧪 Running GATE download tests...\n")
            if test_url_patterns():
                test_download_samples()
            return
        elif sys.argv[1] == "--cleanup":
            cleanup_test_files()
            return
        elif sys.argv[1] == "--help":
            print("GATE Download Test Tool")
            print("Usage:")
            print("  python tools/test_gate_download.py           # Test URL patterns only")
            print("  python tools/test_gate_download.py --download # Test patterns + downloads")
            print("  python tools/test_gate_download.py --cleanup  # Remove test files")
            print("  python tools/test_gate_download.py --help     # Show this help")
            return
    
    # Default: just test URL patterns
    test_url_patterns()

if __name__ == "__main__":
    main()
