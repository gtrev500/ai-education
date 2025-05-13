# This repository hosts resources used for my presentation on LLMs applicability in education. 

View the slides for my presentation: [Generative Technology in Education](https://docs.google.com/presentation/d/1FAtgiLnpyb29fqCMSk-FK_RxCMZzAm6uZJWdD1ysDqI/edit?usp=sharing)

## Links: 
- [Results from prompt runs](https://gtrev500.github.io/ai-education/rendered_results/index.html)
> [![Sample Prompt Responses](https://github.com/user-attachments/assets/77a83190-b430-4b56-9d08-50cb3f940a75)](https://gtrev500.github.io/ai-education/rendered_results/20250512_234638/index.html)
- Cursor demo PoC pending until I get consent to publish the course content publicly

## Python Scripts

Two Python scripts are included to benchmark LLMs and render the results:
```
# Setup
pip install -r requirements.txt
nvim src/api-keys.txt  # Add your API keys (might need to move it to root dir - oops)

# Run benchmark
python src/benchmark.py --prompt your_prompt_file

# Render results as HTML
python src/render_results.py
```
