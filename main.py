import textwrap
import chromadb
import numpy as np
import pandas as pd
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai


client = genai.Client()

DOCUMENT1 = """
  Operating the Climate Control System  Your Googlecar has a climate control
  system that allows you to adjust the temperature and airflow in the car.
  To operate the climate control system, use the buttons and knobs located on
  the center console.  Temperature: The temperature knob controls the
  temperature inside the car. Turn the knob clockwise to increase the
  temperature or counterclockwise to decrease the temperature.
  Airflow: The airflow knob controls the amount of airflow inside the car.
  Turn the knob clockwise to increase the airflow or counterclockwise to
  decrease the airflow. Fan speed: The fan speed knob controls the speed
  of the fan. Turn the knob clockwise to increase the fan speed or
  counterclockwise to decrease the fan speed.
  Mode: The mode button allows you to select the desired mode. The available
  modes are: Auto: The car will automatically adjust the temperature and
  airflow to maintain a comfortable level.
  Cool: The car will blow cool air into the car.
  Heat: The car will blow warm air into the car.
  Defrost: The car will blow warm air onto the windshield to defrost it.
"""
DOCUMENT2 = """
  Your Googlecar has a large touchscreen display that provides access to a
  variety of features, including navigation, entertainment, and climate
  control. To use the touchscreen display, simply touch the desired icon.
  For example, you can touch the \"Navigation\" icon to get directions to
  your destination or touch the \"Music\" icon to play your favorite songs.
"""
DOCUMENT3 = """
  Shifting Gears Your Googlecar has an automatic transmission. To
  shift gears, simply move the shift lever to the desired position.
  Park: This position is used when you are parked. The wheels are locked
  and the car cannot move.
  Reverse: This position is used to back up.
  Neutral: This position is used when you are stopped at a light or in traffic.
  The car is not in gear and will not move unless you press the gas pedal.
  Drive: This position is used to drive forward.
  Low: This position is used for driving in snow or other slippery conditions.
"""

documents = [DOCUMENT1, DOCUMENT2, DOCUMENT3]

from google.genai import types

class GeminiEmbeddingFunction(EmbeddingFunction):
  def __call__(self, input: Documents) -> Embeddings:
    EMBEDDING_MODEL_ID = "gemini-embedding-001"  # @param ["gemini-embedding-001", "text-embedding-004"] {"allow-input": true, "isTemplate": true}
    title = "Custom query"
    response = client.models.embed_content(
        model=EMBEDDING_MODEL_ID,
        contents=input,
        config=types.EmbedContentConfig(
          task_type="retrieval_document",
          title=title
        )
    )

    return [embedding.values for embedding in response.embeddings]

def create_chroma_db(documents, name):
    chroma_client = chromadb.Client()
    db = chroma_client.create_collection(
        name=name,
        # embedding_function=GeminiEmbeddingFunction()
    )

    db.add(
        documents=documents,
        ids=[str(i) for i in range(len(documents))]
    )
    return db

# Set up the DB
db = create_chroma_db(documents, "google-car-db")


sample_data = db.get(include=['documents', 'embeddings'])

df = pd.DataFrame({
    "IDs": sample_data['ids'][:3],
    "Documents": sample_data['documents'][:3],
    "Embeddings": [str(emb)[:50] + "..." for emb in sample_data['embeddings'][:3]]  # Truncate embeddings
})

print(df)


def get_relevant_passage(query, db):
  passage = db.query(query_texts=[query], n_results=1)['documents'][0][0]
  return passage


passage = get_relevant_passage("touch screen features", db)

def make_prompt(query, relevant_passage):
  escaped = relevant_passage.replace("'", "").replace('"', "").replace("\n", " ")
  prompt = ("""
    You are a helpful and informative bot that answers questions using
    text from the reference passage included below.
    Be sure to respond in a complete sentence, being comprehensive,
    including all relevant background information.
    However, you are talking to a non-technical audience, so be sure to
    break down complicated concepts and strike a friendly
    and converstional tone. If the passage is irrelevant to the answer,
    you may ignore it.
    QUESTION: '{query}'
    PASSAGE: '{relevant_passage}'

    ANSWER:
  """).format(query=query, relevant_passage=escaped)

  return prompt


query = "How do you use the touchscreen in the Google car?"
prompt = make_prompt(query, passage)
print(prompt)


MODEL_ID = "gemini-2.5-flash" # @param ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-preview", "gemini-3-pro-preview"] {"allow-input":true, isTemplate: true}
answer = client.models.generate_content(
    model = MODEL_ID,
    contents = prompt
)
print("Answer:", answer.text)
