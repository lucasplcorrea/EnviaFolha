import requests

url = "http://192.168.230.253:8080/message/sendText/RH-Abecker"

payload = {
    "number": "5547988588869",
    "text": "Teste"
}
headers = {
    "apikey": "mude-me-por-uma-chave-segura",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())