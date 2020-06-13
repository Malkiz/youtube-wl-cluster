import json
from googleapiclient.discovery import build

def get_api_key():
    with open('apiKey.json') as json_file:
        data = json.load(json_file)
        api_key = data['key']
    return api_key

api_key = get_api_key()
youtube = build('youtube', 'v3', developerKey=api_key)
request = youtube.videos().list(
    part="snippet,contentDetails,statistics",
    id="Ks-_Mh1QhMc"
)
response = request.execute()

print(response)

