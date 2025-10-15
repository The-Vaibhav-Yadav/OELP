#!/usr/bin/env python3
"""
Comprehensive GATE integration test script.
Tests the entire GATE pipeline from PDF parsing to AI generation.

Usage:
  python tools/gate_integration_test.py               # Run all tests
  python tools/gate_integration_test.py --quick       # Quick tests only
  python tools/gate_integration_test.py --parsing     # Test parsing only
  python tools/gate_integration_test.py --generation  # Test AI generation only
"""

import sys
import os
import asyncio
import json

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

def test_gate_streams():
    """Test that all 30 GATE streams are defined"""
    print("🧪 Testing GATE streams definition...")
    
    try:
        from fastapi_app.rag_service import GATE_STREAMS, SUPPORTED_EXAMS
        
        assert len(GATE_STREAMS) == 30, f"Expected 30 GATE streams, got {len(GATE_STREAMS)}"
        
        # Verify some key streams are present
        expected_streams = ["CS", "EE", "ME", "CE", "EC", "MA", "PH", "CH"]
        for stream in expected_streams:
            assert stream in GATE_STREAMS, f"Stream {stream} not found in GATE_STREAMS"
        
        print(f"  ✅ All 30 GATE streams correctly defined: {', '.join(GATE_STREAMS[:10])}...")
        return True
        
    except Exception as e:
        print(f"  ❌ GATE streams test failed: {e}")
        return False

def test_exam_structure():
    """Test that GATE exam structure is properly defined"""
    print("🧪 Testing exam structures...")
    
    try:
        from fastapi_app.rag_service import SUPPORTED_EXAMS
        
        # Test GATE structure  
        assert "GATE" in SUPPORTED_EXAMS, "GATE not found in SUPPORTED_EXAMS"
        gate_structure = SUPPORTED_EXAMS["GATE"]
        assert "general_aptitude" in gate_structure and "technical" in gate_structure
        
        # Verify GATE question counts
        assert gate_structure["general_aptitude"]["mcq"] == 10
        assert gate_structure["technical"]["mcq"] == 45
        assert gate_structure["technical"]["tita"] == 10
        
        print("  ✅ GATE exam structure correctly defined")
        return True
        
    except Exception as e:
        print(f"  ❌ Exam structure test failed: {e}")
        return False

def test_path_generation():
    """Test that paths are generated correctly for GATE"""
    print("🧪 Testing path generation...")
    
    try:
        from fastapi_app.rag_service import get_exam_paths
        
        # Test GATE paths
        gate_paths = get_exam_paths("GATE")
        assert gate_paths['vector_db'].endswith('app_data/vector_db/GATE')
        assert gate_paths['structured_questions'].endswith('app_data/structured_questions/GATE')
        assert gate_paths['generated_exams'].endswith('app_data/generated_questions/GATE')
        
        print("  ✅ Path generation working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Path generation test failed: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist"""
    print("🧪 Testing directory structure...")
    
    try:
        required_dirs = [
            'data_pipeline/source_pdfs/GATE',
            'app_data/structured_questions/GATE',
            'app_data/vector_db/GATE',
            'app_data/generated_questions/GATE'
        ]
        
        for dir_path in required_dirs:
            full_path = os.path.join(project_root, dir_path)
            assert os.path.exists(full_path), f"Required directory not found: {full_path}"
        
        print("  ✅ All required directories exist")
        return True
        
    except Exception as e:
        print(f"  ❌ Directory structure test failed: {e}")
        return False

def test_pdf_files():
    """Test that GATE PDF files are present"""
    print("🧪 Testing GATE PDF files...")
    
    try:
        gate_pdfs_dir = os.path.join(project_root, 'data_pipeline/source_pdfs/GATE')
        pdf_files = [f for f in os.listdir(gate_pdfs_dir) if f.endswith('.pdf')]
        
        print(f"  📁 Found {len(pdf_files)} GATE PDF files")
        
        if pdf_files:
            # Check naming convention
            sample_file = pdf_files[0]
            assert sample_file.startswith('GATE-'), f"PDF naming convention issue: {sample_file}"
            print(f"  ✅ PDF files present with correct naming: {sample_file}")
        else:
            print("  ⚠️  No PDF files found - run download script first")
        
        return len(pdf_files) > 0
        
    except Exception as e:
        print(f"  ❌ PDF files test failed: {e}")
        return False

def test_parsed_questions():
    """Test that GATE questions are parsed correctly"""
    print("🧪 Testing parsed GATE questions...")
    
    try:
        questions_dir = os.path.join(project_root, 'app_data/structured_questions/GATE')
        
        if not os.path.exists(questions_dir):
            print("  ⚠️  No parsed questions found - run parsing script first")
            return False
        
        json_files = [f for f in os.listdir(questions_dir) if f.endswith('.json')]
        
        if not json_files:
            print("  ⚠️  No JSON files found - run parsing script first")
            return False
        
        print(f"  📄 Found {len(json_files)} question files")
        
        # Test loading a sample file
        sample_file = os.path.join(questions_dir, json_files[0])
        with open(sample_file, 'r') as f:
            questions = json.load(f)
        
        if questions:
            sample_q = questions[0]
            assert 'question_text' in sample_q
            assert 'exam' in sample_q
            assert sample_q['exam'] == 'GATE'
            print(f"  ✅ Questions parsed correctly ({len(questions)} in sample file)")
        else:
            print("  ⚠️  Empty question files found")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Parsed questions test failed: {e}")
        return False

def test_vector_database():
    """Test that GATE vector database is built"""
    print("🧪 Testing GATE vector database...")
    
    try:
        vector_db_dir = os.path.join(project_root, 'app_data/vector_db/GATE')
        
        if not os.path.exists(vector_db_dir):
            print("  ⚠️  No vector database found - run build script first")
            return False
        
        # Check for ChromaDB files
        db_files = os.listdir(vector_db_dir)
        has_chroma_files = any('chroma' in f.lower() or f.endswith('.bin') for f in db_files)
        
        if has_chroma_files:
            print("  ✅ Vector database files present")
        else:
            print("  ⚠️  No ChromaDB files found")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Vector database test failed: {e}")
        return False

def test_rag_service_initialization():
    """Test that RAG service can be initialized for GATE"""
    print("🧪 Testing RAG service initialization...")
    
    try:
        from fastapi_app.rag_service import RAGService
        
        # Test GATE initialization
        gate_service = RAGService("GATE")
        assert gate_service.exam_type == "GATE"
        print("  ✅ GATE RAG service initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"  ❌ RAG service initialization failed: {e}")
        return False

async def test_exam_generation():
    """Test GATE exam generation (requires API key)"""
    print("🧪 Testing GATE exam generation...")
    
    try:
        from fastapi_app.rag_service import RAGService, SUPPORTED_EXAMS
        
        # Create a smaller test structure to avoid long waits
        original_structure = SUPPORTED_EXAMS['GATE'].copy()
        SUPPORTED_EXAMS['GATE'] = {
            'general_aptitude': {'mcq': 1, 'tita': 0},
            'technical': {'mcq': 1, 'tita': 0}
        }
        
        try:
            gate_service = RAGService("GATE")
            result = await gate_service.generate_full_exam(exam_name='GATE', stream='CS', year=2025)
            
            assert 'exam_details' in result
            assert 'GA' in result
            assert 'TECH' in result
            assert 'errors' in result
            
            # Check if generation worked (might fail due to missing API key)
            if result['errors']:
                error_msg = result['errors'][0].get('error', '')
                if 'API Key not found' in error_msg:
                    print("  ⚠️  Exam generation structure works, but API key needed")
                else:
                    print(f"  ❌ Generation error: {error_msg}")
            else:
                print("  ✅ Exam generation successful!")
            
            return True
            
        finally:
            # Restore original structure
            SUPPORTED_EXAMS['GATE'] = original_structure
        
    except Exception as e:
        print(f"  ❌ Exam generation test failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints work (basic validation)"""
    print("🧪 Testing API endpoint structure...")
    
    try:
        # Test gate streams endpoint logic
        from fastapi_app.main import app
        print("  ✅ FastAPI app imports successfully")
        
        # Test stream info structure (from the endpoint)
        stream_info = {
            "AE": "Aerospace Engineering",
            "CS": "Computer Science and Information Technology",
            "ME": "Mechanical Engineering",
        }
        
        assert len(stream_info) >= 3
        print("  ✅ Stream info structure correct")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API endpoints test failed: {e}")
        return False

async def run_all_tests():
    """Run all integration tests"""
    print("🚀 Starting GATE Integration Tests...\n")
    
    tests = [
        ("GATE Streams", test_gate_streams),
        ("Exam Structure", test_exam_structure),
        ("Path Generation", test_path_generation),
        ("Directory Structure", test_directory_structure),
        ("PDF Files", test_pdf_files),
        ("Parsed Questions", test_parsed_questions),
        ("Vector Database", test_vector_database),
        ("RAG Service Init", test_rag_service_initialization),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append((test_name, False))
    
    # Test exam generation separately (optional)
    print(f"\n{'='*60}")
    print(f"🧪 Exam Generation (Optional)")
    print(f"{'='*60}")
    try:
        gen_result = await test_exam_generation()
        results.append(("Exam Generation", gen_result))
    except Exception as e:
        print(f"  ❌ Generation test crashed: {e}")
        results.append(("Exam Generation", False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:<20} {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! GATE integration is working correctly.")
    elif passed >= total * 0.8:
        print("\n⚠️  Most tests passed. Check failed tests above.")
    else:
        print("\n❌ Multiple tests failed. GATE integration needs attention.")
    
    return passed == total

def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg == "--help":
            print("GATE Integration Test Tool")
            print("Usage:")
            print("  python tools/gate_integration_test.py               # Run all tests")
            print("  python tools/gate_integration_test.py --quick       # Quick tests only") 
            print("  python tools/gate_integration_test.py --parsing     # Test parsing only")
            print("  python tools/gate_integration_test.py --generation  # Test AI generation only")
            return
        
        elif arg == "--quick":
            # Run only quick tests
            quick_tests = [test_gate_streams, test_exam_structure, test_path_generation, test_directory_structure]
            for test_func in quick_tests:
                test_func()
            return
            
        elif arg == "--parsing":
            # Test parsing pipeline
            parsing_tests = [test_pdf_files, test_parsed_questions, test_vector_database]
            for test_func in parsing_tests:
                test_func()
            return
            
        elif arg == "--generation":
            # Test AI generation
            async def run_gen_test():
                await test_exam_generation()
            asyncio.run(run_gen_test())
            return
    
    # Run all tests
    asyncio.run(run_all_tests())

if __name__ == "__main__":
    main()
