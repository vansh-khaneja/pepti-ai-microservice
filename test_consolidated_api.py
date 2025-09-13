#!/usr/bin/env python3
"""
Test script for the consolidated admin dashboard API
"""
import requests
import json
import time

def test_consolidated_api():
    """Test the consolidated admin dashboard API endpoint"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/admin-dashboard"
    
    print("🧪 Testing Consolidated Admin Dashboard API")
    print(f"📍 Endpoint: {endpoint}")
    print("-" * 50)
    
    try:
        # Test the consolidated endpoint
        start_time = time.time()
        response = requests.get(endpoint, timeout=30)
        duration = time.time() - start_time
        
        print(f"⏱️  Response time: {duration:.2f} seconds")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API call successful!")
            print(f"📝 Message: {data.get('message', 'N/A')}")
            
            if 'data' in data:
                dashboard_data = data['data']
                print("\n📈 Dashboard Data Summary:")
                print(f"  - Chat restrictions: {len(dashboard_data.get('chat_restrictions', []))}")
                print(f"  - Allowed URLs: {len(dashboard_data.get('allowed_urls', []))}")
                print(f"  - Daily analytics: {len(dashboard_data.get('daily_analytics', []))}")
                print(f"  - Weekly analytics: {len(dashboard_data.get('weekly_analytics', []))}")
                print(f"  - Monthly analytics: {len(dashboard_data.get('monthly_analytics', []))}")
                
                if 'metadata' in dashboard_data:
                    metadata = dashboard_data['metadata']
                    print(f"\n⏱️  Backend fetch time: {metadata.get('fetch_time', 0):.2f} seconds")
                    print(f"🕐 Timestamp: {metadata.get('timestamp', 'N/A')}")
            else:
                print("❌ No data in response")
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_individual_endpoints():
    """Test individual endpoints for comparison"""
    base_url = "http://localhost:8000"
    endpoints = [
        "/api/v1/chat-restrictions/?skip=0&limit=100",
        "/api/v1/allowed-urls/?skip=0&limit=100", 
        "/api/v1/analytics/daily?days=7",
        "/api/v1/analytics/weekly?weeks=4"
    ]
    
    print("\n🔍 Testing Individual Endpoints for Comparison")
    print("-" * 50)
    
    total_time = 0
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            duration = time.time() - start_time
            total_time += duration
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint}: {duration:.2f}s ({response.status_code})")
            
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print(f"\n⏱️  Total time for individual calls: {total_time:.2f} seconds")

if __name__ == "__main__":
    test_consolidated_api()
    test_individual_endpoints()
