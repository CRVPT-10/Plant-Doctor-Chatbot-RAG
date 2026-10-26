import os
import requests

hf_token = os.environ["HF_TOKEN"]  # set HF_TOKEN in your environment
model_id = "BAAI/bge-small-en-v1.5"
texts = ["what is the eligibility for raithu bhandu"]

router_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
payload = {"inputs": texts, "options": {"wait_for_model": False}}
headers = {"Authorization": f"Bearer {hf_token}"}

print("Testing Router URL request directly...")
try:
    resp = requests.post(router_url, json=payload, headers=headers, timeout=15.0)
    print("Status code:", resp.status_code)
    print("Response:", resp.json()[:2] if resp.status_code == 200 else resp.text)
except Exception as e:
    print("Failed request:", e)
