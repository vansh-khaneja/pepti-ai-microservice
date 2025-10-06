#!/usr/bin/env python3
"""
Test script for the new peptide info generation endpoint
"""

import requests
import json
from typing import Dict, Any

def test_peptide_info_generation():
    """Test the peptide info generation endpoint"""
    
    base_url = "http://localhost:8000/api/v1"
    
    # Test data
    test_cases = [
        {
            "peptide_name": "BPC-157",
            "requirements": "mechanism of action and research applications"
        },
        {
            "peptide_name": "TB-500",
            "requirements": "safety profile and dosage information"
        },
        {
            "peptide_name": "Thymosin Alpha-1",
            "requirements": "immunomodulatory effects"
        }
    ]
    
    print("Testing Peptide Info Generation Endpoint")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['peptide_name']}")
        print("-" * 30)
        
        try:
            # Make request to generate peptide info
            response = requests.post(
                f"{base_url}/peptide-info/generate",
                params={
                    "peptide_name": test_case["peptide_name"],
                    "requirements": test_case["requirements"]
                },
                timeout=120  # Longer timeout for complex operations
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["data"]
                
                print(f"✅ Success!")
                print(f"Source: {result['source']}")
                print(f"Accuracy Score: {result['accuracy_score']}")
                print(f"Session ID: {result['session_id']}")
                print(f"Response Length: {len(result['generated_response'])} characters")
                
                # Show first 200 characters of response
                preview = result['generated_response'][:200] + "..." if len(result['generated_response']) > 200 else result['generated_response']
                print(f"Response Preview: {preview}")
                
                # Show source URLs
                if result['source_urls']:
                    print(f"Source URLs: {len(result['source_urls'])} found")
                    for url in result['source_urls'][:3]:  # Show first 3 URLs
                        print(f"  - {url}")
                
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except requests.exceptions.ConnectionError:
            print("🔌 Connection error - make sure the server is running")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

def test_session_history():
    """Test getting session history"""
    
    base_url = "http://localhost:8000/api/v1"
    
    print("\nTesting Session History Endpoint")
    print("=" * 50)
    
    try:
        # First, get a list of sessions
        response = requests.get(f"{base_url}/peptide-info/sessions")
        
        if response.status_code == 200:
            data = response.json()
            sessions = data["data"]["sessions"]
            
            if sessions:
                session_id = sessions[0]["session_id"]
                print(f"Found {len(sessions)} sessions, testing with: {session_id}")
                
                # Get session history
                history_response = requests.get(f"{base_url}/peptide-info/sessions/{session_id}")
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    messages = history_data["data"]["messages"]
                    
                    print(f"✅ Session history retrieved!")
                    print(f"Peptide: {history_data['data']['peptide_name']}")
                    print(f"Messages: {len(messages)}")
                    
                    for msg in messages:
                        print(f"  - {msg['role']}: {msg['content'][:100]}...")
                else:
                    print(f"❌ Error getting history: {history_response.status_code}")
            else:
                print("No sessions found to test history")
        else:
            print(f"❌ Error listing sessions: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing session history: {str(e)}")

if __name__ == "__main__":
    test_peptide_info_generation()
    test_session_history()
