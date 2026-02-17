#!/usr/bin/env python
"""
Quick test script to verify profile permissions
Run: python quick_test.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def get_token(username, password):
    """Get JWT token for user"""
    try:
        response = requests.post(f"{BASE_URL}/api/token/", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token obtained for {username}")
            print(f"   Role: {data.get('role', 'N/A')}")
            return data.get('access')
        else:
            print(f"❌ Failed to get token for {username}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting token: {e}")
        return None

def test_get_profile(token, profile_id, username):
    """Test getting a specific profile"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/profiles/{profile_id}/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {username} accessed profile {profile_id}")
            print(f"   Name: {data.get('name')}, Role: {data.get('role')}")
            return True
        elif response.status_code == 403:
            print(f"❌ {username} denied access to profile {profile_id}")
            print(f"   Error: {response.json().get('detail', 'Permission denied')}")
            return False
        elif response.status_code == 404:
            print(f"❌ Profile {profile_id} not found")
            return False
        else:
            print(f"❌ Unexpected status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_list_profiles(token, username):
    """Test listing profiles"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/profiles/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {username} listed profiles: {len(data)} profile(s)")
            for profile in data:
                print(f"   - ID: {profile.get('id')}, Name: {profile.get('name')}, Role: {profile.get('role')}")
            return len(data)
        else:
            print(f"❌ Failed to list profiles: {response.text}")
            return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def main():
    print_section("PROFILE PERMISSIONS TEST")
    
    # Configuration - UPDATE THESE WITH YOUR TEST USERS
    TEACHER_USERNAME = input("Enter teacher username (or press Enter for 'teacher_test'): ").strip() or "teacher_test"
    TEACHER_PASSWORD = input("Enter teacher password (or press Enter for 'test123'): ").strip() or "test123"
    
    STUDENT1_USERNAME = input("Enter student 1 username (or press Enter for 'student1_test'): ").strip() or "student1_test"
    STUDENT1_PASSWORD = input("Enter student 1 password (or press Enter for 'test123'): ").strip() or "test123"
    
    STUDENT2_USERNAME = input("Enter student 2 username (or press Enter for 'student2_test'): ").strip() or "student2_test"
    STUDENT2_PASSWORD = input("Enter student 2 password (or press Enter for 'test123'): ").strip() or "test123"
    
    # Get tokens
    print_section("STEP 1: Getting Tokens")
    teacher_token = get_token(TEACHER_USERNAME, TEACHER_PASSWORD)
    student1_token = get_token(STUDENT1_USERNAME, STUDENT1_PASSWORD)
    student2_token = get_token(STUDENT2_USERNAME, STUDENT2_PASSWORD)
    
    if not all([teacher_token, student1_token, student2_token]):
        print("\n❌ Failed to get all tokens. Please check usernames and passwords.")
        return
    
    # Test 1: List profiles
    print_section("STEP 2: List Profiles")
    print("\nTeacher listing profiles:")
    teacher_count = test_list_profiles(teacher_token, TEACHER_USERNAME)
    
    print("\nStudent 1 listing profiles:")
    student1_count = test_list_profiles(student1_token, STUDENT1_USERNAME)
    
    # Get profile IDs
    print_section("STEP 3: Get Profile IDs")
    print("\nPlease enter the profile IDs from the list above:")
    teacher_profile_id = input("Teacher profile ID: ").strip()
    student1_profile_id = input("Student 1 profile ID: ").strip()
    student2_profile_id = input("Student 2 profile ID: ").strip()
    
    if not all([teacher_profile_id, student1_profile_id, student2_profile_id]):
        print("❌ Profile IDs are required")
        return
    
    # Test 2: Teacher accessing profiles
    print_section("STEP 4: Teacher Accessing Profiles")
    print("\nTeacher accessing own profile:")
    test_get_profile(teacher_token, teacher_profile_id, TEACHER_USERNAME)
    
    print("\nTeacher accessing Student 1 profile:")
    test_get_profile(teacher_token, student1_profile_id, TEACHER_USERNAME)
    
    print("\nTeacher accessing Student 2 profile:")
    test_get_profile(teacher_token, student2_profile_id, TEACHER_USERNAME)
    
    # Test 3: Student accessing profiles
    print_section("STEP 5: Student Accessing Profiles")
    print("\nStudent 1 accessing own profile:")
    test_get_profile(student1_token, student1_profile_id, STUDENT1_USERNAME)
    
    print("\nStudent 1 accessing Teacher profile (should fail):")
    test_get_profile(student1_token, teacher_profile_id, STUDENT1_USERNAME)
    
    print("\nStudent 1 accessing Student 2 profile (should fail):")
    test_get_profile(student1_token, student2_profile_id, STUDENT1_USERNAME)
    
    # Summary
    print_section("TEST SUMMARY")
    print("\n✅ Expected Results:")
    print("  - Teacher should list ALL profiles")
    print("  - Student should list ONLY their own profile")
    print("  - Teacher should access ANY profile")
    print("  - Student should access ONLY their own profile")
    print("  - Student accessing other profiles should return 403 Forbidden")
    
    print("\n📊 Actual Results:")
    print(f"  - Teacher listed: {teacher_count} profile(s)")
    print(f"  - Student listed: {student1_count} profile(s)")
    print("\nCheck the output above to verify all tests passed!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
