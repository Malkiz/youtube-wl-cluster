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
import gower
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import PCA
import numpy as np
from sklearn import preprocessing
from matplotlib import cm
from sklearn.decomposition import FactorAnalysis

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

def get_features_df(videos_df, use_pca=False):
    # TODO:
    #   - mean & normalize numeric columns
    #       NOTE: K-means normalized the data automatically. But maybe it's needed for other models.
    #   - text columns? e.g. title, description
    #   - array columns? e.g. tags, topicIds, topicCategories
    #   - categorical columns (numeric / string): e.g. categoryId, channelTitle

    time_columns=['duration']
    # maybe I should ignore these values, because my goal is to cluster by topic, and these nombers have nothing to do with that
    numeric_columns = ['viewCount','likeCount','dislikeCount','favoriteCount','commentCount','viewCount_channel','commentCount_channel','subscriberCount','videoCount']
    text_columns = ['title','description','description_channel']
    array_columns = ['tags','relevantTopicIds','topicCategories','topicIds','topicCategories_channel']
    category_columns = ['channelId','channelTitle','categoryId']

    # only numeric columns - for initial K-means test
    #return pd.DataFrame(videos_df, columns=numeric_columns).fillna(0)

    # categorical columns - for gower distance
    #return pd.DataFrame(videos_df, columns=category_columns)

    '''# handle text
    vectorizer = CountVectorizer()
    corpus = videos_df.loc[:, text_columns].values.sum(axis=1)
    text = vectorizer.fit_transform(corpus).toarray()

    # both numerical and categorical columns
    features_df = pd.concat([
        #pd.DataFrame(preprocessing.normalize(videos_df.loc[:, numeric_columns].fillna(0))),
        pd.DataFrame(gower.gower_matrix(videos_df.loc[:, category_columns], cat_features = [True for v in category_columns])),
        pd.DataFrame(text)
    ], axis=1)'''

    def get_array_dummies(df, column):
        return pd.get_dummies(df[column].fillna('').apply(pd.Series).stack(), dtype=int).sum(level=0)

    # try next: use only [categoryId, tags, (channelId)] as features.
    # I have a feeling that this will give better results
    # I will need to convert the 'tags' arrays into "bag of words" somehow
    #print(videos_df.loc[:,array_columns].fillna(''))
    #print(videos_df.loc[:,'tags'].fillna('').map(lambda x: ' '.join(x)))
    #print(len(set([st for row in videos_df.loc[:,"tags"].fillna('') for st in row])))
    #print(pd.get_dummies(videos_df.loc[:,"tags"]))
    #print(get_array_dummies(videos_df, 'tags'))
    dummies_arr = map(lambda col: get_array_dummies(videos_df, col), array_columns)
    dummies_df = pd.concat(dummies_arr, axis=1, sort=False)
    features_df = dummies_df

    # PCA compression
    if (use_pca):
        pca = PCA()
        pca.fit(features_df)
        s = np.cumsum(pca.explained_variance_ratio_)
        variance = 0.95
        n = min(len(s[s < variance]) + 1, len(s))

        pca = PCA(n_components=n)

        features_df = pd.DataFrame(pca.fit_transform(features_df))

        '''pca.fit(features_df)
        print(pca.explained_variance_ratio_)
        print(len(pca.explained_variance_ratio_))
        print(np.cumsum(pca.explained_variance_ratio_))'''

    '''features_df = pd.concat([
        videos_df.reset_index().loc[:, 'id'],
        features_df
    ], axis=1).set_index('id')'''

    return features_df

def clustering(df, n=3):
    def K_means(df):
        model = KMeans(n_clusters=n).fit(df)
        labels = model.labels_
        scores = {
            "inertia": model.inertia_,
            "silhouette_score": metrics.silhouette_score(df, labels, metric='euclidean'),
            "calinski_harabasz_score": metrics.calinski_harabasz_score(df, labels),
            "davies_bouldin_score": metrics.davies_bouldin_score(df, labels)
        }
        return (model, labels, scores)

    # PCA + K-means
    # what else?

    return K_means(df)

def visualize(results, videos_df, features_df, dim_reduction='pca'):
    print(results)
    #print(pd.DataFrame(videos_df, columns=['viewCount', 'categoryId', 'tags', 'title']))

    cmap = cm.get_cmap('Spectral') # Colour map (there are many others)

    plt.figure('scores')
    results.plot(subplots=True,kind='line',y=results.columns.difference(['n','model','labels']))

    if (dim_reduction):
        if (dim_reduction == 'pca'):
            transformer = PCA(n_components=2)
        elif (dim_reduction == 'mca'):
            transformer = FactorAnalysis(n_components=2)
        points = transformer.fit_transform(features_df)
    points_df = pd.DataFrame(points)

    n = results['silhouette_score'].idxmax()
    plt.figure(n)
    row = results.loc[n]
    points_df.plot(kind='scatter', x=0, y=1, c=row['labels'], title=n, cmap=cmap)

    #input("PRESS ENTER TO CONTINUE.")
    plt.show()

def main():
    videos_df = get_videos_df()
    features_df = get_features_df(videos_df)

    print(features_df)
    print(features_df.iloc[0])
    #print(features_df.describe())

    #print(features_df.loc[features_df.isnull().any(axis=1)])

    clusters = range(3,10)
    scores_list = []
    models = []
    labels_list = []
    for n in clusters:
        model, labels, scores = clustering(features_df,n)
        models.append(model)
        labels_list.append(labels)
        scores_list.append(pd.Series(scores, name=n))

        '''print(n)
        for i in range(0,n):
            cluster_df = videos_df.iloc[labels == i].loc[:, ['title','channelId','channelTitle']]
            print(cluster_df.head())'''

    results = pd.DataFrame(scores_list)
    results['model'] = models
    results['labels'] = labels_list
    results['n'] = clusters
    results.set_index('n')

    visualize(results, videos_df, features_df)

if __name__ == "__main__":
    main()
