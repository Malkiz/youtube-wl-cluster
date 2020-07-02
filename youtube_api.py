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
import itertools

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
    videos_list = cache_json(args.file + "_videos_data.json", lambda: get_videos_data(wl_chunks))
    channels_list = cache_json(args.file + "_channels_data.json", lambda: get_channels_data(videos_list))

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

def get_features_df(videos_df, data_sets):
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

    def text():
        print('using text data')
        vectorizer = CountVectorizer()
        corpus = videos_df.loc[:, text_columns].values.sum(axis=1)
        text = vectorizer.fit_transform(corpus).toarray()
        text_df = pd.DataFrame(text).set_index(videos_df.index)
        print('> added {} columns'.format(len(text_df.columns)))
        return text_df

    def categorical_1():
        print('using categorical data - Gower')
        categorical_df = pd.DataFrame(gower.gower_matrix(videos_df.loc[:, category_columns], cat_features = [True for v in category_columns])).set_index(videos_df.index)
        print('> added {} columns'.format(len(categorical_df.columns)))
        return categorical_df

    def numerical():
        print('using numerical data')
        numerical_df = pd.DataFrame(preprocessing.normalize(videos_df.loc[:, numeric_columns].fillna(0))).set_index(videos_df.index)
        return numerical_df

    def get_array_dummies(df, column):
        return pd.get_dummies(df[column].fillna('').apply(pd.Series).stack(), dtype=int).sum(level=0)

    def array():
        print('using array data')
        dummies_arr = map(lambda col: get_array_dummies(videos_df, col), array_columns)
        dummies_df1 = pd.concat(dummies_arr, axis=1, sort=False)
        print('> added {} columns'.format(len(dummies_df1.columns)))
        return dummies_df1

    def categorical_2():
        print('using categorical data - dummies')
        dummies_df2 = pd.concat(map(lambda col: pd.get_dummies(videos_df[col].fillna(''), dtype=int), category_columns), axis=1, sort=False)
        print('> added {} columns'.format(len(dummies_df2.columns)))
        return dummies_df2
       
    data_getters = {
        'text':text,
        'categorical_1':categorical_1,
        'numerical':numerical,
        'array':array,
        'categorical_2':categorical_2
    }
    all_dfs_dict = {n: data_getters[n]() for n in data_sets }
    return all_dfs_dict

def compress(features_df, options):
    # PCA compression
    if (options['method'] == 'pca'):
        print('PCA compression...')
        pca = PCA()
        pca.fit(features_df)
        s = np.cumsum(pca.explained_variance_ratio_)
        n = min(len(s[s < options['variance']]) + 1, len(s))

        print('compressing into {} dimentions for keeping {} variance'.format(n, options['variance']))

        pca = PCA(n_components=n)

        features_df = pd.DataFrame(pca.fit_transform(features_df))

        '''pca.fit(features_df)
        print(pca.explained_variance_ratio_)
        print(len(pca.explained_variance_ratio_))
        print(np.cumsum(pca.explained_variance_ratio_))'''

    #print(features_df)

    return features_df

def clustering(all_dfs_dict, n, index, init=pd.DataFrame()):
    def K_means(df):
        model = KMeans(n_clusters=n).fit(df)
        labels = model.labels_
        scores = {}
        if 'inertia' in args.scorers:
            scores["inertia"] = - model.inertia_
        if 'silhouette_score' in args.scorers:
            scores["silhouette_score"] = metrics.silhouette_score(df, labels, metric='euclidean')
        if 'calinski_harabasz_score' in args.scorers:
            scores["calinski_harabasz_score"] = metrics.calinski_harabasz_score(df, labels)
        if 'davies_bouldin_score' in args.scorers:
            scores["davies_bouldin_score"] = metrics.davies_bouldin_score(df, labels)
        return (model, labels, scores)

    def best_K_means(df, repeat=3):
        bm, bl, bs = K_means(df)
        for i in range(0,int(repeat)-1):
            m, l, s = K_means(df)
            if (s[args.scorer] > bs[args.scorer]):
                bm, bl, bs = (m, l, s)
        return (bm, bl, bs)

    # PCA + K-means
    # what else?

    actions = {
        'best_K_means':best_K_means,
        'K_means':K_means
    }

    curr_res = pd.DataFrame(index=index)

    for s in args.stages:
        if not init.empty:
            features_df = init
            init = pd.DataFrame()
        else:
            features_df = join_features(curr_res, all_dfs_dict, s['data'])

        if 'compress' in s:
            features_df = compress(features_df, s['compress'])

        m_args = s['args'] if 'args' in s else {}
        m, l, s = actions[s['method']](features_df, *m_args)
        curr_res = pd.get_dummies(l, dtype=int)
        curr_res.index = index

    return m, l, s

def join_features(curr_res, all_dfs_dict, data):
        features_df = pd.concat([curr_res]+[all_dfs_dict[d] for d in data], axis=1, sort=False)
        print('features is {} dimentions'.format(len(features_df.columns)))
        return features_df

def visualize(results, videos_df, features_df):
    cmap = cm.get_cmap('Spectral') # Colour map (there are many others)

    results.plot(subplots=True,kind='line',y=results.columns.difference(['n','model','labels']))

    if (args.display_transform):
        n = results[args.scorer].idxmax()
        row = results.loc[n]

        n_components = min(args.display, len(features_df.columns))
        if (args.display_transform == 'pca'):
            transformer = PCA(n_components)
        elif (args.display_transform == 'mca'):
            transformer = FactorAnalysis(n_components)
        points = transformer.fit_transform(features_df)
        points_df = pd.DataFrame(points)

        title = 'best clustering according to {}: {} groups, score {}'.format(args.scorer, n, results.at[n, args.scorer])
        print(title)
        c = row['labels']

        x_vals = points_df.loc[:,0]
        y_vals = points_df.loc[:,1]

        if (n_components == 2):
            fig,ax = plt.subplots()
            sc = plt.scatter(x_vals, y_vals, c=c, cmap=cmap)
        elif (n_components == 3):
            z_vals = points_df.loc[:,2]
            fig = plt.figure()
            ax = fig.add_subplot(111, projection='3d')
            sc = ax.scatter(x_vals, y_vals, z_vals, c=c, cmap=cmap)
        ax.set_title(title)

        annot = ax.annotate("", xy=(0,0), xytext=(20,20),textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)
        names = (pd.DataFrame(c, index=videos_df.index)[0].astype(str) + '|' + videos_df['channelTitle'] + '|' + videos_df['title']).reset_index(drop=True)
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

    unique_data = set(itertools.chain.from_iterable([s['data'] for s in args.stages]))
    all_dfs_dict = get_features_df(videos_df, unique_data)

    stage0 = args.stages[0]
    init = join_features(pd.DataFrame(index=videos_df.index), all_dfs_dict, stage0['data'])
    if 'compress' in stage0:
        init = compress(init, stage0['compress'])
        stage0.pop('compress', None)

    clusters = range(args.min_clusters,args.max_clusters+1)
    print('clustering over {}'.format(clusters))
    scores_list = []
    models = []
    labels_list = []
    for n in clusters:
        print('cluster into {} groups...'.format(n))
        model, labels, scores = clustering(all_dfs_dict,n,videos_df.index, init)
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

    features_df = join_features(pd.DataFrame(index=videos_df.index), all_dfs_dict, unique_data)
    visualize(results, videos_df, features_df)

def parse_args():
    args = parser.parse_args()
    args.scorers = args.scorers.split(',')
    if args.scorer not in args.scorers:
        raise ValueError('the selected scorer {} is not present in the scorers list {}'.format(args.scorer, args.scorers))
    
    stages = []
    for s in args.stages.split('|'):
        x = s.split(':')
        m = x[0].split('@')
        stage = {'method':m[0]}
        if len(m) > 1:
            stage['args'] = m[1].split(',')
        x = x[1].split('>')
        stage['data'] = x[0].split(',')
        if len(x) > 1:
            c = x[1].split(',')
            stage['compress'] = {'method':c[0], 'variance':float(c[1])}
        stages.append(stage)
    args.stages = stages

    return args

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='cluster videos from a youtube playlist based on the available data')
    parser.add_argument('-v','--version',help='display version', action='store_true')
    parser.add_argument('--file', help='the filename containing the playlist video ids', type=str, default='WL.csv')
    parser.add_argument('--display',help='how to display the scatter plot: 2d/3d', choices=[2,3], type=int, default=3)
    parser.add_argument('--display_transform',help='how to transform the data before displaying it', choices=['', 'pca', 'mca'], type=str, default='pca')
    parser.add_argument('--min_clusters',help='minimum number of clusters',type=int,default=5)
    parser.add_argument('--max_clusters',help='maximum number of clusters',type=int,default=15)
    parser.add_argument('--scorer',help='the scorer to use for choosing the best cluster',type=str,default='silhouette_score',choices=['silhouette_score','inertia','calinski_harabasz_score','davies_bouldin_score'])
    parser.add_argument('--scorers',help='which scorers to calculate',type=str,default='silhouette_score')
    parser.add_argument('--stages',help='stages of clustering',type=str,default='best_K_means@10:array,categorical_1>pca,0.99')
 
    args = parse_args()

    if args.version:
        print('1.0.0')
    else:
        print(args)
        main()

