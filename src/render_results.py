#!/usr/bin/env python3
"""
LLM Benchmark Results Renderer

A simple script to render LLM benchmark results as HTML for easy browsing.
"""

import json
import os
import sys
import glob
import argparse
from datetime import datetime
import markdown
from jinja2 import Template


def parse_args():
    parser = argparse.ArgumentParser(description="Render LLM benchmark results as HTML")
    parser.add_argument('--results-dir', type=str, default='results', 
                        help="Directory containing JSON result files (default: 'results')")
    parser.add_argument('--output-dir', type=str, default='rendered_results',
                        help="Directory to write the rendered HTML (default: 'rendered_results')")
    parser.add_argument('--batch', type=str, default=None,
                        help="Specific timestamp batch to render (default: latest)")
    return parser.parse_args()


def create_directories(output_dir):
    """Create the output directory if it doesn't exist"""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'css'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'js'), exist_ok=True)


def write_css(output_dir):
    """Write CSS for the rendered pages"""
    css = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
    }
    header {
        margin-bottom: 2rem;
    }
    h1 {
        font-size: 2.5rem;
        border-bottom: 2px solid #eaecef;
        padding-bottom: 0.5rem;
    }
    h2 {
        font-size: 1.8rem;
        margin-top: 2rem;
    }
    h3 {
        font-size: 1.5rem;
        margin-top: 1.5rem;
    }
    .model-card {
        background-color: #f9f9f9;
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .model-header {
        border-bottom: 1px solid #e1e4e8;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .model-name {
        font-size: 1.5rem;
        font-weight: bold;
    }
    .model-metadata {
        font-size: 0.9rem;
        color: #586069;
    }
    .model-response {
        background-color: white;
        border: 1px solid #e1e4e8;
        border-radius: 5px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    code {
        font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
        font-size: 85%;
        background-color: rgba(27, 31, 35, 0.05);
        border-radius: 3px;
        padding: 0.2em 0.4em;
    }
    pre {
        background-color: #f6f8fa;
        border-radius: 5px;
        padding: 1rem;
        overflow: auto;
    }
    .prompt-box {
        background-color: #f2f8ff;
        border: 1px solid #c8e1ff;
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 2rem;
    }
    .batch-header {
        margin-bottom: 3rem;
    }
    .nav {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .nav a {
        text-decoration: none;
        padding: 0.5rem 1rem;
        background-color: #f1f1f1;
        border-radius: 5px;
        color: #333;
    }
    .nav a:hover {
        background-color: #e9e9e9;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 2rem;
    }
    th, td {
        border: 1px solid #e1e4e8;
        padding: 0.5rem;
        text-align: left;
    }
    th {
        background-color: #f6f8fa;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .token-usage {
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #586069;
    }
    """
    with open(os.path.join(output_dir, 'css', 'style.css'), 'w') as f:
        f.write(css)


def write_js(output_dir):
    """Write JavaScript for the rendered pages"""
    js = """
    document.addEventListener('DOMContentLoaded', function() {
        // Add any client-side interactions here if needed
    });
    """
    with open(os.path.join(output_dir, 'js', 'script.js'), 'w') as f:
        f.write(js)


def get_batches(results_dir):
    """Get all unique timestamp batches from the results directory"""
    all_files = glob.glob(os.path.join(results_dir, '*.json'))
    batches = {}
    
    for filepath in all_files:
        filename = os.path.basename(filepath)
        if filename.startswith('20'):
            timestamp = '_'.join(filename.split('_')[:2])
            batches[timestamp] = True
    
    return sorted(batches.keys(), reverse=True)


def render_model_response(model_response):
    """Render the model's markdown response as HTML"""
    # Check if the response is already in HTML format
    if model_response.strip().startswith('<'):
        return model_response
    
    # Otherwise, render markdown to HTML
    return markdown.markdown(model_response, extensions=['tables', 'fenced_code'])


def render_batch(batch_timestamp, results_dir, output_dir):
    """Render a specific batch of results"""
    print(f"Rendering batch: {batch_timestamp}")
    
    # Create output directories
    batch_dir = os.path.join(output_dir, batch_timestamp)
    models_dir = os.path.join(batch_dir, 'models')
    os.makedirs(batch_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    
    # Find all files for this batch
    batch_files = glob.glob(os.path.join(results_dir, f"{batch_timestamp}_*.json"))
    
    all_results_file = os.path.join(results_dir, f"{batch_timestamp}_all_results.json")
    prompt = ""
    models_data = []
    
    # Process the all_results file if it exists
    if os.path.exists(all_results_file):
        with open(all_results_file, 'r') as f:
            all_data = json.load(f)
            prompt = all_data.get('prompt', 'No prompt available')
            
            # Extract individual model results
            for model_name, result in all_data.get('results', {}).items():
                if result.get('success', False):
                    models_data.append({
                        'name': model_name,
                        'response': result.get('response', ''),
                        'response_time': round(result.get('response_time', 0), 2),
                        'token_usage': result.get('token_usage', None),
                        'timestamp': result.get('timestamp', '')
                    })
    
    # Also process individual model files
    for file_path in batch_files:
        if file_path == all_results_file:
            continue
            
        with open(file_path, 'r') as f:
            model_data = json.load(f)
            model_name = model_data.get('model', os.path.basename(file_path).replace(f"{batch_timestamp}_", "").replace(".json", ""))
            
            # If prompt is still empty, get it from the first model file
            if not prompt and 'prompt' in model_data:
                prompt = model_data.get('prompt', '')
            
            result = model_data.get('result', {})
            
            # Skip if already processed or not successful
            if not result.get('success', False):
                continue
                
            # Check if this model is already in our list
            existing = False
            for model in models_data:
                if model['name'] == model_name:
                    existing = True
                    break
                    
            if not existing:
                models_data.append({
                    'name': model_name,
                    'response': result.get('response', ''),
                    'response_time': round(result.get('response_time', 0), 2),
                    'token_usage': result.get('token_usage', None),
                    'timestamp': result.get('timestamp', '')
                })
    
    # Template for model page
    model_template = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ model_name }} - LLM Benchmark Results</title>
    <link rel="stylesheet" href="../../css/style.css">
</head>
<body>
    <div class="nav">
        <a href="../index.html">← Back to Batch</a>
        <a href="../../index.html">← Back to All Batches</a>
    </div>
    
    <header>
        <h1>{{ model_name }} Response</h1>
    </header>
    
    <div class="prompt-box">
        <h2>Prompt</h2>
        <p>{{ prompt }}</p>
    </div>
    
    <div class="model-card">
        <div class="model-header">
            <div class="model-name">{{ model_name }}</div>
            <div class="model-metadata">
                Response Time: {{ response_time }} seconds
            </div>
        </div>
        
        <div class="model-response">
            {{ rendered_response|safe }}
        </div>
        
        {% if token_usage %}
        <div class="token-usage">
            <strong>Token Usage:</strong> 
            Prompt: {{ token_usage.prompt_tokens }} | 
            Completion: {{ token_usage.completion_tokens }} | 
            Total: {{ token_usage.total_tokens }}
        </div>
        {% endif %}
    </div>
    
    <script src="../../js/script.js"></script>
</body>
</html>""")
    
    # Render individual model pages
    for model in models_data:
        model_filename = model['name'].replace(' ', '_').lower()
        model_url = f"models/{model_filename}.html"
        
        # Render the model response
        rendered_response = render_model_response(model['response'])
        
        # Render the model template
        model_html = model_template.render(
            model_name=model['name'],
            prompt=prompt,
            response_time=model['response_time'],
            rendered_response=rendered_response,
            token_usage=model['token_usage'] if 'token_usage' in model else None
        )
        
        # Write the model HTML file
        with open(os.path.join(models_dir, f"{model_filename}.html"), 'w') as f:
            f.write(model_html)
        
        # Add URL to model data
        model['url'] = model_url
    
    # Template for batch page
    batch_template = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Results - {{ timestamp }}</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header class="batch-header">
        <div class="nav">
            <a href="../index.html">← Back to Batches</a>
        </div>
        <h1>LLM Benchmark Results - {{ timestamp }}</h1>
        
        <div class="prompt-box">
            <h2>Prompt</h2>
            <p>{{ prompt }}</p>
        </div>
        
        <h2>Models Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Response Time (s)</th>
                    <th>Tokens</th>
                    <th>Details</th>
                </tr>
            </thead>
            <tbody>
                {% for model in models %}
                <tr>
                    <td>{{ model.name }}</td>
                    <td>{{ model.response_time }}</td>
                    <td>{{ model.token_usage.total_tokens if model.token_usage else 'N/A' }}</td>
                    <td><a href="{{ model.url }}">View Response</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </header>
    
    <script src="../js/script.js"></script>
</body>
</html>""")
    
    # Render the batch page
    batch_html = batch_template.render(
        timestamp=batch_timestamp,
        prompt=prompt,
        models=models_data
    )
    
    # Write the batch HTML file
    with open(os.path.join(batch_dir, "index.html"), 'w') as f:
        f.write(batch_html)
    
    return {
        'timestamp': batch_timestamp,
        'url': f"{batch_timestamp}/index.html"
    }


def main():
    args = parse_args()
    
    # Create output directories
    create_directories(args.output_dir)
    
    # Write CSS and JavaScript
    write_css(args.output_dir)
    write_js(args.output_dir)
    
    # Get batches
    batches = get_batches(args.results_dir)
    
    if not batches:
        print(f"No result batches found in {args.results_dir}")
        return
    
    # If a specific batch was requested
    if args.batch:
        if args.batch in batches:
            batches = [args.batch]
        else:
            print(f"Batch {args.batch} not found in {args.results_dir}")
            return
    
    # Render each batch
    batch_data = []
    for batch in batches:
        batch_info = render_batch(batch, args.results_dir, args.output_dir)
        batch_data.append(batch_info)
    
    # Template for index page
    index_template = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Benchmark Results</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>LLM Benchmark Results</h1>
    </header>
    
    <div class="batch-list">
        <h2>Available Batches</h2>
        <ul>
            {% for batch in batches %}
            <li><a href="{{ batch.url }}">{{ batch.timestamp }}</a></li>
            {% endfor %}
        </ul>
    </div>
    
    <script src="js/script.js"></script>
</body>
</html>""")
    
    # Render main index
    index_html = index_template.render(batches=batch_data)
    
    # Write index file
    with open(os.path.join(args.output_dir, "index.html"), 'w') as f:
        f.write(index_html)
    
    print(f"Rendered {len(batches)} batch(es) to {args.output_dir}")
    print(f"You can now open {args.output_dir}/index.html in your browser to view the results")


if __name__ == "__main__":
    main()