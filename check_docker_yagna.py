import requests
import time

url = 'http://yagna_requestor_node:3333'

resp = requests.get(url=url)
data = resp.json()
print(data)