#!/usr/bin/env python3
"""
LLM Benchmark Tool for Educators

This script concurrently sends the same prompt to multiple LLMs and logs the responses
for analysis and comparison in an educational presentation. It uses multithreading
to make API requests in parallel, significantly reducing total execution time.
"""

import os
import json
import time
from datetime import datetime
import logging
import litellm
import google.generativeai as genai
from dotenv import load_dotenv
import argparse
import concurrent.futures

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("benchmark.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from file
with open("api-keys.txt", "r") as f:
    for line in f:
        if "=" in line:
            key, value = line.strip().split("=", 1)
            value = value.strip('"')
            os.environ[key] = value
            logger.info(f"Loaded API key: {key}")

# Configure Gemini
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Configure LiteLLM to use our Google API key
os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

# Define models to test
MODELS = [
    {"name": "Sonnet 3.7 thinking", "model": "claude-3-7-sonnet-20250219", "provider": "anthropic", "temperature": 1.0},
    {"name": "ChatGPT o4 mini", "model": "gpt-4o-mini", "provider": "openai", "temperature": 0.8},
    {"name": "ChatGPT 4o", "model": "gpt-4o", "provider": "openai", "temperature": 0.8},
    {"name": "ChatGPT 4.5 preview", "model": "gpt-4.5-preview", "provider": "openai", "temperature": 0.8},
    {"name": "ChatGPT o1", "model": "gpt-4-0125-preview", "provider": "openai", "temperature": 0.8},
    {"name": "Gemini 2.5 Pro Preview", "model": "gemini-2.5-pro-preview-05-06", "provider": "gemini", "temperature": 0.8},
    {"name": "Gemini 2.5 Flash Preview", "model": "gemini-2.5-flash-preview-04-17", "provider": "gemini", "temperature": 0.8},
    {"name": "ChatGPT 4.1", "model": "gpt-4.1", "provider": "openai", "temperature": 0.8},
]

class LLMBenchmark:
    def __init__(self, prompt_file="prompt", output_dir="results"):
        """Initialize the benchmark tool.
        
        Args:
            prompt_file: Path to the file containing the prompt text
            output_dir: Directory where results will be saved
        """
        self.prompt_file = prompt_file
        self.output_dir = output_dir
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
        
        # Load prompt
        with open(prompt_file, "r") as f:
            self.prompt = f.read().strip()
        logger.info(f"Loaded prompt from {prompt_file}")
        logger.debug(f"Prompt content: {self.prompt}")
    
    def query_model(self, model_config):
        """Query a specific model with the prompt and return the response."""
        model_name = model_config["name"]
        model = model_config["model"]
        provider = model_config["provider"]
        temperature = model_config["temperature"]
        
        logger.info(f"Querying model: {model_name} ({model})")
        logger.info(f"Provider: {provider}, Temperature: {temperature}")
        
        start_time = time.time()
        try:
            response_text = ""
            token_usage = {}
            
            # Use appropriate method based on provider
            if provider == "gemini":
                # Use litellm for Gemini models
                logger.info(f"Using litellm for Gemini model {model_name}")
                full_model_id = f"gemini/{model}"
                logger.info(f"LiteLLM ID: {full_model_id}")
                
                response = litellm.completion(
                    model=full_model_id,
                    messages=[{"role": "user", "content": self.prompt}],
                    temperature=temperature
                )
                
                response_text = response.choices[0].message.content
                
                # Get token usage if available
                prompt_tokens = getattr(response.usage, "prompt_tokens", -1)
                completion_tokens = getattr(response.usage, "completion_tokens", -1)
                total_tokens = getattr(response.usage, "total_tokens", -1)
                
                token_usage = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
            else:
                # Use litellm for other providers
                logger.info(f"Using litellm for {model_name}")
                # Construct model string with provider for proper litellm handling
                model_string = f"{provider}/{model}" if provider else model
                
                # Add thinking parameter for Claude 3.7 Sonnet
                if model == "claude-3-7-sonnet-20250219":
                    response = litellm.completion(
                        model=model_string,
                        messages=[{"role": "user", "content": self.prompt}],
                        temperature=temperature,
                        thinking={"type": "enabled", "budget_tokens": 4000}
                    )
                else:
                    response = litellm.completion(
                        model=model_string,
                        messages=[{"role": "user", "content": self.prompt}],
                        temperature=temperature
                    )
                response_text = response.choices[0].message.content
                token_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            end_time = time.time()
            response_time = end_time - start_time
            
            logger.info(f"Response received from {model_name} in {response_time:.2f} seconds")
            if token_usage.get("total_tokens", -1) != -1:
                logger.info(f"Token usage: {token_usage}")
            logger.debug(f"Response content: {response_text[:100]}...")
            
            return {
                "success": True,
                "response": response_text,
                "response_time": response_time,
                "token_usage": token_usage,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error querying {model_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_benchmark(self, max_workers=None):
        """Run the benchmark on all models concurrently.
        
        Args:
            max_workers: Maximum number of worker threads. Default is None (uses ThreadPoolExecutor default).
        """
        logger.info("Starting benchmark run with concurrent execution")
        
        # Create a mapping to store futures and their corresponding model configs
        futures_to_models = {}
        
        # Use ThreadPoolExecutor for concurrent API calls (I/O bound)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all model queries to the executor
            for model_config in MODELS:
                model_name = model_config["name"]
                logger.info(f"Submitting query for model: {model_name}")
                
                # Submit the task to the executor
                future = executor.submit(self.query_model, model_config)
                futures_to_models[future] = model_config
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(futures_to_models):
                model_config = futures_to_models[future]
                model_name = model_config["name"]
                
                try:
                    # Get the result from the future
                    result = future.result()
                    logger.info(f"Received result for model: {model_name}")
                    
                    # Store the result
                    self.results[model_name] = result
                    
                    # Save individual result
                    self.save_result(model_name, result)
                except Exception as e:
                    logger.error(f"Error processing result for {model_name}: {str(e)}")
                    self.results[model_name] = {
                        "success": False,
                        "error": f"Error during concurrent execution: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
        
        # Save all results
        self.save_all_results()
        logger.info("Benchmark completed")
    
    def save_result(self, model_name, result):
        """Save result for a specific model."""
        sanitized_name = model_name.replace(" ", "_").lower()
        filename = f"{self.output_dir}/{self.timestamp}_{sanitized_name}.json"
        
        with open(filename, "w") as f:
            json.dump({
                "model": model_name,
                "prompt": self.prompt,
                "result": result
            }, f, indent=2)
        
        logger.info(f"Saved result for {model_name} to {filename}")
    
    def save_all_results(self):
        """Save all results to a single file."""
        filename = f"{self.output_dir}/{self.timestamp}_all_results.json"
        
        with open(filename, "w") as f:
            json.dump({
                "timestamp": self.timestamp,
                "prompt": self.prompt,
                "results": self.results
            }, f, indent=2)
        
        logger.info(f"Saved all results to {filename}")

def main():
    """Main function to run the benchmark."""
    parser = argparse.ArgumentParser(description="LLM Benchmark Tool for Educators")
    parser.add_argument("--prompt", default="prompt", help="Path to the prompt file")
    parser.add_argument("--output", default="results", help="Output directory for results")
    parser.add_argument("--workers", type=int, default=None, 
                        help="Maximum number of concurrent workers (default: based on system resources)")
    args = parser.parse_args()
    
    logger.info("LLM Benchmark Tool starting")
    benchmark = LLMBenchmark(prompt_file=args.prompt, output_dir=args.output)
    benchmark.run_benchmark(max_workers=args.workers)
    logger.info("LLM Benchmark Tool completed")

if __name__ == "__main__":
    main()