import requests

from constants import BASE_URL, HEADERS

response = requests.get(BASE_URL, headers=HEADERS)

print(response)
