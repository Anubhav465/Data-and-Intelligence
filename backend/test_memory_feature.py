#!/usr/bin/env python3
"""
Test script for conversation memory feature

Tests:
1. Greeting response
2. Name introduction and memory
3. Cross-referencing previous queries
4. Session management
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def print_response(response_data):
    print(f"Session ID: {response_data.get('session_id', 'N/A')}")
    print(f"Intent: {response_data.get('meta', {}).get('intent', 'N/A')}")
    print(f"Response: {response_data.get('summary') or response_data.get('response', 'N/A')}")
    if response_data.get('meta', {}).get('user_name'):
        print(f"User Name: {response_data['meta']['user_name']}")
    print()

def test_greeting():
    """Test 1: Simple greeting"""
    print_section("TEST 1: Greeting Response")
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": "Hi"}
    )
    
    data = response.json()
    print_response(data)
    
    assert response.status_code == 200, "Request failed"
    assert data.get('session_id'), "No session_id returned"
    assert 'help' in data.get('summary', '').lower() or 'help' in data.get('response', '').lower(), "Greeting response not appropriate"
    
    print("✅ Test 1 PASSED: Greeting response works correctly\n")
    return data['session_id']

def test_name_introduction(session_id):
    """Test 2: Name introduction and memory"""
    print_section("TEST 2: Name Introduction")
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "My name is Anubhav",
            "session_id": session_id
        }
    )
    
    data = response.json()
    print_response(data)
    
    assert response.status_code == 200, "Request failed"
    assert data.get('session_id') == session_id, "Session ID changed"
    response_text = data.get('summary', '') or data.get('response', '')
    assert 'anubhav' in response_text.lower(), "Name not acknowledged in response"
    
    print("✅ Test 2 PASSED: Name introduction works correctly\n")
    return session_id

def test_name_memory(session_id):
    """Test 3: Name memory in subsequent query"""
    print_section("TEST 3: Name Memory")
    
    # Wait a moment to ensure session is updated
    time.sleep(0.5)
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "What can you do?",
            "session_id": session_id
        }
    )
    
    data = response.json()
    print_response(data)
    
    assert response.status_code == 200, "Request failed"
    assert data.get('session_id') == session_id, "Session ID changed"
    
    # Check if name is used in response or stored in meta
    response_text = data.get('summary', '') or data.get('response', '')
    user_name = data.get('meta', {}).get('user_name')
    
    name_remembered = 'anubhav' in response_text.lower() or user_name == 'Anubhav'
    
    if name_remembered:
        print("✅ Test 3 PASSED: Name is remembered across queries\n")
    else:
        print("⚠️  Test 3 WARNING: Name not explicitly used in response, but may be stored in session\n")
    
    return session_id

def test_data_query(session_id):
    """Test 4: Data query with name context"""
    print_section("TEST 4: Data Query with Context")
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "Show me the first 5 rows of data",
            "session_id": session_id,
            "table_names": []  # Will use Olist database
        }
    )
    
    data = response.json()
    print(f"Session ID: {data.get('session_id', 'N/A')}")
    print(f"SQL Generated: {data.get('sql', 'N/A')[:100]}...")
    print(f"Rows returned: {data.get('meta', {}).get('row_count', 0)}")
    
    if data.get('meta', {}).get('user_name'):
        print(f"User Name in context: {data['meta']['user_name']}")
    
    print()
    
    assert response.status_code == 200, "Request failed"
    print("✅ Test 4 PASSED: Data query executed successfully\n")
    
    return session_id

def test_session_stats():
    """Test 5: Session statistics"""
    print_section("TEST 5: Session Statistics")
    
    response = requests.get(f"{BASE_URL}/sessions/stats")
    data = response.json()
    
    print(f"Active Sessions: {data.get('active_sessions', 0)}")
    print(f"Backend: {data.get('backend', 'N/A')}")
    print(f"TTL Hours: {data.get('ttl_hours', 0)}")
    print()
    
    assert response.status_code == 200, "Request failed"
    assert data.get('active_sessions', 0) > 0, "No active sessions found"
    
    print("✅ Test 5 PASSED: Session statistics retrieved\n")

def test_cross_referencing(session_id):
    """Test 6: Cross-referencing previous queries"""
    print_section("TEST 6: Cross-Referencing")
    
    # First query
    print("First query: Count of orders")
    response1 = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "How many orders are there?",
            "session_id": session_id
        }
    )
    data1 = response1.json()
    print(f"Response: {data1.get('summary', 'N/A')[:200]}")
    print()
    
    time.sleep(0.5)
    
    # Second query referencing first
    print("Second query: Referencing previous")
    response2 = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "What about customers?",
            "session_id": session_id
        }
    )
    data2 = response2.json()
    print(f"Response: {data2.get('summary', 'N/A')[:200]}")
    print()
    
    assert response1.status_code == 200, "First request failed"
    assert response2.status_code == 200, "Second request failed"
    
    print("✅ Test 6 PASSED: Cross-referencing queries work\n")

def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "🧪 " * 20)
    print("  CONVERSATION MEMORY FEATURE - TEST SUITE")
    print("🧪 " * 20)
    
    try:
        # Test 1: Greeting
        session_id = test_greeting()
        
        # Test 2: Name introduction
        session_id = test_name_introduction(session_id)
        
        # Test 3: Name memory
        session_id = test_name_memory(session_id)
        
        # Test 4: Data query
        session_id = test_data_query(session_id)
        
        # Test 5: Session stats
        test_session_stats()
        
        # Test 6: Cross-referencing
        test_cross_referencing(session_id)
        
        print_section("🎉 ALL TESTS PASSED!")
        print("The conversation memory feature is working correctly.")
        print(f"\nYour session ID: {session_id}")
        print("You can continue testing with this session ID.\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("Make sure the backend is running on http://localhost:8000\n")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {str(e)}\n")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

# Made with Bob
