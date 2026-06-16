import os
from dotenv import load_dotenv
from litellm import completion

# Load .env

load_dotenv(override=True)

print("\n===== ENVIRONMENT CHECK =====")

nvidia_key = os.getenv("NVIDIA_NIM_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

print("NVIDIA_NIM_API_KEY loaded:", bool(nvidia_key))
print("GEMINI_API_KEY loaded:", bool(gemini_key))

if nvidia_key:
    print("NVIDIA key prefix:", nvidia_key[:12])
    print("NVIDIA key length:", len(nvidia_key))
else:
    print("NVIDIA key NOT FOUND")

print("\n===== MODEL CHECK =====")

MODEL = "nvidia_nim/meta/llama-3.1-8b-instruct"
print("Model:", MODEL)

print("\n===== LITELLM TEST =====")

try:
    response = completion(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": "Reply with only the word SUCCESS"
            }
        ],
        max_tokens=20,
        temperature=0
    )

    print("\n===== SUCCESS =====")
    print(response)


except Exception as e:
    print("\n===== ERROR =====")
    print(type(e).__name__)
    print(str(e))

import traceback
traceback.print_exc()
