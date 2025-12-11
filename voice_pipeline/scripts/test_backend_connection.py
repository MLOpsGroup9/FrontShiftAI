#!/usr/bin/env python3
"""
Test Backend Connection Script
Tests if JWT token can successfully access Cloud Run backend APIs
"""
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Get configuration
BACKEND_URL = os.getenv('VOICE_AGENT_BACKEND_URL', '').rstrip('/')
JWT_TOKEN = os.getenv('VOICE_AGENT_JWT', '')

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_test(test_name, passed, details=""):
    icon = "✅" if passed else "❌"
    print(f"{icon} {test_name}")
    if details:
        print(f"   {details}")

async def test_health_check():
    """Test 1: Health check (no auth required)"""
    print_header("Test 1: Health Check (No Auth)")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{BACKEND_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print_test("Health Check", True, f"Status: {data.get('status')}, DB: {data.get('database')}")
                return True
            else:
                print_test("Health Check", False, f"Status Code: {response.status_code}, Response: {response.text}")
                return False
    except Exception as e:
        import traceback
        print_test("Health Check", False, f"Error: {str(e)}")
        print(f"   Full error: {traceback.format_exc()}")
        return False

async def test_auth_me():
    """Test 2: Authentication endpoint"""
    print_header("Test 2: /api/auth/me (Verify Token)")

    try:
        headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{BACKEND_URL}/api/auth/me", headers=headers)

            if response.status_code == 200:
                data = response.json()
                print_test("Auth Verification", True,
                          f"User: {data.get('email')}, Company: {data.get('company')}, Role: {data.get('role')}")
                return True, data
            else:
                try:
                    error_data = response.json()
                    print_test("Auth Verification", False,
                              f"Status: {response.status_code}, Error: {error_data.get('detail')}")
                except:
                    print_test("Auth Verification", False,
                              f"Status: {response.status_code}, Response: {response.text}")
                return False, None
    except Exception as e:
        import traceback
        print_test("Auth Verification", False, f"Error: {str(e)}")
        print(f"   Full error: {traceback.format_exc()}")
        return False, None

async def test_rag_query():
    """Test 3: RAG query endpoint"""
    print_header("Test 3: /api/rag/query (RAG Tool)")

    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": "What is the PTO policy?",
            "top_k": 3
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/rag/query",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                sources = data.get('sources', [])
                print_test("RAG Query", True,
                          f"Got {len(sources)} sources, Answer length: {len(answer)} chars")
                print(f"   Preview: {answer[:100]}...")
                return True
            else:
                error_data = response.json()
                print_test("RAG Query", False,
                          f"Status: {response.status_code}, Error: {error_data.get('detail')}")
                return False
    except Exception as e:
        print_test("RAG Query", False, f"Error: {str(e)}")
        return False

async def test_pto_chat():
    """Test 4: PTO chat endpoint"""
    print_header("Test 4: /api/pto/chat (PTO Tool)")

    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": "How many PTO days do I have remaining?"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/pto/chat",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                print_test("PTO Chat", True, f"Response length: {len(response_text)} chars")
                print(f"   Preview: {response_text[:100]}...")
                return True
            else:
                error_data = response.json()
                print_test("PTO Chat", False,
                          f"Status: {response.status_code}, Error: {error_data.get('detail')}")
                return False
    except Exception as e:
        print_test("PTO Chat", False, f"Error: {str(e)}")
        return False

async def test_hr_ticket_chat():
    """Test 5: HR Ticket chat endpoint"""
    print_header("Test 5: /api/hr-tickets/chat (HR Ticket Tool)")

    try:
        headers = {
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": "I need to schedule a meeting with HR about benefits"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/hr-tickets/chat",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                ticket_created = data.get('ticket_created', False)
                print_test("HR Ticket Chat", True,
                          f"Ticket created: {ticket_created}, Response: {len(response_text)} chars")
                return True
            else:
                error_data = response.json()
                print_test("HR Ticket Chat", False,
                          f"Status: {response.status_code}, Error: {error_data.get('detail')}")
                return False
    except Exception as e:
        print_test("HR Ticket Chat", False, f"Error: {str(e)}")
        return False

async def main():
    print("\n" + "=" * 70)
    print("  VOICE AGENT BACKEND CONNECTION TEST")
    print("=" * 70)
    print(f"\n📍 Backend URL: {BACKEND_URL}")
    print(f"🔑 JWT Token: {JWT_TOKEN[:20]}...{JWT_TOKEN[-20:] if len(JWT_TOKEN) > 40 else ''}")
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not BACKEND_URL:
        print("\n❌ Error: VOICE_AGENT_BACKEND_URL not found in .env")
        sys.exit(1)

    if not JWT_TOKEN:
        print("\n❌ Error: VOICE_AGENT_JWT not found in .env")
        sys.exit(1)

    # Run all tests
    results = []

    # Test 1: Health check
    result = await test_health_check()
    results.append(("Health Check", result))

    # Test 2: Auth verification
    auth_passed, user_data = await test_auth_me()
    results.append(("Auth Verification", auth_passed))

    if not auth_passed:
        print("\n" + "=" * 70)
        print("⚠️  CRITICAL: Authentication failed!")
        print("=" * 70)
        print("\nThe JWT token is NOT valid for this backend.")
        print("\nPossible causes:")
        print("1. Token was generated with a different JWT_SECRET_KEY")
        print("2. Token has expired")
        print("3. Token format is incorrect")
        print("\nRECOMMENDATION:")
        print("Ask your teammate to generate a NEW token using Cloud Run's JWT_SECRET_KEY")
        print("Then update VOICE_AGENT_JWT in voice_pipeline/scripts/.env")
        sys.exit(1)

    # Test 3: RAG query
    result = await test_rag_query()
    results.append(("RAG Query", result))

    # Test 4: PTO chat
    result = await test_pto_chat()
    results.append(("PTO Chat", result))

    # Test 5: HR Ticket chat
    result = await test_hr_ticket_chat()
    results.append(("HR Ticket Chat", result))

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 SUCCESS! All tests passed!")
        print("Your voice agent should work correctly with this backend.")
    elif auth_passed:
        print("\n⚠️  Authentication works, but some endpoints failed.")
        print("Check the error messages above for details.")
    else:
        print("\n❌ Authentication failed. Voice agent will NOT work.")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
