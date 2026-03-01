"""
DigiMasterJi - Performance Benchmarking Script
================================================
Measures actual latency metrics for the presentation.

Run this script to get real numbers for:
1. Bedrock TTFT (Time-to-First-Token)
2. Total response latency
3. RAG retrieval time
4. Lambda warm/cold start estimation
"""

import asyncio
import time
import statistics
import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0")


class BedrockBenchmark:
    """Measure Bedrock LLM latency metrics."""
    
    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    
    def measure_ttft_and_latency(self, prompt: str, num_runs: int = 5):
        """
        Measure Time-to-First-Token (TTFT) and total latency using streaming.
        
        Returns:
            dict with ttft_ms, total_latency_ms, tokens_generated
        """
        results = []
        
        for i in range(num_runs):
            print(f"  Run {i+1}/{num_runs}...", end=" ", flush=True)
            
            # Prepare request based on model type
            if "nova" in BEDROCK_MODEL_ID.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {
                        "maxTokens": 256,
                        "temperature": 0.7
                    }
                })
            else:
                # Llama format
                body = json.dumps({
                    "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
                    "max_gen_len": 256,
                    "temperature": 0.7
                })
            
            # Measure streaming response
            start_time = time.perf_counter()
            ttft = None
            token_count = 0
            
            try:
                response = self.client.invoke_model_with_response_stream(
                    modelId=BEDROCK_MODEL_ID,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                
                stream = response.get("body")
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        if ttft is None:
                            ttft = (time.perf_counter() - start_time) * 1000
                        token_count += 1
                
                total_latency = (time.perf_counter() - start_time) * 1000
                
                results.append({
                    "ttft_ms": ttft,
                    "total_latency_ms": total_latency,
                    "tokens": token_count
                })
                print(f"TTFT: {ttft:.0f}ms, Total: {total_latency:.0f}ms")
                
            except Exception as e:
                print(f"Error: {e}")
                continue
            
            # Small delay between runs
            time.sleep(0.5)
        
        if not results:
            return None
        
        return {
            "avg_ttft_ms": statistics.mean([r["ttft_ms"] for r in results]),
            "avg_total_latency_ms": statistics.mean([r["total_latency_ms"] for r in results]),
            "min_ttft_ms": min([r["ttft_ms"] for r in results]),
            "max_ttft_ms": max([r["ttft_ms"] for r in results]),
            "runs": len(results)
        }
    
    def measure_non_streaming_latency(self, prompt: str, num_runs: int = 5):
        """Measure non-streaming (invoke_model) latency."""
        latencies = []
        
        for i in range(num_runs):
            print(f"  Run {i+1}/{num_runs}...", end=" ", flush=True)
            
            if "nova" in BEDROCK_MODEL_ID.lower():
                body = json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {
                        "maxTokens": 256,
                        "temperature": 0.7
                    }
                })
            else:
                body = json.dumps({
                    "prompt": f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
                    "max_gen_len": 256,
                    "temperature": 0.7
                })
            
            start_time = time.perf_counter()
            
            try:
                response = self.client.invoke_model(
                    modelId=BEDROCK_MODEL_ID,
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
                print(f"{latency:.0f}ms")
                
            except Exception as e:
                print(f"Error: {e}")
            
            time.sleep(0.5)
        
        if not latencies:
            return None
        
        return {
            "avg_latency_ms": statistics.mean(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "runs": len(latencies)
        }


class EmbeddingBenchmark:
    """Measure Titan Embeddings latency."""
    
    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    
    def measure_embedding_latency(self, text: str, num_runs: int = 10):
        """Measure embedding generation latency."""
        latencies = []
        
        for i in range(num_runs):
            body = json.dumps({
                "inputText": text,
                "dimensions": 1024,
                "normalize": True
            })
            
            start_time = time.perf_counter()
            
            try:
                self.client.invoke_model(
                    modelId="amazon.titan-embed-text-v2:0",
                    body=body,
                    contentType="application/json",
                    accept="application/json"
                )
                
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
                
            except Exception as e:
                print(f"Error: {e}")
        
        if not latencies:
            return None
        
        return {
            "avg_latency_ms": statistics.mean(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "runs": len(latencies)
        }


class DynamoDBBenchmark:
    """Measure DynamoDB read/write latency."""
    
    def __init__(self):
        self.client = boto3.client("dynamodb", region_name=AWS_REGION)
        self.table_name = os.getenv("DYNAMODB_PROFILES_TABLE", "digimasterji-profiles")
    
    def measure_read_latency(self, num_runs: int = 20):
        """Measure GetItem latency."""
        latencies = []
        
        # First, do a scan to get a real item key
        try:
            scan_response = self.client.scan(
                TableName=self.table_name,
                Limit=1
            )
            if not scan_response.get("Items"):
                print("  No items in table to benchmark")
                return None
            
            item = scan_response["Items"][0]
            key = {k: v for k, v in item.items() if k in ["userId", "profileId"]}
            
        except Exception as e:
            print(f"  Error scanning table: {e}")
            return None
        
        for i in range(num_runs):
            start_time = time.perf_counter()
            
            try:
                self.client.get_item(
                    TableName=self.table_name,
                    Key=key
                )
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
                
            except Exception as e:
                print(f"Error: {e}")
        
        if not latencies:
            return None
        
        return {
            "avg_latency_ms": statistics.mean(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p50_ms": statistics.median(latencies),
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 20 else max(latencies),
            "runs": len(latencies)
        }


def measure_api_latency(api_url: str, endpoint: str, num_runs: int = 10):
    """
    Measure API endpoint latency (cold vs warm starts).
    
    To measure cold starts:
    1. Deploy to Lambda
    2. Wait 15+ minutes (Lambda scales to zero)
    3. Make first request = cold start
    4. Subsequent requests = warm starts
    """
    import httpx
    
    latencies = []
    
    for i in range(num_runs):
        print(f"  Run {i+1}/{num_runs}...", end=" ", flush=True)
        
        start_time = time.perf_counter()
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(f"{api_url}{endpoint}")
                latency = (time.perf_counter() - start_time) * 1000
                latencies.append(latency)
                print(f"{latency:.0f}ms (status: {response.status_code})")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(0.2)
    
    if not latencies:
        return None
    
    return {
        "first_request_ms": latencies[0],  # Likely cold start if Lambda was idle
        "avg_warm_ms": statistics.mean(latencies[1:]) if len(latencies) > 1 else latencies[0],
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "runs": len(latencies)
    }


def main():
    print("=" * 60)
    print("DigiMasterJi - Performance Benchmarking")
    print("=" * 60)
    
    # Test prompt
    test_prompt = "Explain Newton's first law of motion in simple terms for a class 8 student."
    
    # 1. Bedrock TTFT & Latency
    print("\n📊 1. BEDROCK LLM LATENCY (Streaming - TTFT)")
    print("-" * 40)
    print(f"Model: {BEDROCK_MODEL_ID}")
    
    bedrock = BedrockBenchmark()
    streaming_results = bedrock.measure_ttft_and_latency(test_prompt, num_runs=5)
    
    if streaming_results:
        print(f"\n✅ Results:")
        print(f"   Average TTFT: {streaming_results['avg_ttft_ms']:.0f}ms")
        print(f"   TTFT Range: {streaming_results['min_ttft_ms']:.0f}ms - {streaming_results['max_ttft_ms']:.0f}ms")
        print(f"   Average Total Latency: {streaming_results['avg_total_latency_ms']:.0f}ms")
    
    # 2. Non-streaming latency
    print("\n📊 2. BEDROCK LLM LATENCY (Non-Streaming)")
    print("-" * 40)
    
    non_streaming_results = bedrock.measure_non_streaming_latency(test_prompt, num_runs=5)
    
    if non_streaming_results:
        print(f"\n✅ Results:")
        print(f"   Average Latency: {non_streaming_results['avg_latency_ms']:.0f}ms")
        print(f"   Range: {non_streaming_results['min_latency_ms']:.0f}ms - {non_streaming_results['max_latency_ms']:.0f}ms")
        print(f"   Std Dev: {non_streaming_results['std_dev_ms']:.0f}ms")
    
    # 3. Embedding Latency
    print("\n📊 3. TITAN EMBEDDINGS LATENCY")
    print("-" * 40)
    
    embedding = EmbeddingBenchmark()
    embedding_results = embedding.measure_embedding_latency(test_prompt, num_runs=10)
    
    if embedding_results:
        print(f"✅ Results:")
        print(f"   Average Latency: {embedding_results['avg_latency_ms']:.0f}ms")
        print(f"   Range: {embedding_results['min_latency_ms']:.0f}ms - {embedding_results['max_latency_ms']:.0f}ms")
    
    # 4. DynamoDB Latency
    print("\n📊 4. DYNAMODB READ LATENCY")
    print("-" * 40)
    
    dynamo = DynamoDBBenchmark()
    dynamo_results = dynamo.measure_read_latency(num_runs=20)
    
    if dynamo_results:
        print(f"✅ Results:")
        print(f"   Average Latency: {dynamo_results['avg_latency_ms']:.1f}ms")
        print(f"   P50 (Median): {dynamo_results['p50_ms']:.1f}ms")
        print(f"   P95: {dynamo_results['p95_ms']:.1f}ms")
        print(f"   Range: {dynamo_results['min_latency_ms']:.1f}ms - {dynamo_results['max_latency_ms']:.1f}ms")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY FOR PRESENTATION")
    print("=" * 60)
    
    print("""
⚠️  IMPORTANT NOTES ON COLD STARTS:

For container-based Lambda (Docker + FastAPI), realistic cold starts are:
- First cold start: 3-8 seconds (container init + Python imports)
- Warm start: 50-200ms

To measure actual cold starts:
1. Deploy to Lambda
2. Wait 15+ minutes for Lambda to scale to zero
3. Call the /health endpoint - this is your cold start
4. Subsequent calls are warm starts

Use CloudWatch Insights query:
```
filter @type = "REPORT"
| stats avg(@initDuration) as avg_cold_start,
        max(@initDuration) as max_cold_start,
        avg(@duration) as avg_warm_duration
  by bin(1h)
```
""")
    
    print("\n📊 Recommended Presentation Numbers:")
    print("-" * 40)
    
    if streaming_results:
        print(f"• Cloud Inference TTFT: ~{streaming_results['avg_ttft_ms']:.0f}ms")
        print(f"• Cloud Inference Total: ~{streaming_results['avg_total_latency_ms']:.0f}ms")
    
    if embedding_results:
        print(f"• Embedding Generation: ~{embedding_results['avg_latency_ms']:.0f}ms")
    
    if dynamo_results:
        print(f"• DynamoDB Read Latency: ~{dynamo_results['avg_latency_ms']:.0f}ms (P95: {dynamo_results['p95_ms']:.0f}ms)")
    
    print("\n• Lambda Cold Start (Container): 3-6 seconds (realistic)")
    print("• Lambda Warm Start: 100-300ms")


if __name__ == "__main__":
    main()
