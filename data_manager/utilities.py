# Useful functions for computation and visualization of data descriptors

# Imports
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from IPython.display import display, Markdown

# Hierarchical clustering
import matplotlib as mpl
import scipy
import scipy.cluster.hierarchy as sch
import scipy.spatial.distance as dist
import string
import time
import sys, os
import getopt

# Principal component analysis
from sklearn.decomposition import PCA
from itertools import combinations

# Discriminant analysis
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

# T-SNE
from sklearn.manifold import TSNE

# Kolmogorov-Smirnov
from scipy.stats import ks_2samp

# Chi-square
from scipy.stats import chi2_contingency

# KL divergence, mutual information
from sklearn.metrics import mutual_info_score
from scipy.stats import entropy

def printmd(string):
    """ Print Markdown string
    """
    display(Markdown(string))


def is_numeric(variable):
    """ Test if a variable (DataFrame column) is numeric or categorical 
    """

    numeric = False
    for value in variable:
        # Check if there is at least one value that is a number and not NaN
        # (isinstance consider Nan as a Number)
        if isinstance(value, (int, float)) and not np.isnan(value):
            numeric = True
            break

    return numeric


def preprocessing(data, normalization='mean'):
    """ Return preprocessed DataFrame
        Input: 
          data: DataFrame
          normalization: 'mean', 'minmax', None
    """

    columns = data.columns.values

    for column in columns:

        # For numerical variables
        if is_numeric(data[column]): # TODO use feat_type

            # Replace NaN with the median of the variable value
            data[column] = data[column].fillna(data[column].median())

            # Replace +Inf by the maximum and -Inf by the minimum
            data[column] = data[column].replace(np.inf, max(data[column]))
            data[column] = data[column].replace(-np.inf, min(data[column]))

        # For categorigal variables
        else:
            # Replace NaN with 'missing'
            # TODO : For one-hot encoding : [0, 0, ..., 0]
            data[column] = data[column].fillna('missing')

            # One-hot encoding
            one_hot = pd.get_dummies(data[column])
            data = data.drop(column, axis=1)
            data = data.join(one_hot, lsuffix='l', rsuffix='r')

    if normalization == 'mean':
        data = (data - data.mean()) / data.std()
    
    elif normalization in ['minmax', 'min-max']:
        data = (data - data.min()) / (data.max() - data.min())

    return data


def show_classes(y):
    """ Shows classes distribution
		Input : y is a pandas DataFrame
	"""
    for column in y.columns:
        sns.distplot(y[column])
        plt.show()


def show_correlation(df, size=10):
    """ Shows a graphical correlation matrix for each pair of columns in the dataframe.

    Input:
      	df: pandas DataFrame
        size: vertical and horizontal size of the plot
    """

    corr = df.corr()
    fig, ax = plt.subplots(figsize=(size, size))
    ax.matshow(corr)
    plt.xticks(range(len(corr.columns)), corr.columns)
    plt.yticks(range(len(corr.columns)), corr.columns)
    plt.show()


def heatmap(X, row_method, column_method, row_metric, column_metric,
            color_gradient):

    print(
        "\nPerforming hierarchical clustering using {} for columns and {} for rows".
        format(column_metric, row_metric))
    """
    This below code is based in large part on the protype methods:
    http://old.nabble.com/How-to-plot-heatmap-with-matplotlib--td32534593.html
    http://stackoverflow.com/questions/7664826/how-to-get-flat-clustering-corresponding-to-color-clusters-in-the-dendrogram-cre

    x is an m by n ndarray, m observations, n genes
    """

    ### Define variables
    x = np.array(X)
    column_header = column_header = [
        'T' + str(dataset) for dataset in list(X)
    ]  # X.columns.values
    row_header = ['A' + str(model) for model in list(X.index)]  # X.index

    ### Define the color gradient to use based on the provided name
    n = len(x[0])
    m = len(x)
    if color_gradient == 'red_white_blue':
        cmap = plt.cm.bwr
    if color_gradient == 'red_black_sky':
        cmap = RedBlackSkyBlue()
    if color_gradient == 'red_black_blue':
        cmap = RedBlackBlue()
    if color_gradient == 'red_black_green':
        cmap = RedBlackGreen()
    if color_gradient == 'yellow_black_blue':
        cmap = YellowBlackBlue()
    if color_gradient == 'seismic':
        cmap = plt.cm.seismic
    if color_gradient == 'green_white_purple':
        cmap = plt.cm.PiYG_r
    if color_gradient == 'coolwarm':
        cmap = plt.cm.coolwarm

    ### Scale the max and min colors so that 0 is white/black
    vmin = x.min()
    vmax = x.max()
    vmax = max([vmax, abs(vmin)])
    # vmin = vmax*-1
    # norm = mpl.colors.Normalize(vmin/2, vmax/2) ### adjust the max and min to scale these colors
    norm = mpl.colors.Normalize(vmin, vmax)
    ### Scale the Matplotlib window size
    default_window_hight = 8.5
    default_window_width = 12
    fig = plt.figure(figsize=(default_window_width, default_window_hight))  
    ### could use m,n to scale here
    color_bar_w = 0.015  ### Sufficient size to show

    ## calculate positions for all elements
    # axm, placement of heatmap for the data matrix
    [axm_x, axm_y, axm_w, axm_h] = [0.05, 0.95, 1, 1]
    width_between_axm_axr = 0.01
    text_margin = 0.1 # space between color bar and feature names
    
    # axr, placement of row side colorbar
    [axr_x, axr_y, axr_w, axr_h] = [0.31, 0.1, color_bar_w, 0.6]  
    ### second to last controls the width of the side color bar - 0.015 when showing
    axr_x =  axm_x + axm_w + width_between_axm_axr + text_margin
    axr_y = axm_y
    axr_h = axm_h
    width_between_axr_ax1 = 0.004
    
    # ax1, placement of dendrogram 1, on the right of the heatmap
    #if row_method != None: w1 =
    [ax1_x, ax1_y, ax1_w, ax1_h] = [0.05, 0.22, 0.2, 0.6]
    ax1_x = axr_x + axr_w + width_between_axr_ax1
    ax1_y = axr_y
    ax1_h = axr_h
    ### The second value controls the position of the matrix relative to the bottom of the view
    width_between_ax1_axr = 0.004
    height_between_ax1_axc = 0.004  ### distance between the top color bar axis and the matrix

    # axc, placement of column side colorbar
    [axc_x, axc_y, axc_w, axc_h] = [0.4, 0.63, 0.5, color_bar_w]  
    ### last one controls the height of the top color bar - 0.015 when showing
    axc_x = axm_x
    axc_y = axm_y - axc_h - width_between_axm_axr - text_margin
    axc_w = axm_w
    height_between_axc_ax2 = 0.004

    # ax2, placement of dendrogram 2, on the top of the heatmap
    [ax2_x, ax2_y, ax2_w, ax2_h] = [0.3, 0.72, 0.6, 0.15]
    ### last one controls height of the dendrogram
    ax2_x = axc_x
    ax2_y = axc_y - axc_h - ax2_h - height_between_axc_ax2
    ax2_w = axc_w

    # axcb - placement of the color legend
    [axcb_x, axcb_y, axcb_w, axcb_h] = [0.07, 0.88, 0.18, 0.09]
    axcb_x = ax1_x
    axcb_y = ax2_y
    axcb_w = ax1_w
    axcb_h = ax2_h

    # Compute and plot bottom dendrogram
    if column_method != None:
        start_time = time.time()
        d2 = dist.pdist(x.T)
        D2 = dist.squareform(d2)
        ax2 = fig.add_axes([ax2_x, ax2_y, ax2_w, ax2_h], frame_on=True)
        Y2 = sch.linkage(D2, method=column_method, metric=column_metric)  
        ### array-clustering metric - 'average', 'single', 'centroid', 'complete'
        Z2 = sch.dendrogram(Y2, orientation='bottom')
        ind2 = sch.fcluster(Y2, 0.7 * max(Y2[:, 2]), 'distance')  
        ### This is the default behavior of dendrogram
        ax2.set_xticks([])  ### Hides ticks
        ax2.set_yticks([])
        time_diff = str(round(time.time() - start_time, 1))
        print('Column clustering completed in {} seconds'.format(time_diff))
    else:
        ind2 = ['NA'] * len(column_header)  
        ### Used for exporting the flat cluster data

    # Compute and plot right dendrogram.
    if row_method != None:
        start_time = time.time()
        d1 = dist.pdist(x)
        D1 = dist.squareform(d1)  # full matrix
        ax1 = fig.add_axes([ax1_x, ax1_y, ax1_w, ax1_h], frame_on=True)  
        # frame_on may be False
        Y1 = sch.linkage(D1, method=row_method, metric=row_metric)  
        ### gene-clustering metric - 'average', 'single', 'centroid', 'complete'
        Z1 = sch.dendrogram(Y1, orientation='right')
        ind1 = sch.fcluster(Y1, 0.7 * max(Y1[:, 2]), 'distance')  
        ### This is the default behavior of dendrogram
        # print 'ind1', ind1
        ax1.set_xticks([])  ### Hides ticks
        ax1.set_yticks([])
        time_diff = str(round(time.time() - start_time, 1))
        print('Row clustering completed in {} seconds'.format(time_diff))
    else:
        ind1 = ['NA'] * len(row_header)  
        ### Used for exporting the flat cluster data

    # Plot distance matrix.
    axm = fig.add_axes([axm_x, axm_y, axm_w, axm_h])  
    # axes for the data matrix
    xt = x
    if column_method != None:
        idx2 = Z2['leaves']  
        ### apply the clustering for the array-dendrograms to the actual matrix data
        xt = xt[:, idx2]
        # print 'idx2', idx2, len(idx2)
        # print 'ind2', ind2, len(ind2)
        ind2 = [ind2[i] for i in idx2]
        # ind2 = ind2[:,idx2] ### reorder the flat cluster to match the order of the leaves the dendrogram
    if row_method != None:
        idx1 = Z1['leaves']  
        ### apply the clustering for the gene-dendrograms to the actual matrix data
        xt = xt[idx1, :]  # xt is transformed x
        # ind1 = ind1[idx1,:] ### reorder the flat cluster to match the order of the leaves the dendrogram
        ind1 = [ind1[i] for i in idx1]
    ### taken from http://stackoverflow.com/questions/2982929/plotting-results-of-hierarchical-clustering-ontop-of-a-matrix-of-data-in-python/3011894#3011894
    # print xt
    im = axm.matshow(xt, aspect='auto', origin='lower', cmap=cmap, norm=norm)  
    ### norm=norm added to scale coloring of expression with zero = white or black
    axm.set_xticks([])  ### Hides x-ticks
    axm.set_yticks([])

    # Add text
    new_row_header = []
    new_column_header = []
    for i in range(x.shape[0]):
        if row_method != None:
            if len(
                    row_header
            ) < 100:  ### Don't visualize gene associations when more than 100 rows
                axm.text(x.shape[1] - 0.5, i, '  ' + row_header[idx1[i]])
            new_row_header.append(row_header[idx1[i]])
        else:
            if len(
                    row_header
            ) < 100:  ### Don't visualize gene associations when more than 100 rows
                axm.text(x.shape[1] - 0.5, i,
                         '  ' + row_header[i])  ### When not clustering rows
            new_row_header.append(row_header[i])
    for i in range(x.shape[1]):
        if column_method != None:
            axm.text(
                i,
                -0.9,
                ' ' + column_header[idx2[i]],
                rotation=270,
                verticalalignment="top")  # rotation could also be degrees
            new_column_header.append(column_header[idx2[i]])
        else:  ### When not clustering columns
            axm.text(
                i,
                -0.9,
                ' ' + column_header[i],
                rotation=270,
                verticalalignment="top")
            new_column_header.append(column_header[i])

    for j in range(x.shape[0]):
        if row_method != None:
            axm.text(
                len(new_column_header) + 1,
                j,
                ' ' + row_header[idx1[j]],
                rotation=0,
                verticalalignment="top")  # rotation could also be degrees
            new_row_header.append(row_header[idx1[j]])
        else:  ### When not clustering columns
            axm.text(
                len(new_column_header) + 1,
                j,
                ' ' + row_header[j],
                rotation=0,
                verticalalignment="top")
            new_row_header.append(row_header[j])

    # Plot colside colors
    # axc --> axes for column side colorbar
    if column_method != None:
        axc = fig.add_axes([axc_x, axc_y, axc_w,
                            axc_h])  # axes for column side colorbar
        cmap_c = mpl.colors.ListedColormap(['r', 'g', 'b', 'y', 'w', 'k', 'm'])
        dc = np.array(ind2, dtype=int)
        dc.shape = (1, len(ind2))
        im_c = axc.matshow(dc, aspect='auto', origin='lower', cmap=cmap_c)
        axc.set_xticks([])  ### Hides ticks
        axc.set_yticks([])

    # Plot rowside colors
    # axr --> axes for row side colorbar
    if row_method != None:
        axr = fig.add_axes([axr_x, axr_y, axr_w,
                            axr_h])  # axes for column side colorbar
        dr = np.array(ind1, dtype=int)
        dr.shape = (len(ind1), 1)
        #print ind1, len(ind1)
        cmap_r = mpl.colors.ListedColormap(['r', 'g', 'b', 'y', 'w', 'k', 'm'])
        im_r = axr.matshow(dr, aspect='auto', origin='lower', cmap=cmap_r)
        axr.set_xticks([])  ### Hides ticks
        axr.set_yticks([])

    # Plot color legend
    axcb = fig.add_axes(
        [axcb_x, axcb_y, axcb_w, axcb_h], frame_on=False)  # axes for colorbar
    # print 'axcb', axcb
    cb = mpl.colorbar.ColorbarBase(
        axcb, cmap=cmap, norm=norm, orientation='horizontal')
    # print cb
    axcb.set_title("colorkey")

    cb.set_label("Differential Expression (log2 fold)")

    ### Render the graphic
    if len(row_header) > 50 or len(column_header) > 50:
        plt.rcParams['font.size'] = 5
    else:
        plt.rcParams['font.size'] = 8

    plt.show()


def compute_pca(X, verbose=False, **kwargs):
    """ 
        Compute PCA.

        :param X: Data 
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for PCA (see sklearn doc)
        :return: Tuple (pca, X) containing a PCA object (see sklearn doc) and the transformed data
        :rtype: Tuple
    """
    pca = PCA(**kwargs)
    X = pca.fit_transform(X)

    print('Explained variance ratio of the {} components: \n {}'.format(pca.n_components_, 
                                                                        pca.explained_variance_ratio_))

    if verbose: 
        plt.bar(left=range(pca.n_components_), 
                height=pca.explained_variance_ratio_, 
                width=0.3, 
                tick_label=range(pca.n_components_))
        plt.title('Explained variance ratio by principal component')
        plt.show()
        
    return pca, X


def show_pca(X, y, i=1, j=2, verbose=False, **kwargs):
    """ 
        Plot PCA.

        :param X: Data
        :param y: Labels
        :param i: i_th component of the PCA
        :param j: j_th component of the PCA
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for PCA (see sklearn doc)
    """
    pca, X = compute_pca(X, verbose, **kwargs)

    assert(i <= pca.n_components_ and j <= pca.n_components_ and i != j)

    if y.ndim > 1:
        y = np.where(y==1)[1]

    target_num = len(np.unique(y))
    target_names = range(target_num)
    
    for label in range(target_num):
        plt.scatter(X[y == label, i-1], X[y == label, j-1], alpha=.8, lw=2, label=target_names[label])
    plt.xlabel('PC '+str(i))
    plt.ylabel('PC '+str(j))
    plt.legend(loc='best', shadow=False, scatterpoints=1)
    plt.title('Principal Component Analysis: PC{} and PC{}'.format(str(i), str(j)))
    plt.show()


def compute_lda(X, verbose=False, **kwargs):
    """ 
        Compute LDA.

        :param X: Data 
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for LDA (see sklearn doc)
        :return: Tuple (lda, X) containing a LDA object (see sklearn doc) and the transformed data
        :rtype: Tuple
    """
    lda = LinearDiscriminantAnalysis(**kwargs)
    X = lda.fit_transform(X)

    return lda, X


def show_lda(X, y, verbose=False, **kwargs):
    """ 
        Plot LDA.

        :param X: Data
        :param y: Labels
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for PCA (see sklearn doc)
    """
    _, X = compute_lda(X, verbose=verbose, **kwargs)
    if y.shape[1] > 1:
        y = np.where(y==1)[1]

    target_num = len(np.unique(y))
    target_names = range(target_num)

    for label in range(target_num):
        plt.scatter(X[y == label, 0], X[y == label, 1], alpha=.8, lw=2, label=target_names[label])

    plt.legend(loc='best', shadow=False, scatterpoints=1)
    plt.title('LDA of dataset')
    plt.show()


def compute_tsne(X, verbose=False, **kwargs):
    """ 
        Compute T-SNE.

        :param X: Data 
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for T-SNE (see sklearn doc)
        :return: Tuple (tsne, X) containing a T-SNE object (see sklearn doc) and the transformed data
        :rtype: Tuple
    """
    tsne = TSNE(**kwargs)
    X = tsne.fit_transform(X)

    return tsne, X 


def show_tsne(X, y, i=1, j=2, verbose=False, **kwargs):
    """ 
        Plot T-SNE.

        :param X: Data
        :param y: Labels
        :param i: i_th component of the T-SNE
        :param j: j_th component of the T-SNE
        :param verbose: Display additional information during run
        :param **kwargs: Additional parameters for T-SNE (see sklearn doc)
    """
    tsne, X = compute_tsne(X, verbose=verbose, **kwargs)
    assert(i <= tsne.embedding_.shape[1] and j <= tsne.embedding_.shape[1] and i != j)

    if y.shape[1] > 1:
        y = np.where(y==1)[1]

    target_num = len(np.unique(y))
    target_names = range(target_num)

    for label in range(target_num):
        plt.scatter(X[y == label, i-1], X[y == label, j-1], alpha=.8, lw=2, label=target_names[label])
    plt.legend(loc='best', shadow=False, scatterpoints=1)
    plt.title('T-SNE: TC{} and TC{}'.format(str(i), str(j)))
    plt.show()
  
    
def frequency(data):
    """ Pandas series to frequency distribution
    """
    # TODO error if several columns have the same header
    return data.value_counts()
    
    
def chi_square(col1, col2):
    """ Performs Chi2 on two DataFrame columns
    """
    return chi2_contingency(np.array([col1, col2]))
        
        
def kolmogorov_smirnov(col1, col2):
    """ Performs Kolmogorov-Smirnov test on two DataFrame columns
    """
    return ks_2samp(col1, col2)
    
def kullback_leibler(freq1, freq2):
    """ Performs KL divergence on probability distributions
        Return a couple because this is not symetric
    """    
    return entropy(freq1, qk=freq2), entropy(freq2, qk=freq1)
    
def mutual_information(freq1, freq2):
    """ Performs the Kullback-Leibler divergence of the joint distribution with the product distribution of the marginals.
        freq1 and freq2 are probability distributions.
    """
    return mutual_info_score(freq1, freq2)
