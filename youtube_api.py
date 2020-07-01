import argparse
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
    wl = pd.read_csv(args.file)
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
    #       NOTE: K-means normalized the data automatically. But maybe it's needed for other models.
    #   - text columns? e.g. title, description
    #   - array columns? e.g. tags, topicIds, topicCategories
    #   - categorical columns (numeric / string): e.g. categoryId, channelTitle

    time_columns=['duration']
    # maybe I should ignore these values, because my goal is to cluster by topic, and these nombers have nothing to do with that
    numeric_columns = ['viewCount','likeCount','dislikeCount','favoriteCount','commentCount','viewCount_channel','commentCount_channel','subscriberCount','videoCount']
    text_columns = ['title','description','description_channel']
    array_columns = ['tags','relevantTopicIds','topicCategories','topicIds']
    category_columns = ['channelId','categoryId']

    all_dfs = []

    if (args.text):
        print('using text data')
        vectorizer = CountVectorizer()
        corpus = videos_df.loc[:, text_columns].values.sum(axis=1)
        text = vectorizer.fit_transform(corpus).toarray()
        text_df = pd.DataFrame(text).set_index(videos_df.index)
        print('> added {} columns'.format(len(text_df.columns)))
        all_dfs.append(text_df)

    if (args.categorical):
        print('using categorical data')
        categorical_df = pd.DataFrame(gower.gower_matrix(videos_df.loc[:, category_columns], cat_features = [True for v in category_columns])).set_index(videos_df.index)
        all_dfs.append(categorical_df)

    if (args.numerical):
        print('using numerical data')
        numerical_df = pd.DataFrame(preprocessing.normalize(videos_df.loc[:, numeric_columns].fillna(0))).set_index(videos_df.index)
        all_dfs.append(numerical_df)

    def get_array_dummies(df, column):
        return pd.get_dummies(df[column].fillna('').apply(pd.Series).stack(), dtype=int).sum(level=0)

    if (args.array):
        print('using array data')
        dummies_arr = map(lambda col: get_array_dummies(videos_df, col), array_columns)
        dummies_df1 = pd.concat(dummies_arr, axis=1, sort=False)
        #dummies_df2 = pd.concat(map(lambda col: pd.get_dummies(videos_df[col].fillna(''), dtype=int), category_columns), axis=1, sort=False)
        print('> added {} columns'.format(len(dummies_df1.columns)))
        all_dfs.append(dummies_df1)
       
    features_df = pd.concat(all_dfs, axis=1, sort=False)
    print('features is {} dimentions'.format(len(features_df.columns)))

    # PCA compression
    if (args.pca):
        print('PCA compression...')
        pca = PCA()
        pca.fit(features_df)
        s = np.cumsum(pca.explained_variance_ratio_)
        n = min(len(s[s < args.pca_variance]) + 1, len(s))

        print('compressing into {} dimentions for keeping {} variance'.format(n, args.pca_variance))

        pca = PCA(n_components=n)

        features_df = pd.DataFrame(pca.fit_transform(features_df))

        '''pca.fit(features_df)
        print(pca.explained_variance_ratio_)
        print(len(pca.explained_variance_ratio_))
        print(np.cumsum(pca.explained_variance_ratio_))'''

    #print(features_df)

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

def visualize(results, videos_df, features_df):
    cmap = cm.get_cmap('Spectral') # Colour map (there are many others)

    results.plot(subplots=True,kind='line',y=results.columns.difference(['n','model','labels']))

    if (args.display_transform):
        if (args.display_transform == 'pca'):
            transformer = PCA(args.display)
        elif (args.display_transform == 'mca'):
            transformer = FactorAnalysis(args.display)
        points = transformer.fit_transform(features_df)
        points_df = pd.DataFrame(points)

        n = results['silhouette_score'].idxmax()
        row = results.loc[n]
        c = row['labels']

        x_vals = points_df.loc[:,0]
        y_vals = points_df.loc[:,1]

        if (args.display == 2):
            fig,ax = plt.subplots()
            sc = plt.scatter(x_vals, y_vals, c=c, cmap=cmap)
        elif (args.display == 3):
            z_vals = points_df.loc[:,2]
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            sc = ax.scatter(x_vals, y_vals, z_vals, c=c, cmap=cmap)

        annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)
        names = videos_df['title'].reset_index(drop=True)
        norm = plt.Normalize(1,4)

        def get_text(ind):
            return "\n".join([names[n] for n in ind["ind"]])

        def update_annot(ind, text):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor(cmap(norm(c[ind["ind"][0]])))
            annot.get_bbox_patch().set_alpha(0.4)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = sc.contains(event)
                text = get_text(ind)
                if cont:
                    update_annot(ind, text)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                elif vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)

    plt.show()

def main():
    videos_df = get_videos_df()
    features_df = get_features_df(videos_df)

    #print(features_df)
    #print(features_df.iloc[0])
    #print(features_df.describe())

    #print(features_df.loc[features_df.isnull().any(axis=1)])

    clusters = range(args.min_clusters,args.max_clusters+1)
    scores_list = []
    models = []
    labels_list = []
    for n in clusters:
        print('cluster into {} groups...'.format(n))
        model, labels, scores = clustering(features_df,n)
        print(scores)
        models.append(model)
        labels_list.append(labels)
        scores_list.append(pd.Series(scores, name=n))

        videos_df['{} labels'.format(n)] = labels

    videos_df.to_csv('out.csv')

    results = pd.DataFrame(scores_list)
    results['model'] = models
    results['labels'] = labels_list
    results['n'] = clusters
    results.set_index('n')

    visualize(results, videos_df, features_df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='cluster videos from a youtube playlist based on the available data')
    parser.add_argument('-v','--version',help='display version', action='store_true')
    parser.add_argument('--file', help='the filename containing the playlist video ids', type=str, default='WL.csv')
    parser.add_argument('--array',help='use array data columns', action='store_true', default=True)
    parser.add_argument('--numerical',help='use numerical data columns', action='store_true', default=False)
    parser.add_argument('--categorical',help='use categorical data columns', action='store_true', default=False)
    parser.add_argument('--text',help='use text data columns', action='store_true', default=False)
    parser.add_argument('--pca',help='compress the features dataframe using pca', action='store_true', default=False)
    parser.add_argument('--pca_variance',help='if using pca, how much variance to retain',type=float,default=0.95)
    parser.add_argument('--display',help='how to display the scatter plot: 2d/3d', choices=[2,3], type=int, default=3)
    parser.add_argument('--display_transform',help='how to transform the data before displaying it', choices=['', 'pca', 'mca'], type=str, default='pca')
    parser.add_argument('--min_clusters',help='minimum number of clusters',type=int,default=3)
    parser.add_argument('--max_clusters',help='maximum number of clusters',type=int,default=10)
 
    args = parser.parse_args()

    if args.version:
        print('1.0.0')
    else:
        main()

