import json
from googleapiclient.discovery import build
import pandas as pd
from os import path
from itertools import chain
from sklearn.cluster import KMeans
from sklearn import metrics
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

def chunk_df(df, n=10):
    return [df[i:i+n] for i in range(0,df.shape[0],n)]

def get_api_key():
    with open('apiKey.json') as json_file:
        data = json.load(json_file)
        api_key = data['key']
    return api_key

cacheTypes = {
    "json": {
        "load": lambda f: json.load(f),
        "save": lambda data, f: json.dump(data, f)
    }
}
def cache(filename, get_data_fn, cacher):
    if not path.exists(filename):
        data = get_data_fn()
        with open(filename, 'w') as f:
            cacher['save'](data, f)
    else:
        with open(filename) as f:
            data = cacher['load'](f)

    return data

def cache_json(filename, get_data_fn):
    return cache(filename, get_data_fn, cacheTypes['json'])

_youtube = False
def youtube():
    global _youtube
    if not _youtube:
        api_key = get_api_key()
        _youtube = build('youtube', 'v3', developerKey=api_key)
    return _youtube

def join_concat(list_of_lists):
    return list(chain.from_iterable(list_of_lists))

def get_videos_data(wl_chunks):
    return join_concat([youtube().videos().list(
        part="snippet,contentDetails,statistics,topicDetails",
        id=','.join(wl_chunks[i]['id'])
    ).execute()['items'] for i in range(0, len(wl_chunks))])

def get_channels_data(videos_list):
    channel_ids = set(map(lambda item: item['snippet']['channelId'], videos_list))
    channel_chunks = chunk_df(pd.DataFrame(list(channel_ids)), 50)
    return join_concat([youtube().channels().list(
        part="snippet,contentDetails,statistics,topicDetails",
        id=','.join(channel_chunks[i][0])
    ).execute()['items'] for i in range(0, len(channel_chunks))])

def get_videos_df():
    wl = pd.read_csv('WL.csv')
    wl_chunks = chunk_df(wl, 50)
    videos_list = cache_json("videos_data.json", lambda: get_videos_data(wl_chunks))
    channels_list = cache_json("channels_data.json", lambda: get_channels_data(videos_list))

    videos_df = pd.DataFrame(videos_list, columns=['id'])
    videos_snippet = pd.DataFrame([v['snippet'] for v in videos_list], columns=['channelId','title','description','channelTitle','tags','categoryId'])
    videos_contentDetails = pd.DataFrame([v['contentDetails'] for v in videos_list], columns=['duration'])
    videos_statistics = pd.DataFrame([v['statistics'] for v in videos_list])
    videos_topicDetails = pd.DataFrame([v['topicDetails'] if 'topicDetails' in v else {} for v in videos_list])

    videos_df = pd.concat([videos_df, videos_snippet, videos_contentDetails, videos_statistics, videos_topicDetails], axis=1)

    channels_df = pd.DataFrame(channels_list, columns=['id'])
    channels_snippet = pd.DataFrame([v['snippet'] for v in channels_list], columns=['title', 'description'])
    channels_statistics = pd.DataFrame([v['statistics'] for v in channels_list])
    channels_topicDetails = pd.DataFrame([v['topicDetails'] if 'topicDetails' in v else {} for v in channels_list])

    channels_df = pd.concat([channels_df, channels_snippet, channels_statistics, channels_topicDetails], axis=1)

    videos_df = videos_df.join(channels_df.set_index('id'), on='channelId', rsuffix='_channel')
    return videos_df.set_index('id')

def get_features_df(videos_df):
    # TODO:
    #   - mean & normalize numeric columns
    #   - text columns? e.g. title, description
    #   - array columns? e.g. tags, topicIds, topicCategories
    #   - categorical columns (numeric / string): e.g. categoryId, channelTitle
    
    time_columns=['duration']
    numeric_columns = ['viewCount','likeCount','dislikeCount','favoriteCount','commentCount','viewCount_channel','commentCount_channel','subscriberCount','videoCount']
    text_columns = ['title','description','description_channel']
    array_columns = ['tags','relevantTopicIds','topicCategories','topicIds','topicCategories_channel']
    category_columns = ['channelId','channelTitle','categoryId']

    return pd.DataFrame(videos_df, columns=numeric_columns).fillna(0)

def clustering(df, n=3):
    # K-means
    model = KMeans(n_clusters=n).fit(df)
    labels = model.labels_
    scores = {
        "inertia": model.inertia_,
        "silhouette_score": metrics.silhouette_score(df, labels, metric='euclidean'),
        "calinski_harabasz_score": metrics.calinski_harabasz_score(df, labels),
        "davies_bouldin_score": metrics.davies_bouldin_score(df, labels)
    }

    # PCA + K-means
    # what else?

    return (model, labels, scores)

def main():
    videos_df = get_videos_df()
    features_df = get_features_df(videos_df)

    print(features_df)
    print(features_df.iloc[0])

    #print(features_df.loc[features_df.isnull().any(axis=1)])

    all_scores = pd.DataFrame([])
    for n in range(3,10):
        model, labels, scores = clustering(features_df,n)
        all_scores = all_scores.append(pd.Series(scores, name=n))

    #print(all_scores)

    ax = plt.gca()
    all_scores.plot(subplots=True,ax=ax,kind='line')
    plt.show()

if __name__ == "__main__":
    main()
