#!/usr/bin/env python3
"""
Simple test script to verify ResumeRAG system functionality
"""

import requests
import json
import time
import os


def test_health_check():
    """Test the health endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data['status']}")
            print(f"   Services: {health_data['services']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_example_queries():
    """Test the example queries endpoint"""
    print("\n📝 Testing example queries...")
    try:
        response = requests.get("http://localhost:8000/examples/queries")
        if response.status_code == 200:
            examples = response.json()
            print("✅ Example queries retrieved successfully")
            print(f"   Single fact examples: {len(examples['single_fact'])}")
            print(f"   List items examples: {len(examples['list_items'])}")
            print(f"   Summary examples: {len(examples['summary'])}")
            return True
        else:
            print(f"❌ Example queries failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Example queries error: {e}")
        return False


def test_upload_and_query():
    """Test upload and query with a sample resume"""
    print("\n📄 Testing upload and query functionality...")
    
    # Create a sample resume text file for testing
    sample_resume = """
    John Doe
    Software Engineer
    Email: john.doe@email.com
    Phone: (555) 123-4567
    
    EXPERIENCE
    Senior Software Engineer at TechCorp (2020-2023)
    - Developed web applications using Python and React
    - Led a team of 5 developers
    
    Software Engineer at StartupXYZ (2018-2020)
    - Built REST APIs using FastAPI
    - Worked with machine learning models
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Technology (2014-2018)
    GPA: 3.8/4.0
    
    SKILLS
    Python, JavaScript, React, FastAPI, Machine Learning, Git
    """
    
    # Save sample resume to temporary file
    with open("sample_resume.txt", "w") as f:
        f.write(sample_resume)
    
    try:
        # Test upload
        print("   🔄 Uploading sample resume...")
        with open("sample_resume.txt", "rb") as f:
            files = {"file": ("sample_resume.txt", f, "text/plain")}
            upload_response = requests.post("http://localhost:8000/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"   Response: {upload_response.text}")
            return False
        
        upload_data = upload_response.json()
        session_id = upload_data["session_id"]
        print(f"✅ Upload successful! Session ID: {session_id}")
        print(f"   Chunks created: {upload_data['chunks_created']}")
        
        # Wait a moment for processing
        time.sleep(1)
        
        # Test queries
        test_queries = [
            ("What is the email address?", "single_fact"),
            ("What is the phone number?", "single_fact"),
            ("List all technical skills", "list_items"),
            ("What is the current job title?", "single_fact")
        ]
        
        print("\n   🔍 Testing queries...")
        successful_queries = 0
        
        for query, query_type in test_queries:
            print(f"      Query: '{query}'")
            
            query_data = {
                "query": query,
                "session_id": session_id,
                "query_type": query_type
            }
            
            query_response = requests.post(
                "http://localhost:8000/query",
                headers={"Content-Type": "application/json"},
                json=query_data
            )
            
            if query_response.status_code == 200:
                result = query_response.json()
                answer = result.get("answer")
                confidence = result.get("confidence", 0)
                
                if answer:
                    print(f"      ✅ Answer: {answer} (confidence: {confidence:.2f})")
                    successful_queries += 1
                else:
                    print(f"      ⚠️  No answer found (confidence: {confidence:.2f})")
            else:
                print(f"      ❌ Query failed: {query_response.status_code}")
        
        print(f"\n   📊 Query Results: {successful_queries}/{len(test_queries)} successful")
        
        # Clean up session
        print("   🧹 Cleaning up session...")
        delete_response = requests.delete(f"http://localhost:8000/session/{session_id}")
        if delete_response.status_code == 200:
            print("   ✅ Session cleaned up successfully")
        
        return successful_queries > 0
        
    except Exception as e:
        print(f"❌ Upload and query test error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists("sample_resume.txt"):
            os.remove("sample_resume.txt")


def main():
    """Run all tests"""
    print("🚀 ResumeRAG System Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Health Check
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Example Queries
    if test_example_queries():
        tests_passed += 1
    
    # Test 3: Upload and Query
    if test_upload_and_query():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! ResumeRAG system is working correctly.")
        print("\n🌐 Access the web interface at: http://localhost:8000/static/index.html")
        print("📚 API documentation at: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed. Check the server logs and configuration.")
        print("💡 Make sure the server is running: python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()