#!/usr/bin/env python3
"""
Verification test suite for the Resume Workshop App.
This script tests all core functionality without running the Streamlit UI.
"""

import sys
import os

# Prevent Streamlit warnings
sys.argv = ['streamlit', 'run', 'app.py']

import app
import io


def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    required_modules = [
        'streamlit', 'pandas', 'docxtpl', 'docx', 'pypdf', 'requests'
    ]
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            return False
    return True


def test_data_files():
    """Test that all required data files exist."""
    print("\nTesting data files...")
    required_files = [
        'Job_History_Master.docx',
        'resume_app_template.docx',
        'requirements.txt',
        'runtime.txt'
    ]
    all_found = True
    for fname in required_files:
        exists = os.path.exists(fname)
        print(f"  {'✓' if exists else '✗'} {fname}")
        if not exists:
            all_found = False
    return all_found


def test_text_parsing():
    """Test text parsing functions."""
    print("\nTesting text parsing functions...")
    
    test_text = """
John Doe
Seattle, WA
(206) 555-1234
john.doe@example.com

OSHA-10, Forklift, First Aid, CPR

Experience:
Line Cook at Restaurant ABC
Operated kitchen tools, maintained safety standards

Education:
High School Diploma, Seattle High School, 2020
"""
    
    # Test header parsing
    header = app.parse_header(test_text)
    assert header['Name'], "Name not parsed"
    assert header['Email'] == 'john.doe@example.com', f"Email incorrect: {header['Email']}"
    assert header['Phone'] == '(206) 555-1234', f"Phone incorrect: {header['Phone']}"
    assert header['City'] == 'Seattle', f"City incorrect: {header['City']}"
    assert header['State'] == 'WA', f"State incorrect: {header['State']}"
    print(f"  ✓ Header parsing")
    
    # Test certification parsing
    certs = app.parse_certs(test_text)
    assert len(certs) >= 3, f"Expected at least 3 certs, got {len(certs)}"
    print(f"  ✓ Certification parsing ({len(certs)} found)")
    
    # Test education parsing
    edu = app.parse_education(test_text)
    assert len(edu) > 0, "No education parsed"
    print(f"  ✓ Education parsing ({len(edu)} found)")
    
    # Test skills suggestion
    skills = app.suggest_transferable_skills_from_text(test_text)
    assert len(skills) > 0, "No skills suggested"
    print(f"  ✓ Skills suggestion ({len(skills)} found)")
    
    return True


def test_job_master():
    """Test Job Master parsing."""
    print("\nTesting Job Master parsing...")
    
    try:
        with open('Job_History_Master.docx', 'rb') as f:
            job_bytes = f.read()
        roles = app.cached_read_job_master(job_bytes)
        assert len(roles) > 0, "No roles parsed from Job Master"
        print(f"  ✓ Job Master parsed: {len(roles)} roles")
        
        # Verify structure
        sample_roles = list(roles.items())[:3]
        for role, bullets in sample_roles:
            assert isinstance(role, str), f"Role should be string: {type(role)}"
            assert isinstance(bullets, list), f"Bullets should be list: {type(bullets)}"
            print(f"    - {role}: {len(bullets)} bullets")
        
        return True
    except Exception as e:
        print(f"  ✗ Job Master parsing failed: {e}")
        return False


def test_document_generation():
    """Test document generation functions."""
    print("\nTesting document generation...")
    
    # Test resume generation
    try:
        with open('resume_app_template.docx', 'rb') as f:
            tpl_bytes = f.read()
        
        test_context = {
            'Name': 'John Doe',
            'City': 'Seattle',
            'State': 'WA',
            'phone': '(206) 555-1234',
            'email': 'john.doe@example.com',
            'summary': 'Seeking apprenticeship in construction trades',
            'skills': ['Safety awareness', 'Hand & power tools', 'Teamwork & collaboration'],
            'certs': ['OSHA Outreach 10-Hour (Construction)', 'WA Flagger'],
            'jobs': [{
                'company': 'ABC Restaurant',
                'role': 'Line Cook',
                'city': 'Seattle',
                'start': '2022',
                'end': 'Present',
                'bullets': ['Maintained safety standards', 'Operated kitchen equipment']
            }],
            'schools': [{
                'school': 'Seattle High School',
                'credential': 'Diploma',
                'year': '2020',
                'details': 'Seattle, WA'
            }],
            'trade_label': 'Electrician – Inside (01)'
        }
        
        resume_bytes = app.render_docx_with_template(tpl_bytes, test_context)
        assert len(resume_bytes) > 1000, f"Resume too small: {len(resume_bytes)} bytes"
        print(f"  ✓ Resume generation ({len(resume_bytes)} bytes)")
    except Exception as e:
        print(f"  ✗ Resume generation failed: {e}")
        return False
    
    # Test cover letter generation
    try:
        cover_data = {
            'name': 'John Doe',
            'city': 'Seattle',
            'state': 'WA',
            'phone': '(206) 555-1234',
            'email': 'john.doe@example.com',
            'company': 'XYZ Company',
            'role': 'Apprentice Electrician',
            'location': 'Seattle, WA',
            'trade_label': 'Electrician – Inside (01)',
            'strength': 'Reliable, Safety-focused, Coachable',
            'application_type': 'Apprenticeship'
        }
        cover_bytes = app.build_cover_letter_docx(cover_data)
        assert len(cover_bytes) > 1000, f"Cover letter too small: {len(cover_bytes)} bytes"
        print(f"  ✓ Cover letter generation ({len(cover_bytes)} bytes)")
    except Exception as e:
        print(f"  ✗ Cover letter generation failed: {e}")
        return False
    
    # Test pathway packet generation
    try:
        student = {'name': 'John Doe'}
        reflections = {
            'Objective typed by student': 'I want to be an electrician',
            'Skills (transferable)': 'Teamwork, Problem-solving'
        }
        
        packet_bytes = app.build_pathway_packet_docx(
            student, 
            'Electrician – Inside (01)', 
            'Apprenticeship', 
            [],
            reflections
        )
        assert len(packet_bytes) > 1000, f"Pathway packet too small: {len(packet_bytes)} bytes"
        print(f"  ✓ Pathway packet generation ({len(packet_bytes)} bytes)")
    except Exception as e:
        print(f"  ✗ Pathway packet generation failed: {e}")
        return False
    
    return True


def test_utility_functions():
    """Test utility functions."""
    print("\nTesting utility functions...")
    
    # Test text cleaning
    assert app.strip_banned("This is union work") == "This is  work"
    assert app.norm_ws("  multiple   spaces  ") == "multiple spaces"
    assert app.cap_first("hello world") == "Hello world"
    print("  ✓ Text cleaning functions")
    
    # Test phone cleaning
    assert app.clean_phone("2065551234") == "(206) 555-1234"
    assert app.clean_phone("(206) 555-1234") == "(206) 555-1234"
    print("  ✓ Phone cleaning")
    
    # Test email cleaning
    assert app.clean_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
    print("  ✓ Email cleaning")
    
    # Test skill normalization
    assert app.normalize_skill_label("problem solving") == "Problem-solving"
    assert app.normalize_skill_label("teamwork") == "Teamwork & collaboration"
    print("  ✓ Skill normalization")
    
    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Resume Workshop App - Verification Test Suite")
    print("=" * 60)
    
    results = {
        'Imports': test_imports(),
        'Data Files': test_data_files(),
        'Text Parsing': test_text_parsing(),
        'Job Master': test_job_master(),
        'Document Generation': test_document_generation(),
        'Utility Functions': test_utility_functions(),
    }
    
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    all_passed = all(results.values())
    
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
