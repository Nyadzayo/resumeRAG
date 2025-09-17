#!/usr/bin/env python3
"""
Test script for form filling functionality in ResumeRAG system
"""

import requests
import json
import time
import os


def test_form_templates():
    """Test the form templates endpoint"""
    print("📋 Testing form templates...")
    try:
        response = requests.get("http://localhost:8000/form/templates")
        if response.status_code == 200:
            templates_data = response.json()
            print("✅ Form templates retrieved successfully")
            print(f"   Template categories: {len(templates_data['templates'])}")
            print(f"   Common fields: {len(templates_data['common_fields'])}")
            
            # Show some examples
            for category, fields in templates_data['templates'].items():
                if fields:
                    print(f"   {category}: {len(fields)} fields")
            return True
        else:
            print(f"❌ Form templates failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Form templates error: {e}")
        return False


def test_single_field_extraction():
    """Test single field extraction"""
    print("\n🎯 Testing single field extraction...")
    
    # Create a sample resume
    sample_resume = """
    John Smith
    Senior Software Engineer
    Email: john.smith@techcorp.com
    Phone: (555) 987-6543
    Location: San Francisco, CA
    LinkedIn: linkedin.com/in/johnsmith
    
    PROFESSIONAL EXPERIENCE
    Senior Software Engineer at TechCorp (2021-Present)
    - Lead development of web applications using React and Python
    - Manage a team of 8 engineers
    
    Software Engineer at StartupXYZ (2019-2021)
    - Built scalable APIs using FastAPI and PostgreSQL
    - Implemented machine learning models for recommendation systems
    
    EDUCATION
    Bachelor of Science in Computer Science
    Stanford University (2015-2019)
    GPA: 3.9/4.0
    
    SKILLS
    Python, JavaScript, React, Node.js, PostgreSQL, AWS, Docker, Kubernetes
    """
    
    # Save sample resume
    with open("test_resume.txt", "w") as f:
        f.write(sample_resume)
    
    try:
        # Upload resume
        print("   📤 Uploading test resume...")
        with open("test_resume.txt", "rb") as f:
            files = {"file": ("test_resume.txt", f, "text/plain")}
            upload_response = requests.post("http://localhost:8000/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            return False
        
        session_id = upload_response.json()["session_id"]
        print(f"   ✅ Upload successful! Session: {session_id}")
        
        # Test various form fields
        form_fields_to_test = [
            "First Name",
            "Last Name", 
            "Email",
            "Phone",
            "Current Job Title",
            "Current Company",
            "University",
            "Skills",
            "LinkedIn"
        ]
        
        successful_extractions = 0
        
        for field_label in form_fields_to_test:
            print(f"   🔍 Extracting: {field_label}")
            
            extract_data = {
                "field_label": field_label,
                "session_id": session_id
            }
            
            extract_response = requests.post(
                "http://localhost:8000/extract",
                headers={"Content-Type": "application/json"},
                json=extract_data
            )
            
            if extract_response.status_code == 200:
                result = extract_response.json()
                value = result.get("value")
                confidence = result.get("confidence", 0)
                field_type = result.get("field_type", "unknown")
                
                if value:
                    print(f"      ✅ {field_label}: '{value}' (confidence: {confidence:.2f}, type: {field_type})")
                    successful_extractions += 1
                else:
                    print(f"      ⚠️  {field_label}: No value found (confidence: {confidence:.2f})")
            else:
                print(f"      ❌ {field_label}: Extraction failed ({extract_response.status_code})")
        
        print(f"\n   📊 Single Field Results: {successful_extractions}/{len(form_fields_to_test)} successful")
        
        # Clean up
        requests.delete(f"http://localhost:8000/session/{session_id}")
        
        return successful_extractions > 0
        
    except Exception as e:
        print(f"❌ Single field extraction error: {e}")
        return False
    finally:
        if os.path.exists("test_resume.txt"):
            os.remove("test_resume.txt")


def test_bulk_extraction():
    """Test bulk field extraction"""
    print("\n📦 Testing bulk field extraction...")
    
    # Create a comprehensive resume
    sample_resume = """
    Sarah Johnson
    Product Manager & Data Scientist
    
    CONTACT INFORMATION
    Email: sarah.johnson@gmail.com
    Phone: +1-555-123-4567
    Address: 123 Tech Street, Seattle, WA 98101
    LinkedIn: linkedin.com/in/sarahjohnson
    GitHub: github.com/sarahj
    Portfolio: sarahjohnson.dev
    
    PROFESSIONAL EXPERIENCE
    Senior Product Manager at Microsoft (2022-Present)
    - Lead product strategy for Azure machine learning services
    - Collaborate with engineering teams across 3 time zones
    - Increased user engagement by 40% through data-driven features
    
    Data Scientist at Amazon (2020-2022)
    - Built recommendation algorithms serving 100M+ customers
    - Developed A/B testing frameworks using Python and SQL
    - Reduced model training time by 60% through optimization
    
    Software Engineer at Google (2018-2020)
    - Implemented search ranking improvements using TensorFlow
    - Mentored 5 junior engineers in machine learning best practices
    
    EDUCATION
    Master of Science in Data Science
    University of Washington (2016-2018)
    GPA: 3.8/4.0
    
    Bachelor of Science in Computer Science
    MIT (2012-2016)
    Magna Cum Laude, GPA: 3.9/4.0
    
    SKILLS
    Programming: Python, R, SQL, JavaScript, Java
    Machine Learning: TensorFlow, PyTorch, Scikit-learn, Pandas
    Cloud: AWS, Azure, Google Cloud Platform
    Tools: Docker, Kubernetes, Git, Jupyter, Tableau
    
    CERTIFICATIONS
    - AWS Certified Solutions Architect
    - Google Cloud Professional Data Engineer
    - PMP (Project Management Professional)
    """
    
    with open("comprehensive_resume.txt", "w") as f:
        f.write(sample_resume)
    
    try:
        # Upload resume
        print("   📤 Uploading comprehensive resume...")
        with open("comprehensive_resume.txt", "rb") as f:
            files = {"file": ("comprehensive_resume.txt", f, "text/plain")}
            upload_response = requests.post("http://localhost:8000/upload", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Upload failed: {upload_response.status_code}")
            return False
        
        session_id = upload_response.json()["session_id"]
        print(f"   ✅ Upload successful! Session: {session_id}")
        
        # Test bulk extraction with comprehensive field list (max 20 fields)
        bulk_fields = [
            "First Name", "Last Name", "Full Name", "Email", "Phone", 
            "Address", "City", "State", "Current Job Title", "Current Company",
            "Previous Company", "University", "Degree", "GPA", "Skills",
            "Programming Languages", "LinkedIn", "GitHub", "Portfolio",
            "Certifications"
        ]
        
        print(f"   🔄 Extracting {len(bulk_fields)} fields in bulk...")
        
        bulk_data = {
            "fields": bulk_fields,
            "session_id": session_id
        }
        
        start_time = time.time()
        bulk_response = requests.post(
            "http://localhost:8000/extract/bulk",
            headers={"Content-Type": "application/json"},
            json=bulk_data
        )
        processing_time = (time.time() - start_time) * 1000
        
        if bulk_response.status_code == 200:
            result = bulk_response.json()
            
            print(f"   ✅ Bulk extraction completed!")
            print(f"   📊 Results: {result['extracted_fields']}/{result['total_fields']} fields extracted")
            print(f"   ⏱️  Processing time: {result['processing_time_ms']:.1f}ms (client: {processing_time:.1f}ms)")
            
            # Show successful extractions
            successful_fields = [f for f in result['fields'] if f['value']]
            print(f"\n   🎯 Successfully extracted fields:")
            for field in successful_fields[:10]:  # Show first 10
                value = field['value'][:50] + "..." if len(field['value']) > 50 else field['value']
                print(f"      • {field['field_label']}: '{value}' ({field['confidence']:.2f})")
            
            if len(successful_fields) > 10:
                print(f"      ... and {len(successful_fields) - 10} more fields")
            
            # Clean up
            requests.delete(f"http://localhost:8000/session/{session_id}")
            
            return result['extracted_fields'] > 0
        else:
            print(f"❌ Bulk extraction failed: {bulk_response.status_code}")
            print(f"   Response: {bulk_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Bulk extraction error: {e}")
        return False
    finally:
        if os.path.exists("comprehensive_resume.txt"):
            os.remove("comprehensive_resume.txt")


def main():
    """Run all form filling tests"""
    print("🚀 ResumeRAG Form Filling Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Form Templates
    if test_form_templates():
        tests_passed += 1
    
    # Test 2: Single Field Extraction
    if test_single_field_extraction():
        tests_passed += 1
    
    # Test 3: Bulk Field Extraction  
    if test_bulk_extraction():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All form filling tests passed! System ready for Chrome extension!")
        print("\n🌐 New API Endpoints:")
        print("   • POST /extract - Extract single form field")
        print("   • POST /extract/bulk - Extract multiple fields at once") 
        print("   • GET /form/templates - Get form field templates")
        print("\n📱 Access the form demo at: http://localhost:8000/static/index.html")
    else:
        print("⚠️  Some tests failed. Check the server logs and configuration.")
        print("💡 Make sure the server is running with the updated code.")


if __name__ == "__main__":
    main()