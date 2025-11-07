import requests

url = "https://api.sandbox.co.in/gst/compliance/e-way-bill/tax-payer/hsn"

headers = {"accept": "application/json"}

response = requests.get(url, headers=headers)

print(response.text)