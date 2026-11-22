import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "user", "content": "Explain gross margin deterioration in simple terms."}
    ],
    max_completion_tokens=300,
)

print(response.choices[0].message.content)