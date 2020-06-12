import json

with open('client_secret.json') as json_file:
    data = json.load(json_file)['installed']
    client_id = data['client_id']
    client_secret = data['client_secret']
    project_id = data['project_id']

print(client_id)
print(client_secret)
print(project_id)


