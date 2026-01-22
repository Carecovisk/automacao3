from collections.abc import Generator
from ollama import chat

# Import from parent module
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from ai import PesquisaPrompt, PromptResult, Candidates

def get_candidates_ollama(prompts: list[PesquisaPrompt]):
    for prompt in prompts:
        response = chat(
            model='gemma3:4b-it-qat',
            messages=[{'role': 'user', 'content': prompt.build()}],
            format=Candidates.model_json_schema()
        )
        candidates = Candidates.model_validate_json(response.message.content)
        yield PromptResult(prompt=prompt, candidates=candidates.candidates)
