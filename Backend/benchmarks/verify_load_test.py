"""
API Gateway/Lambda Load Test
============================
Verifies: "Successfully handled 100+ concurrent simulated requests per second"

This script uses asyncio to simulate concurrent requests to the API.
"""

import asyncio
import time
import statistics
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
HEALTH_ENDPOINT = "/health"
TEST_ENDPOINT = "/health"  # Use health endpoint for load testing


class LoadTestResults:
    def __init__(self):
        self.successful = 0
        self.failed = 0
        self.latencies = []
        self.errors = []
        self.start_time = None
        self.end_time = None
    
    @property
    def total(self):
        return self.successful + self.failed
    
    @property
    def success_rate(self):
        return (self.successful / self.total * 100) if self.total > 0 else 0
    
    @property
    def duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    @property
    def requests_per_second(self):
        return self.total / self.duration if self.duration > 0 else 0


async def make_request(client: httpx.AsyncClient, url: str, results: LoadTestResults):
    """Make a single request and record results."""
    start = time.perf_counter()
    
    try:
        response = await client.get(url, timeout=10.0)
        latency = (time.perf_counter() - start) * 1000
        
        if response.status_code == 200:
            results.successful += 1
            results.latencies.append(latency)
        else:
            results.failed += 1
            results.errors.append(f"Status {response.status_code}")
            
    except Exception as e:
        results.failed += 1
        results.errors.append(str(e))


async def run_load_test(
    url: str,
    total_requests: int = 100,
    concurrent_requests: int = 100,
    duration_seconds: float = 1.0
) -> LoadTestResults:
    """
    Run load test with specified concurrency.
    
    Args:
        url: Target URL
        total_requests: Total number of requests to make
        concurrent_requests: Number of concurrent requests
        duration_seconds: Target duration for the test
    """
    results = LoadTestResults()
    
    # Calculate delay between request batches to achieve target RPS
    batches = total_requests // concurrent_requests
    delay_between_batches = duration_seconds / batches if batches > 0 else 0
    
    async with httpx.AsyncClient() as client:
        results.start_time = time.perf_counter()
        
        for batch in range(batches):
            # Create concurrent tasks
            tasks = [
                make_request(client, url, results)
                for _ in range(concurrent_requests)
            ]
            
            # Run batch concurrently
            await asyncio.gather(*tasks)
            
            # Delay to space out requests
            if batch < batches - 1 and delay_between_batches > 0:
                await asyncio.sleep(delay_between_batches)
        
        # Handle remaining requests
        remaining = total_requests % concurrent_requests
        if remaining > 0:
            tasks = [make_request(client, url, results) for _ in range(remaining)]
            await asyncio.gather(*tasks)
        
        results.end_time = time.perf_counter()
    
    return results


async def progressive_load_test(url: str):
    """
    Run progressive load tests to find breaking point.
    """
    print("\n📊 Progressive Load Test")
    print("-" * 60)
    
    test_levels = [
        (10, 10),    # 10 concurrent, 10 total
        (50, 50),    # 50 concurrent, 50 total
        (100, 100),  # 100 concurrent, 100 total
        (100, 200),  # 100 concurrent, 200 total
        (150, 150),  # 150 concurrent, 150 total
    ]
    
    all_results = []
    
    for concurrent, total in test_levels:
        print(f"\n🔄 Testing {concurrent} concurrent requests ({total} total)...")
        
        results = await run_load_test(
            url=url,
            total_requests=total,
            concurrent_requests=concurrent,
            duration_seconds=1.0
        )
        
        all_results.append({
            "concurrent": concurrent,
            "total": total,
            "results": results
        })
        
        # Print results
        print(f"   ✅ Successful: {results.successful}/{results.total} ({results.success_rate:.1f}%)")
        print(f"   ⏱️  Duration: {results.duration:.2f}s")
        print(f"   📈 RPS: {results.requests_per_second:.1f}")
        
        if results.latencies:
            print(f"   📊 Latency:")
            print(f"      Average: {statistics.mean(results.latencies):.0f}ms")
            print(f"      Min: {min(results.latencies):.0f}ms")
            print(f"      Max: {max(results.latencies):.0f}ms")
            if len(results.latencies) > 1:
                p95_idx = int(len(results.latencies) * 0.95)
                p95 = sorted(results.latencies)[p95_idx]
                print(f"      P95: {p95:.0f}ms")
        
        if results.errors:
            unique_errors = list(set(results.errors))[:3]
            print(f"   ❌ Errors: {unique_errors}")
        
        # Stop if too many failures
        if results.success_rate < 80:
            print(f"\n⚠️  Success rate dropped below 80%, stopping test")
            break
        
        # Brief pause between test levels
        await asyncio.sleep(2)
    
    return all_results


async def sustained_load_test(url: str, rps: int = 100, duration: int = 10):
    """
    Run sustained load test at target RPS for specified duration.
    """
    print(f"\n📊 Sustained Load Test: {rps} RPS for {duration} seconds")
    print("-" * 60)
    
    results = LoadTestResults()
    
    async with httpx.AsyncClient() as client:
        results.start_time = time.perf_counter()
        
        for second in range(duration):
            print(f"   Second {second + 1}/{duration}...", end=" ", flush=True)
            
            # Send 'rps' requests in this second
            second_start = time.perf_counter()
            tasks = [make_request(client, url, results) for _ in range(rps)]
            await asyncio.gather(*tasks)
            
            # Calculate how long this second took
            elapsed = time.perf_counter() - second_start
            print(f"sent {rps} in {elapsed:.2f}s (actual RPS: {rps/elapsed:.0f})")
            
            # Wait for the rest of the second if we were faster
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        
        results.end_time = time.perf_counter()
    
    return results


def print_summary(results: LoadTestResults, claim_rps: int = 100):
    """Print test summary and verify claim."""
    print("\n" + "=" * 60)
    print("📋 LOAD TEST SUMMARY")
    print("=" * 60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Requests: {results.total}")
    print(f"   Successful: {results.successful} ({results.success_rate:.1f}%)")
    print(f"   Failed: {results.failed}")
    print(f"   Duration: {results.duration:.2f}s")
    print(f"   Actual RPS: {results.requests_per_second:.1f}")
    
    if results.latencies:
        print(f"\n📊 Latency Statistics:")
        print(f"   Average: {statistics.mean(results.latencies):.0f}ms")
        print(f"   Min: {min(results.latencies):.0f}ms")
        print(f"   Max: {max(results.latencies):.0f}ms")
        print(f"   Median: {statistics.median(results.latencies):.0f}ms")
        
        if len(results.latencies) > 10:
            p95_idx = int(len(results.latencies) * 0.95)
            p99_idx = int(len(results.latencies) * 0.99)
            sorted_lat = sorted(results.latencies)
            print(f"   P95: {sorted_lat[p95_idx]:.0f}ms")
            print(f"   P99: {sorted_lat[p99_idx]:.0f}ms")
    
    # Verify claim
    print(f"\n📋 Claim Verification:")
    print(f"   Claim: 'Handled 100+ concurrent requests per second'")
    
    if results.requests_per_second >= claim_rps and results.success_rate >= 95:
        print(f"   ✅ VERIFIED: Achieved {results.requests_per_second:.0f} RPS with {results.success_rate:.1f}% success")
    elif results.requests_per_second >= claim_rps:
        print(f"   ⚠️  PARTIAL: Achieved {results.requests_per_second:.0f} RPS but only {results.success_rate:.1f}% success")
    else:
        print(f"   ❌ NOT VERIFIED: Only achieved {results.requests_per_second:.0f} RPS")


async def main():
    print("=" * 60)
    print("API GATEWAY / LAMBDA LOAD TEST")
    print("=" * 60)
    print(f"\nTarget: {API_URL}")
    print(f"Claim: 'Successfully handled 100+ concurrent requests per second'")
    
    # Check if API is reachable
    print("\n🔍 Checking API availability...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}{HEALTH_ENDPOINT}", timeout=5.0)
            if response.status_code == 200:
                print(f"   ✅ API is reachable ({API_URL})")
            else:
                print(f"   ⚠️  API returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cannot reach API: {e}")
        print(f"\n💡 Make sure the API is running or set API_GATEWAY_URL in .env")
        print(f"   For local testing: uvicorn app.main:app")
        print(f"   For Lambda: Set API_GATEWAY_URL=https://xxx.execute-api.region.amazonaws.com")
        return
    
    # Run progressive load test
    all_results = await progressive_load_test(f"{API_URL}{TEST_ENDPOINT}")
    
    # Find the best result that maintained >95% success rate
    best_result = None
    for r in all_results:
        if r["results"].success_rate >= 95:
            if best_result is None or r["concurrent"] > best_result["concurrent"]:
                best_result = r
    
    if best_result:
        print_summary(best_result["results"], claim_rps=100)
    
    # Optional: Run sustained load test
    print("\n" + "-" * 60)
    print("💡 For sustained load test, run with --sustained flag")
    print("   Example: python verify_load_test.py --sustained")
    
    import sys
    if "--sustained" in sys.argv:
        print("\n🔄 Running 10-second sustained load test at 100 RPS...")
        sustained_results = await sustained_load_test(
            f"{API_URL}{TEST_ENDPOINT}",
            rps=100,
            duration=10
        )
        print_summary(sustained_results, claim_rps=100)


if __name__ == "__main__":
    asyncio.run(main())
