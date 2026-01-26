from collections.abc import Hashable
from dataclasses import dataclass
import json
import random
import uuid
import re
from pydantic import BaseModel, Field

from utils.ai import BasePrompt
from utils.models.gemini import make_prompt

class Replacement(BaseModel):
  regex: str = Field(description="Regular expression pattern to match. python regex syntax")
  replacement: str = Field(description="Replacement string")

@dataclass
class PreprocessingPrompt(BasePrompt):
  id: Hashable
  sample: list[str]
  context: str

  class PromptResult(BaseModel):
    replacements: list[Replacement] = []

  def build(self) -> str:
    return f"""
    Você é um especialista em Regex e dados de varejo.
    
    CONTEXTO:
      {self.context}
    
    TAREFA:
      Crie uma lista de 'replacements' para expandir abreviações e minemonicos comuns encontrados nos dados de varejo.
    
    DADOS DE AMOSTRA:
    {json.dumps(self.sample, indent=2, ensure_ascii=False)}
    
    """


def fetch_replacements_from_llm(
    strings: list[str],
    context: str = "Dados de varejo contendo abreviações e variações"
) -> list[Replacement]:
    """
    Create a PreprocessingPrompt from a list of strings and get replacements using Gemini API.

    Args:
        strings: List of strings to analyze for common abbreviations and patterns
        context: Context description for the prompt (default: retail data context)

    Returns:
        PreprocessingPrompt.PromptResult containing a list of regex replacements
    """

    sample = random.sample(strings, min(len(strings), 50))

    prompt = PreprocessingPrompt(
        id=uuid.uuid4(),
        sample=sample,
        context=context
    )

    result = make_prompt(prompt)
    return result.replacements # type: ignore

def apply_replacements(strings: list[str], replacements: list[Replacement]) -> list[str]:
  """
  Apply regex replacements to a list of strings.
  
  Args:
    strings: List of strings to process
    replacements: List of Replacement objects with regex patterns and replacements
  
  Returns:
    List of strings with all replacements applied
  """
  result = []
  for string in strings:
    processed = string
    for replacement in replacements:
      try:
        processed = re.sub(replacement.regex, replacement.replacement, processed)
      except re.error as e:
        print(f"Invalid regex pattern '{replacement.regex}': {e}")
        continue
    result.append(processed)
  return result
