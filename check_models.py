from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Scanning all available models for active status...")
all_models = [m.name for m in client.models.list()]
for m in all_models:
    model_short = m.replace("models/", "")
    try:
        res = client.models.generate_content(model=model_short, contents="say hi")
        print(f"  [WORKING] {model_short:<35} : Response: '{res.text.strip()}'")
    except Exception as e:
        # Check if it's rate limited or other errors
        err_msg = str(e)
        if "429" in err_msg:
            print(f"  [429]     {model_short:<35} : Rate limited")
        elif "404" in err_msg or "400" in err_msg:
            pass # Skip retired or unsupported models
        else:
            print(f"  [ERROR]   {model_short:<35} : {err_msg[:60]}")