import uuid
from google import genai

# Import from parent module
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from ai import BasePrompt, PesquisaPrompt, PromptResult, Candidates

client = genai.Client()

def make_prompt(prompt: BasePrompt) -> BasePrompt.PromptResult:
  """Make a single prompt request to Gemini API and return the structured result."""
  
  response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt.build(),
    config={
        "response_mime_type": "application/json",
        "response_json_schema": prompt.PromptResult.model_json_schema(),
    },
  )
  result = prompt.PromptResult.model_validate_json(response.text)
  return result

def _build_batch_request(prompt: PesquisaPrompt) -> dict:
  """Build a single batch request for Gemini API."""
  return {
    'contents': [{
      'parts': [{'text': prompt.build()}],
      'role': 'user'
    }],
    'config': {
      'response_mime_type': 'application/json',
      'response_schema': Candidates.model_json_schema()
    }
  }

def _process_inline_response(inline_response, prompt: PesquisaPrompt) -> PromptResult:
  """Process a single inline response and return PromptResult."""
  if inline_response.error:
    print(f"Error for prompt {prompt.id}: {inline_response.error}")
    return PromptResult(prompt=prompt, candidates=[])
  
  if not inline_response.response:
    print(f"No response for prompt {prompt.id}")
    return PromptResult(prompt=prompt, candidates=[])
  
  try:
    candidates = Candidates.model_validate_json(inline_response.response.text)
    print(f"Received {len(candidates.candidates)} candidates for prompt ID {prompt.id}")
    return PromptResult(prompt=prompt, candidates=candidates.candidates)
  except Exception as e:
    print(f"Error parsing response for prompt {prompt.id}: {e}")
    return PromptResult(prompt=prompt, candidates=[])

def _poll_batch_job(batch_job, poll_interval: int = 30):
  """Poll batch job until completion."""
  import time
  
  completed_states = {
    'JOB_STATE_SUCCEEDED',
    'JOB_STATE_FAILED',
    'JOB_STATE_CANCELLED',
    'JOB_STATE_EXPIRED'
  }
  
  while batch_job.state.name not in completed_states:
    print(f"Job state: {batch_job.state.name}. Waiting {poll_interval} seconds...")
    time.sleep(poll_interval)
    batch_job = client.batches.get(name=batch_job.name)
  
  print(f"Job finished with state: {batch_job.state.name}")
  return batch_job

def _yield_batch_results(batch_job, prompts: list[PesquisaPrompt]):
  """Yield results from a completed batch job."""
  if batch_job.state.name != 'JOB_STATE_SUCCEEDED':
    print(f"Batch job failed with state: {batch_job.state.name}")
    if batch_job.error:
      print(f"Error: {batch_job.error}")
    for prompt in prompts:
      yield PromptResult(prompt=prompt, candidates=[])
    return
  
  if not batch_job.dest or not batch_job.dest.inlined_responses:
    print("No inline responses found in batch job result")
    for prompt in prompts:
      yield PromptResult(prompt=prompt, candidates=[])
    return
  
  for i, inline_response in enumerate(batch_job.dest.inlined_responses):
    yield _process_inline_response(inline_response, prompts[i])


def get_candidates_gemini(prompts: list[PesquisaPrompt]):
  """
  Fetch candidates using Gemini Batch API (50% cost reduction).
  Submits all prompts as a batch job, waits for completion, then yields results.
  """
  # Create inline requests with structured output config
  inline_requests = [_build_batch_request(prompt) for prompt in prompts]
  
  # Create batch job
  print(f"Creating batch job with {len(prompts)} requests...")
  batch_job = client.batches.create(
    model="gemini-2.5-flash",
    src=inline_requests,
    config={
      'display_name': f'candidates-batch-{uuid.uuid4().hex[:8]}'
    }
  )
  
  print(f"Batch job created: {batch_job.name}")
  
  # Poll for completion
  batch_job = _poll_batch_job(batch_job)
  
  # Process and yield results
  yield from _yield_batch_results(batch_job, prompts)
