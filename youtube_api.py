import json
from googleapiclient.discovery import build
import pandas as pd

def chunk_df(df, n=10):
    return [df[i:i+n] for i in range(0,df.shape[0],n)]

def get_api_key():
    with open('apiKey.json') as json_file:
        data = json.load(json_file)
        api_key = data['key']
    return api_key

wl = pd.read_csv('WL.csv')
wl_chunks = chunk_df(wl, 50)

#print(wl_chunks[0])

api_key = get_api_key()
youtube = build('youtube', 'v3', developerKey=api_key)
data = [youtube.videos().list(
    part="snippet,contentDetails,statistics",
    id=','.join(wl_chunks[i]['id'])
).execute() for i in range(0, len(wl_chunks))]

print(data)

