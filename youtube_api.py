import json
from googleapiclient.discovery import build
import pandas as pd
from os import path

def chunk_df(df, n=10):
    return [df[i:i+n] for i in range(0,df.shape[0],n)]

def get_api_key():
    with open('apiKey.json') as json_file:
        data = json.load(json_file)
        api_key = data['key']
    return api_key

def cache(filename, get_data_fn):
    if not path.exists(filename):
        data = get_data_fn()
        with open(filename, 'w') as f:
            json.dump(data, f)
    else:
        with open(filename) as f:
            data = json.load(f)

    return data

_youtube = False
def youtube():
    global _youtube
    if not _youtube:
        api_key = get_api_key()
        _youtube = build('youtube', 'v3', developerKey=api_key)
    return _youtube

def get_videos_data(wl_chunks):
    return [youtube().videos().list(
        part="snippet,contentDetails,statistics",
        id=','.join(wl_chunks[i]['id'])
    ).execute() for i in range(0, len(wl_chunks))]

def main():
    wl = pd.read_csv('WL.csv')
    wl_chunks = chunk_df(wl, 50)
    data = cache("videos_data.json", lambda: get_videos_data(wl_chunks))
    print(data)

if __name__ == "__main__":
    main()
