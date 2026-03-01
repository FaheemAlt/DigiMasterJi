"""
Lambda Cold Start Measurement Script
=====================================
Measures actual cold start times by invoking Lambda after idle period.

Usage:
1. Deploy your Lambda function
2. Wait 15+ minutes (or scale to zero manually)
3. Run this script to measure cold vs warm starts
"""

import boto3
import time
import json
import statistics
import os
from datetime import datetime, timedelta

# Configuration
LAMBDA_FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "digimasterji-backend-dev")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "")  # e.g., https://xxx.execute-api.us-east-1.amazonaws.com
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


def measure_cold_start_via_lambda():
    """
    Directly invoke Lambda to measure cold start.
    Uses provisioned concurrency = 0 to ensure cold start.
    """
    lambda_client = boto3.client("lambda", region_name=AWS_REGION)
    
    print("=" * 60)
    print("LAMBDA COLD START MEASUREMENT")
    print("=" * 60)
    
    # Test payload (health check)
    payload = {
        "httpMethod": "GET",
        "path": "/health",
        "headers": {},
        "queryStringParameters": None,
        "body": None
    }
    
    print("\n⏳ Measuring cold start (first invocation after idle)...")
    print("   Note: For accurate cold start, Lambda should be idle for 15+ min\n")
    
    results = []
    
    for i in range(10):
        run_type = "COLD" if i == 0 else "WARM"
        print(f"Run {i+1}/10 ({run_type})...", end=" ", flush=True)
        
        start_time = time.perf_counter()
        
        try:
            response = lambda_client.invoke(
                FunctionName=LAMBDA_FUNCTION_NAME,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload)
            )
            
            latency = (time.perf_counter() - start_time) * 1000
            
            # Check for errors
            if response.get("FunctionError"):
                print(f"Error: {response.get('FunctionError')}")
                continue
            
            results.append({
                "run": i + 1,
                "type": run_type,
                "latency_ms": latency
            })
            
            print(f"{latency:.0f}ms")
            
        except Exception as e:
            print(f"Error: {e}")
        
        # Small delay between warm invocations
        if i > 0:
            time.sleep(0.5)
    
    if results:
        cold_start = results[0]["latency_ms"] if results else 0
        warm_starts = [r["latency_ms"] for r in results[1:]]
        
        print("\n" + "-" * 40)
        print("📊 RESULTS:")
        print(f"   Cold Start (first run): {cold_start:.0f}ms")
        
        if warm_starts:
            print(f"   Warm Start Average: {statistics.mean(warm_starts):.0f}ms")
            print(f"   Warm Start Range: {min(warm_starts):.0f}ms - {max(warm_starts):.0f}ms")


def get_cloudwatch_cold_starts():
    """
    Query CloudWatch Logs for actual Lambda cold start metrics.
    """
    logs_client = boto3.client("logs", region_name=AWS_REGION)
    
    log_group = f"/aws/lambda/{LAMBDA_FUNCTION_NAME}"
    
    print("\n" + "=" * 60)
    print("CLOUDWATCH COLD START ANALYSIS")
    print("=" * 60)
    print(f"Log Group: {log_group}\n")
    
    # Query for REPORT logs with Init Duration (indicates cold start)
    query = """
    filter @type = "REPORT"
    | fields @timestamp, @duration, @initDuration, @maxMemoryUsed, @memorySize
    | filter ispresent(@initDuration)
    | sort @timestamp desc
    | limit 50
    """
    
    try:
        # Start query
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        
        response = logs_client.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )
        
        query_id = response["queryId"]
        
        # Wait for query to complete
        print("Running CloudWatch Insights query...")
        while True:
            result = logs_client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                break
            elif result["status"] == "Failed":
                print("Query failed")
                return
            time.sleep(1)
        
        results = result["results"]
        
        if not results:
            print("No cold starts found in the last 7 days")
            return
        
        # Parse results
        cold_starts = []
        warm_durations = []
        
        for row in results:
            row_dict = {field["field"]: field["value"] for field in row}
            
            init_duration = float(row_dict.get("@initDuration", 0))
            duration = float(row_dict.get("@duration", 0))
            
            if init_duration > 0:
                cold_starts.append(init_duration)
                warm_durations.append(duration)
        
        print(f"\n📊 COLD START STATISTICS (last 7 days, {len(cold_starts)} samples):")
        print("-" * 40)
        
        if cold_starts:
            print(f"   Average Init Duration: {statistics.mean(cold_starts):.0f}ms")
            print(f"   Min Init Duration: {min(cold_starts):.0f}ms")
            print(f"   Max Init Duration: {max(cold_starts):.0f}ms")
            print(f"   Median Init Duration: {statistics.median(cold_starts):.0f}ms")
            
            if len(cold_starts) > 1:
                print(f"   Std Dev: {statistics.stdev(cold_starts):.0f}ms")
            
            print(f"\n   Average Handler Duration: {statistics.mean(warm_durations):.0f}ms")
            print(f"   Total Cold Start = Init + Handler: {statistics.mean(cold_starts) + statistics.mean(warm_durations):.0f}ms")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group {log_group} not found. Lambda may not have been invoked yet.")
    except Exception as e:
        print(f"Error querying CloudWatch: {e}")


def get_all_lambda_metrics():
    """
    Get Lambda metrics from CloudWatch Metrics.
    """
    cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)
    
    print("\n" + "=" * 60)
    print("LAMBDA CLOUDWATCH METRICS")
    print("=" * 60)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)
    
    metrics = [
        ("Duration", "Average"),
        ("Duration", "Maximum"),
        ("Duration", "p99"),
        ("Invocations", "Sum"),
        ("Errors", "Sum"),
        ("ConcurrentExecutions", "Maximum"),
    ]
    
    for metric_name, stat in metrics:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName=metric_name,
                Dimensions=[
                    {"Name": "FunctionName", "Value": LAMBDA_FUNCTION_NAME}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=604800,  # 7 days
                Statistics=[stat] if stat != "p99" else [],
                ExtendedStatistics=["p99"] if stat == "p99" else []
            )
            
            datapoints = response.get("Datapoints", [])
            if datapoints:
                if stat == "p99":
                    value = datapoints[0].get("ExtendedStatistics", {}).get("p99", 0)
                else:
                    value = datapoints[0].get(stat, 0)
                
                unit = "ms" if metric_name == "Duration" else ""
                print(f"   {metric_name} ({stat}): {value:.2f}{unit}")
            
        except Exception as e:
            print(f"   {metric_name}: Error - {e}")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║         DigiMasterJi - Lambda Cold Start Analyzer            ║
╚══════════════════════════════════════════════════════════════╝

This script helps you measure ACTUAL cold start times for your
Lambda function deployed as a container image.

IMPORTANT: Container-based Lambda cold starts include:
  1. Container image pull (cached after first pull)
  2. Container initialization
  3. Python runtime startup
  4. Dependency imports (FastAPI, boto3, etc.)
  5. Application initialization

Typical cold start for FastAPI + Docker: 2-6 seconds
Warm start: 50-200ms
""")
    
    # Method 1: CloudWatch Logs Analysis (most accurate)
    get_cloudwatch_cold_starts()
    
    # Method 2: CloudWatch Metrics
    get_all_lambda_metrics()
    
    # Method 3: Direct invocation (requires Lambda to be idle)
    print("\n" + "-" * 60)
    print("💡 To measure fresh cold start:")
    print("   1. Don't invoke Lambda for 15+ minutes")
    print("   2. Run: python measure_cold_start.py --invoke")
    print("-" * 60)
    
    import sys
    if "--invoke" in sys.argv:
        measure_cold_start_via_lambda()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                  RECOMMENDED PRESENTATION NUMBERS            ║
╠══════════════════════════════════════════════════════════════╣
║  ❌ "Cold start below 200ms" - NOT realistic for containers  ║
║                                                              ║
║  ✅ More accurate claims:                                    ║
║     • Lambda Cold Start: 2-5 seconds (container init)        ║
║     • Lambda Warm Start: 100-300ms                           ║
║     • Or use "Warm response times under 300ms"               ║
║                                                              ║
║  💡 Optimization strategies you CAN mention:                 ║
║     • Provisioned Concurrency (eliminates cold starts)       ║
║     • Lambda SnapStart (not for containers yet)              ║
║     • Keep-warm with CloudWatch Events                       ║
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
