#!/usr/bin/env python3
"""
Test script for hallucination prevention (out-of-scope detection)

Tests that the system correctly rejects questions outside the data analytics domain
and provides helpful, polite responses instead of hallucinating answers.
"""

import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

from app.graph.workflow import AnalyticsWorkflow
from app.models.state import AnalyticsState


def test_out_of_scope_detection():
    """Test that out-of-scope questions are detected and rejected"""
    
    print("=" * 80)
    print("HALLUCINATION PREVENTION TEST")
    print("=" * 80)
    print()
    
    workflow = AnalyticsWorkflow()
    
    # Test cases: questions that should be rejected
    out_of_scope_tests = [
        {
            "question": "What's the weather today?",
            "expected_topic": "weather",
            "description": "Weather question"
        },
        {
            "question": "Who won the football game last night?",
            "expected_topic": "sports",
            "description": "Sports question"
        },
        {
            "question": "Tell me about the history of France",
            "expected_topic": "history",
            "description": "History question"
        },
        {
            "question": "How do I cook pasta?",
            "expected_topic": "cooking",
            "description": "Cooking question"
        },
        {
            "question": "What's the capital of Germany?",
            "expected_topic": "geography",
            "description": "Geography question"
        },
        {
            "question": "What are the latest news headlines?",
            "expected_topic": "news",
            "description": "News question"
        }
    ]
    
    # Test cases: questions that should be accepted
    in_scope_tests = [
        {
            "question": "Show me sales trends",
            "expected_intent": "sql_query",
            "description": "Data analysis question"
        },
        {
            "question": "Detect anomalies in my dataset",
            "expected_intent": "anomaly",
            "description": "Anomaly detection question"
        },
        {
            "question": "Forecast next month's revenue",
            "expected_intent": "forecast",
            "description": "Forecasting question"
        },
        {
            "question": "What's in my uploaded data?",
            "expected_intent": "summary",
            "description": "Summary question"
        }
    ]
    
    print("🚫 Testing OUT-OF-SCOPE Detection (should be rejected)")
    print("-" * 80)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(out_of_scope_tests, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Question: \"{test['question']}\"")
        
        try:
            # Create initial state
            initial_state: AnalyticsState = {
                "question": test["question"],
                "table_names": ["user_table_breast_cancer"],  # Simulated uploaded table
                "document_ids": None,
                "session_id": "test_session",
                "conversation_history": None,
                "user_profile": {"name": "Anubhav"},
                "key_findings": None,
                "conversation_summary": None,
                "schema_context": None,
                "relevant_tables": None,
                "sql": None,
                "sql_explanation": None,
                "data": None,
                "columns": None,
                "rows": None,
                "row_count": None,
                "error": None,
                "retry_count": 0,
                "chart_spec": None,
                "summary": None,
                "anomalies": None,
                "forecast": None,
                "knowledge_graph": None,
                "sources": None,
                "execution_time_ms": None,
                "source": None,
                "intent": None
            }
            
            # Classify intent
            result_state = workflow.classify_intent_node(initial_state)
            
            intent = result_state.get("intent")
            
            if intent == "out_of_scope":
                print(f"✅ PASS: Correctly detected as out-of-scope")
                print(f"   Rejection reason: {result_state.get('error', 'N/A')}")
                passed += 1
            else:
                print(f"❌ FAIL: Incorrectly classified as '{intent}' (should be 'out_of_scope')")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 80)
    print("✅ Testing IN-SCOPE Detection (should be accepted)")
    print("-" * 80)
    
    for i, test in enumerate(in_scope_tests, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Question: \"{test['question']}\"")
        
        try:
            initial_state: AnalyticsState = {
                "question": test["question"],
                "table_names": ["user_table_breast_cancer"],
                "document_ids": None,
                "session_id": "test_session",
                "conversation_history": None,
                "user_profile": {"name": "Anubhav"},
                "key_findings": None,
                "conversation_summary": None,
                "schema_context": None,
                "relevant_tables": None,
                "sql": None,
                "sql_explanation": None,
                "data": None,
                "columns": None,
                "rows": None,
                "row_count": None,
                "error": None,
                "retry_count": 0,
                "chart_spec": None,
                "summary": None,
                "anomalies": None,
                "forecast": None,
                "knowledge_graph": None,
                "sources": None,
                "execution_time_ms": None,
                "source": None,
                "intent": None
            }
            
            result_state = workflow.classify_intent_node(initial_state)
            intent = result_state.get("intent")
            
            if intent != "out_of_scope":
                print(f"✅ PASS: Correctly classified as '{intent}'")
                passed += 1
            else:
                print(f"❌ FAIL: Incorrectly rejected as out-of-scope")
                print(f"   Rejection reason: {result_state.get('error', 'N/A')}")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    total = passed + failed
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    print()
    
    if failed == 0:
        print("🎉 All tests passed! Hallucination prevention is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the output above.")
    
    return failed == 0


def test_rejection_response():
    """Test that rejection responses are polite and helpful"""
    
    print("\n" + "=" * 80)
    print("REJECTION RESPONSE TEST")
    print("=" * 80)
    print()
    
    workflow = AnalyticsWorkflow()
    
    test_question = "What's the weather like today?"
    
    print(f"Question: \"{test_question}\"")
    print(f"Context: User has uploaded breast cancer dataset")
    print()
    
    try:
        initial_state: AnalyticsState = {
            "question": test_question,
            "table_names": ["user_table_breast_cancer"],
            "document_ids": None,
            "session_id": "test_session",
            "conversation_history": [],
            "user_profile": {"name": "Anubhav"},
            "key_findings": None,
            "conversation_summary": None,
            "schema_context": None,
            "relevant_tables": None,
            "sql": None,
            "sql_explanation": None,
            "data": None,
            "columns": None,
            "rows": None,
            "row_count": None,
            "error": None,
            "retry_count": 0,
            "chart_spec": None,
            "summary": None,
            "anomalies": None,
            "forecast": None,
            "knowledge_graph": None,
            "sources": None,
            "execution_time_ms": None,
            "source": None,
            "intent": None
        }
        
        # Classify intent
        state_after_intent = workflow.classify_intent_node(initial_state)
        
        if state_after_intent.get("intent") == "out_of_scope":
            print("✅ Detected as out-of-scope")
            
            # Generate rejection response
            state_after_greeting = workflow.handle_greeting_node(state_after_intent)
            
            response = state_after_greeting.get("summary", "")
            
            print("\nGenerated Response:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            print()
            
            # Check response quality
            checks = {
                "Mentions user name": "Anubhav" in response or "anubhav" in response.lower(),
                "Polite/apologetic": any(word in response.lower() for word in ["sorry", "apologize", "unfortunately"]),
                "Explains limitation": any(word in response.lower() for word in ["specialize", "focus", "analytics", "data"]),
                "Offers alternative": any(word in response.lower() for word in ["instead", "help", "analyze", "explore"])
            }
            
            print("Response Quality Checks:")
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"{status} {check}")
            
            all_passed = all(checks.values())
            
            if all_passed:
                print("\n🎉 Rejection response is polite and helpful!")
                return True
            else:
                print("\n⚠️  Rejection response could be improved.")
                return False
        else:
            print(f"❌ Question was not detected as out-of-scope (classified as: {state_after_intent.get('intent')})")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 Starting Hallucination Prevention Tests\n")
    
    # Test 1: Out-of-scope detection
    test1_passed = test_out_of_scope_detection()
    
    # Test 2: Rejection response quality
    test2_passed = test_rejection_response()
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if test1_passed and test2_passed:
        print("✅ All hallucination prevention tests passed!")
        print("\nThe system will now:")
        print("  • Detect questions outside data analytics domain")
        print("  • Politely reject with helpful explanations")
        print("  • Suggest analyzing uploaded data instead")
        print("  • Prevent hallucinated answers about weather, sports, etc.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please review the output above.")
        sys.exit(1)

# Made with Bob
