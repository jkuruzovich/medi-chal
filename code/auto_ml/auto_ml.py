# Imports
import numpy as np
import os
from sklearn.model_selection import train_test_split
import pandas as pd
from utilities import *
import processing
import normalization
import encoding
import imputation
import matplotlib.pyplot as plt
import seaborn as sns
import random

class AutoML():
    def __init__(self, input_dir="", basename="", test_size=0.2, verbose=False):
        """
            Constructor.
            Recover all autoML files available and build the AutoML structure containing them.
            :param input_dir: The directory where the autoML files are stored.
            :param basename: The name of the dataset (i.e. the prefix in the name of the files) 
                                Example : files = ('iris.data', iris_feat.name', etc.)
                                          basename = 'iris'
            :param test_size: Proportion of the dataset to include in the test split.
            :param verbose: Display additional information during run.
        """
        if os.path.isdir(os.path.join(input_dir, basename + '_automl')):
            self.input_dir = os.path.join(input_dir, basename + '_automl')
        elif os.path.isdir(input_dir):
            self.input_dir = input_dir
        else:
            raise OSError(
                'Input directory {} does not exist.'.format(input_dir))

        self.basename = basename
        if os.path.exists(os.path.join(self.input_dir, basename + '_train.data')) or \
         os.path.exists(os.path.join(self.input_dir, basename + '.data')):
            self.basename = basename
        else:
            raise OSError('No .data files found')

        # The subsets dictionnary contains the train/test and the X/y splits
        # Examples:
        #   subsets['train'] = [0, 1, 3, 4] (index of train rows)
        #   subsets['y'] = ['class'] (headers of y columns)
        self.subsets = dict()

        # Column names
        self.feat_name = self.load_name(
            os.path.join(self.input_dir, self.basename + '_feat.name'))
        self.label_name = self.load_name(
            os.path.join(self.input_dir, self.basename + '_label.name'))

        # Data
        self.data = None
        self.init_data(test_size=test_size)
        
        # Processed data
        self.processed_data = self.data.copy()

        # autoML info
        self.info = dict()
        self.init_info(
            os.path.join(self.input_dir, self.basename + '_public.info'), verbose=verbose)
            
        # Type of each variable
        self.feat_type = self.load_type(
            os.path.join(self.input_dir, self.basename + '_feat.type'))

        # Meta-features
        self.descriptors = dict()
        #self.compute_descriptors()

    @classmethod
    def from_df(cls, input_dir, basename, X, y=None):
        """
            Class Method
            Build AutoML structure from Pandas DataFrame.
            Generates autoML files from Pandas DataFrame, write them on disk and call the AutoML constructor.
            
            :param input_dir: The directory where the autoML files will be stored.
            :param basename: The name of the dataset.
            :param X: Dataset containing the samples.
            :param y: Dataset containing the labels (optional if no labels).
        """
        def write(filepath, X):
            np.savetxt(filepath, X, delimiter=' ', fmt='%s')

        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)

        input_dir += '/' + basename + '_automl'
        if not os.path.isdir(input_dir):
            os.mkdir(input_dir)


        path = input_dir + '/' + basename
        write(path + ".data", X.values)
        if X.columns.values.dtype == np.int64:
            X = X.add_prefix('X')
        write(path + "_feat.name", X.columns.values)
        write(path + "_feat.type", processing.get_types(X))

        if y is not None:
            write(path + ".solution", y.values)
            if isinstance(y, pd.Series):
                write(path + "_label.name", [y.name])
            else:
                write(path + "_label.name", y.columns)

        return cls(input_dir, basename)

    @classmethod
    def from_csv(cls, input_dir, basename, data_path, target=None, seps=[',', ','], headers=['infer', 'infer']):
        """
            Class Method
            Build AutoML structure from CSV file.
            Generates autoML files from CSV file, write them on disk and call the AutoML constructor.
            
            :param input_dir: The directory where the autoML files will be stored.
            :param basename: The name of the dataset.
            :param X: path of the .csv containing the samples.
            :param y: path of the .csv containing the labels (optional if no labels).
                           or column number (integer)
                           or list of column numbers (list of integers).
            :param header_X: header (parameter under review)
            :param header_y: header (parameter under review)
        """
        if os.path.exists(os.path.join(input_dir, data_path)):
            X = pd.read_csv(os.path.join(input_dir, data_path), sep=seps[0], header=headers[0])
        else:
            print(os.path.join(input_dir, data_path))
            raise OSError('{} file does not exist'.format(data_path))

        if isinstance(target, str) and os.path.exists(os.path.join(input_dir, target)):
            y = pd.read_csv(os.path.join(input_dir, y), sep=seps[1], header=headers[1])
        elif isinstance(target, int):
            y = pd.Series(X[X.columns[target]], name=X.columns[target])
            X = X.drop(X.columns[target], axis=1)
        elif isinstance(target, list):
            y = pd.DataFrame(X[X.columns[target]], columns=X.columns[target])
            X = X.drop(X.columns[target], axis=1)
        elif isinstance(target, str):
            y = pd.Series(X[target], name=target)
            X = X.drop([y], axis=1)
        else:
            y = None

        return cls.from_df(input_dir, basename, X, y)


    def init_data(self, test_size=0.2):
        """
            Load .data autoML files in a dictionary.
            
            :param test_size: If data is not splitted in autoML files, size of the test set.
                                Example : files = (i.e 'iris.data')
                                          test_size = 0.5
                                -> Data will be splitted 50% in X_train and 50% in X_test
            .. note:: If data is not splitted (i.e. no '_train.data', '_test.data'), samples are loaded in X.
        """
        
        self.subsets['X'] = self.feat_name
        
        if os.path.exists(
                os.path.join(self.input_dir, self.basename + '_train.data')):
            
            X_train = self.load_data(
                os.path.join(self.input_dir, self.basename + '_train.data'))
            
            X_test = self.load_data(
                os.path.join(self.input_dir, self.basename + '_test.data'))
            
            X = np.concatenate((X_train, X_test), axis=0)
            self.subsets['train'] = range(len(X_train))
            self.subsets['test'] = range(len(X_train), len(X_train) + len(X_test))
            
            # Create pandas dataframe
            self.data = pd.DataFrame(X, columns=self.feat_name)
            
            if os.path.exists(
                os.path.join(self.input_dir, self.basename + '_train.solution')):
                
                y_train = self.load_label(
                    os.path.join(self.input_dir, self.basename + '_train.solution'))
                
                y_test = self.load_label(
                    os.path.join(self.input_dir, self.basename + '_test.solution'))
                
                y = np.concatenate((y_train, y_test), axis=0)
                self.subsets['y'] = self.label_name
                
                # Create pandas dataframe
                y_df = pd.DataFrame(y, columns=self.label_name)
                self.data = pd.concat([self.data, y_df], axis=1)
                
        elif os.path.exists(
                os.path.join(self.input_dir, self.basename + '.data')):
            
            X = self.load_data(
                os.path.join(self.input_dir, self.basename + '.data'))

            # Create pandas dataframe
            self.data = pd.DataFrame(X, columns=self.feat_name)

            if os.path.exists(os.path.join(self.input_dir, self.basename + '.solution')):
                y = self.load_label(
                    os.path.join(self.input_dir, self.basename + '.solution'))
                self.subsets['y'] = self.label_name
                    
                # Create pandas dataframe
                y_df = pd.DataFrame(y, columns=self.label_name)
                self.data = pd.concat([self.data, y_df], axis=1)
 
            self.train_test_split(test_size=test_size)
            
        else:
            raise OSError('No .data files in {}.'.format(self.input_dir))


    def train_test_split(self, **kwargs):
        """ Apply the train test split
        """
        
        index = self.data.index.values
        
        shuffle = True
        if 'shuffle' in kwargs:
            shuffle = kwargs.get('shuffle')
        if shuffle:
            #random.shuffle(index)
            # We use sample to not modify or copy index
            shuffled_index = random.sample(list(index), len(index))
        
        test_size = 0.2
        if 'test_size' in kwargs:
            test_size = kwargs.get('test_size')
        split = int(test_size * len(index))
        
        self.subsets['train'] = shuffled_index[split:]
        self.subsets['test'] = shuffled_index[:split]


    def load_data(self, filepath):
        """
            Load a .data autoML file in an array.
            :param filepath: path of the file.
            :return: array containing the data. 
            :rtype: numpy array
        """
        return pd.read_csv(filepath, sep=' ', header=None).values if os.path.exists(filepath) \
          else []

    def load_label(self, filepath):
        """ 
            Load a .solution autoML file in an array.
            :param filepath: Path of the file.
            :return: Array containing the data labels. 
            :rtype: Numpy Array
        """
        return pd.read_csv(filepath, sep=' ', header=None).values if os.path.exists(filepath) \
          else []

    def load_name(self, filepath):
        """
            Load a _feat.name autoML file in an array.
            If None, return an array of variables [X1, ..., XN] (with N the number of features).
                   
            :param filepath: Path of the file.
            :return: Array containing the data names. 
            :rtype: Numpy Array
        """
        return pd.read_csv(filepath, header=None).values.ravel() if os.path.exists(filepath) \
          else None
          # When None is given to a pandas DataFrame, it automatically generate index
          #else ['X' + str(i) for i in range(self.info['feat_num'])]

    def load_type(self, filepath):
        """
            Load a _feat.type autoML file in an array.
            If None, compute it.
                   
            :param filepath: Path of the file.
            :return: Array containing the data types. 
            :rtype: Numpy Array
        """
        dtypes = []
        if os.path.exists(filepath):
            dtypes = pd.read_csv(filepath, header=None).values.ravel()
        else:
            dtypes = processing.get_types(self.get_data('X'))
        return dtypes

    def init_info(self, filepath, verbose=True):
        """
            Load a _public.info autoML file in a dictionary.
            If None, build the dictionary on its own.
                   
            :param filepath: Path of the file.
            :return: Dictionary containing the data information. 
            :rtype: Dict
        """
        if os.path.exists(filepath):
            df = pd.read_csv(
                os.path.join(self.input_dir, self.basename + '_public.info'),
                header=None,
                sep='=').values
            for x in df:
                x[0] = x[0].replace("'", '').strip()
                x[1] = x[1].replace("'", '').strip()
                # Convert numerical information in int instead of str
                for v in x[1]:
                    try:
                        x[1] = int(x[1])
                    except:
                        pass
            self.info = dict(zip(df[:, 0], df[:, 1]))

        else:
            if verbose:
                print('No info file found.')

            if os.path.exists(
                    os.path.join(self.input_dir, self.basename + '.data')):
                self.get_type_problem(
                    os.path.join(self.input_dir, self.basename + '.solution'))
            else:
                self.get_type_problem(
                    os.path.join(self.input_dir, self.basename + '_train.solution'))

            self.info['format'] = 'dense'
            self.info['is_sparse'] = 0
            self.info['train_num'], self.info['feat_num'] = self.get_data('X_train').shape
            if ('y' in self.subsets):
                self.info['target_num'] = self.get_data('y_train').shape[1]
                self.info['test_num'] = self.get_data('X_test').shape[0]
                assert (self.info['train_num'] == self.get_data('y_train').shape[0])
                assert (self.info['feat_num'] == self.get_data('X_test').shape[1])
                assert (self.info['test_num'] == self.get_data('y_test').shape[0])
                assert (self.info['target_num'] == self.get_data('y_test').shape[1])
            self.info['usage'] = 'No info file'
            self.info['name'] = self.basename
            self.info['has_categorical'] = 0
            self.info['has_missing'] = 0
            self.info['feat_type'] = 'mixed'
            self.info['time_budget'] = 600
            self.info['metric'] = 'r2_metric' if self.info['task'] == 'regression' else 'auc_metric'

        return self.info
        

    def get_data(self, s='', processed=False, array=False, verbose=True):
        """ 
            Return data as a pandas DataFrame.
            You can access different subsets with the 's' argument.
            Examples:
                get_data() returns all the data
                get_data('y') returns the class
                get_data('train') returns the train set, with X and y
                get_data('X_test') returns the X test set
            
            :param s: Wanted set (X, y_train, all, etc.)
            :param processed: If True, the method returns processed data.
                              Please use the method process_data() to change processing parameters.
            :param array: If True, the return type is ndarray instead of pandas DataFrame.
            :return: The data.
            :rtype: pd.DataFrame
        """
        
        if s in ['', 'all', 'data']:
            instances = self.data.index.values
            columns = self.data.columns.values
        
        # We split the data using self.subsets
        # Thanks to this, processings are done only once
        if '_' in s: # For example 'X_train' 
            c, i = s.split('_') # c = 'X', i = 'train'
            instances = self.subsets[i]
            columns = self.subsets[c]
        
        else:
            if s == 'X':
                instances = self.data.index.values
                columns = self.subsets['X']
            elif s == 'y':
                instances = self.data.index.values
                columns = self.subsets['y']
            elif s == 'train':
                instances = self.subsets['train']
                columns = self.data.columns.values
            elif s == 'test':
                instances = self.subsets['test']
                columns = self.data.columns.values
        
        # Get processed data
        if processed:
            if self.processed_data.equals(self.data) and verbose:
                print('Warning: data has not been processed yet. To process data, please use process_data method.')
            data = self.processed_data.loc[instances, columns]
        else:
            # at is a fast accessor
            # loc is slower but can manage subsets
            data = self.data.loc[instances, columns]
        
        # Get data as ndarray
        if array:
            return data.as_matrix() #data.values
            
        return data
        
        
    def set_data(self, values, s='', processed=False):
        if s in ['', 'all', 'data']:
            instances = self.data.index.values
            columns = self.data.columns.values
        
        # We split the data using self.subsets
        # Thanks to this, processings are done only once
        if '_' in s: # For example 'X_train' 
            c, i = s.split('_') # c = 'X', i = 'train'
            instances = self.subsets[i]
            columns = self.subsets[c]
        
        else:
            if s == 'X':
                instances = self.data.index.values
                columns = self.subsets['X']
            elif s == 'y':
                instances = self.data.index.values
                columns = self.subsets['y']
            elif s == 'train':
                instances = self.subsets['train']
                columns = self.data.columns.values
            elif s == 'test':
                instances = self.subsets['test']
                columns = self.data.columns.values
        
        if processed:
            self.processed_data.loc[instances, columns] = values
        else:
            self.data.loc[instances, columns] = values

    def save(self, out_path, out_name):
        """ Save data in auto_ml file format
        
            :param out_path: Path of output directory.
            :param out_name: Basename of output files.
        """
        def write_array(path, X):
            np.savetxt(path, X, fmt='%s')

        if not os.path.isdir(out_path):
            os.makedirs(out_path)

        write_array(
            os.path.join(out_path, out_name + '.data'),
            self.get_data('X'))
        write_array(
            os.path.join(out_path, out_name + '_feat.name'), 
            self.feat_name)

        if 'y' in self.data:
            write_array(
                os.path.join(out_path, out_name + '.solution'),
                self.get_data('y'))

        if 'X_train' and 'X_test' in self.data:
            write_array(
                os.path.join(out_path, out_name + '_train.data'),
                self.get_data('X_train'))
            write_array(
                os.path.join(out_path, out_name + '_test.data'),
                self.get_data('X_test'))
            if 'y_train' and 'y_test' in self.data:
                write_array(
                    os.path.join(out_path, out_name + '_test.solution'),
                    self.get_data('y_train'))
                write_array(
                    os.path.join(out_path, out_name + '_test.solution'),
                    self.get_data('y_test'))
                write_array(
                    os.path.join(out_path, out_name + '_label.name'),
                    self.label_name)

        with open(os.path.join(out_path, out_name + '_public.info'), 'w') as f:
            for key, item in self.info.items():
                f.write(str(key))
                f.write(' = ')
                f.write(str(item))
                f.write('\n')

    def get_type_problem(self, solution_filepath):
        """ 
            Get the type of problem directly from the solution file (in case we do not have an info file).
            :param solution_filepath: Path of the file
            :return: Type of the problem stored in the info dict attribute as 'task'
            :rtype: str
        """
        if 'task' not in self.info.keys() and 'y_train' in self.data:
            solution = pd.read_csv(
                solution_filepath, sep=' ', header=None).values
            target_num = solution.shape[1]
            self.info['target_num'] = target_num
            if target_num == 1:  # if we have only one column
                solution = np.ravel(solution)  # flatten
                nbr_unique_values = len(np.unique(solution))
                if nbr_unique_values < len(solution) / 8:
                    # Classification
                    self.info['label_num'] = nbr_unique_values
                    if nbr_unique_values == 2:
                        self.info['task'] = 'binary.classification'
                        self.info['target_type'] = 'binary'
                    else:
                        self.info['task'] = 'multiclass.classification'
                        self.info['target_type'] = 'categorical'
                else:
                    # Regression
                    self.info['label_num'] = 0
                    self.info['task'] = 'regression'
                    self.info['target_type'] = 'numerical'
            else:
                # Multilabel or multiclass
                self.info['label_num'] = target_num
                self.info['target_type'] = 'binary'
                if any(item > 1 for item in map(np.sum, solution.astype(int))):
                    self.info['task'] = 'multilabel.classification'
                else:
                    self.info['task'] = 'multiclass.classification'
        else:
            self.info['task'] = 'Unknown'
        return self.info['task']

    def process_data(self, norm='standard', code='label', missing=['most', 'most', 'median']):
        """ 
            Preprocess data.
            - Missing values inputation ('remove', 'mean', 'median', 'most', None)
            - +Inf and -Inf replaced by maximum and minimum
            - Encoding ('label', 'one-hot') for categorical variables
            - Normalization ('mean', 'min-max', None)
            
            Precision: processings are done first on the train set and then the parameters are used to process the test set.
            
            :param encoding: 'label', 'one-hot', 'likelihood'
            :param normalization: 'mean', 'min-max' 
            :param missing: 'remove', 'median', 'mean', None, or a list [binary, categorical, numerical]
            :return: Preprocessed data
            :rtype: pd.DataFrame
        """
        self.processed_data = self.data.copy() # Re initialization for data != processed_data case
        
        # Encoding
        self.encoding(code=code)
        
        # Imputation
        if isinstance(missing, str) or missing is None:
            self.imputation(binary=missing, categorical=missing, numerical=missing)
        else:
            self.imputation(binary=missing[0], categorical=missing[1], numerical=missing[2])
        
        # Normlization
        self.normalization(norm=norm)
        return self.processed_data


    def _impute(self, data, columns, how='remove'):

        imputed_data = data.copy()
        
        if how == 'remove':
            imputed_data = imputation.remove(imputed_data, columns)
            
        elif how == 'median':
            for column in columns:
                imputed_data = imputation.median(imputed_data, column)
                
        elif how == 'mean':
            for column in columns:
                imputed_data = imputation.mean(imputed_data, column)
                
        elif how == 'most':
            for column in columns:
                imputed_data = imputation.most(imputed_data, column)
                
        elif how is None or how in ['None', 'none']:
            # No imputation
            pass
            
        else: 
            raise OSError('{} imputation is not taken in charge'.format(how))
            
        return imputed_data

    
    def imputation(self, binary='most', categorical='most', numerical='median'):
        """
            Impute missing values.
            :param binary: 'remove', 'mean', 'median', 'most', None
            :param categorical: 'remove', 'mean', 'median', 'most', None
            :param numerical: 'remove', 'mean', 'median', 'most', None
            :return: data with imputed values.
            :rtype: pd.DataFrame

        """
        data = self.get_data('X', processed=True, verbose=False)

        # For Binary variables
        binary_columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if j=='Binary']].values
        data = self._impute(data, binary_columns, how=binary)

        # For Categorical variables
        categorical_columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if j=='Categorical']].values        
        data = self._impute(data, categorical_columns, how=categorical)

        # For Numerical variables
        numerical_columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if j=='Numerical']].values
        data = self._impute(data, numerical_columns, how=numerical)

        self.set_data(data, 'X', processed=True)

        return self.processed_data

    def normalization(self, norm='standard'):
        """
            Normalize the data
            :param norm: 'standard', 'min-max', None
            :return: normalized data
            :rtype: pd.DataFrame
        """
        train = self.get_data('X_train', processed=True, verbose=False)
        test = self.get_data('X_test', processed=True, verbose=False)

        numerical_columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if j=='Numerical']].values

        # For numerical variables
        for column in numerical_columns:
            # Standard normalization
            if norm == 'standard':
                train, (mean, std) = normalization.standard(train, column)
                test, _ = normalization.standard(test, column, mean, std)
            
            # Min-Max normalization
            elif norm == 'min-max':
                train, (mini, maxi) = normalization.min_max(train, column)
                test, _ = normalization.min_max(test, column, mini, maxi)
             
            #elif norm is None or norm in ['None', 'none']
        self.set_data(train, 'X_train', processed=True)
        self.set_data(test, 'X_test', processed=True)

        return self.processed_data

    def encoding(self, code='label'):
    
        train = self.get_data('X_train', processed=True, verbose=False)
        test = self.get_data('X_test', processed=True, verbose=False)

        columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if (j=='Binary' or j=='Categorical')]].values
        #categorical_columns = self.data.columns[[i for i, j in enumerate(self.feat_type) if j=='Categorical']].values

        # One-hot encoding: [0, 0, 1]
        if code=='one-hot':
            f = encoding.one_hot
            
        # Likelihood encoding
        elif code=='likelihood':
            f = encoding.likelihood

        # Label encoding: [1, 2, 3]
        elif code=='label':
            f = encoding.label

        # For binary and categorigal variables
        for column in columns:
                
            train, mapping = f(train, column)
            test, _ = f(test, column, mapping)

        self.set_data(train, 'X_train', processed=True)
        self.set_data(test, 'X_test', processed=True)

        return self.processed_data

    def compute_descriptors(self, processed=False):
        """ 
            Compute descriptors of the dataset and store them in the descriptors dictionary.
            - ratio: Dataset ratio
            - symb_ratio: Ratio of symbolic attributes
            - class_deviation: Standard deviation of class distribution
            - missing_proba: Probability of missing values
            - skewness_min: Minimum skewness over features 
            - skewness_max: Maximum skewness over features
            - skewness_mean: Average skewness over features
        """ # - defective_proba: Probability of defective records (columns with missing values)
        X = self.get_data('X', processed=processed)
        
        self.descriptors['ratio'] = int(self.info['feat_num']) / int(self.info['train_num'])
            
        self.descriptors['symb_ratio'] = list(self.feat_type).count('Numerical') / len(self.feat_type)
        
        if 'y' in self.subsets:
            y = self.get_data('y')
            self.descriptors['class_deviation'] = y.std().mean()
        
        self.descriptors['missing_proba'] = (X.isnull().sum() / len(X)).mean()
            
        skewness = X.skew()
        self.descriptors['skewness_min'] = skewness.min()
        self.descriptors['skewness_max'] = skewness.max()
        self.descriptors['skewness_mean'] = skewness.mean()
    

    def show_info(self):
        """ Show AutoML info 
        """
        for k in list(self.info.keys()):
            key = k.capitalize().replace('_', ' ')
            value = self.info[k]
            if isinstance(value, str):
                value = value.capitalize().replace('_', ' ').replace('.', ' ')

            print('{}: {}'.format(key, value))
          
    def show_feat_type(self):
        """ Display type of each variable (numerical, categorical, etc.)
        """
        df = pd.DataFrame(columns=self.feat_name)
        df.at['Type'] = self.feat_type
        display(df)


    def show_descriptors(self, processed=False):
        """ 
            Show numerical descriptors of the dataset.
            
            Descriptors:
            - ratio: Dataset ratio
            - symb_ratio: Ratio of symbolic attributes
            - class_deviation: Standard deviation of class distribution
            - missing_proba: Probability of missing values
            - skewness_min: Minimum skewness over features 
            - skewness_max: Maximum skewness over features
            - skewness_mean: Average skewness over features
        """
        self.compute_descriptors(processed=processed)
        
        for k in list(self.descriptors.keys()):
            key = k.capitalize().replace('_', ' ')
            value = self.descriptors[k]
            if isinstance(value, str):
                value = value.capitalize().replace('_', ' ').replace('.', ' ')

            print('{}: {}'.format(key, value))
            
    def show_pairplot(self, s='', processed=False, max_features=20):
        feat_num = int(self.info['feat_num'])
        if feat_num < max_features: # TODO selection, plot with y
            sns.set(style="ticks")
            print('Pairplot of {} set'.format(s))
            data = self.get_data(s, processed)
            sns.pairplot(data) 
            plt.show()
        else:
            print('Too much features to pairplot. Number of features: {}, max features to plot set at: {}'.format(feat_num, max_features))
    
    def show_correlation(self, s='', processed=False):
        print('Correlation matrix of {} set'.format(s))
        data = self.get_data(s, processed)
        show_correlation(data)
    
    def show_hierarchical_clustering(self, s='', processed=False):
        print('Hierarchical clustering heatmap of {} set'.format(s))
        data = self.get_data(s, processed)
        # row_method, column_method, row_metric, column_metric, color_gradient
        heatmap(data, 'average', 'single', 'euclidean', 'euclidean', 'coolwarm')
    
    def show_classes(self, s='', processed=False):
        print('Classes distribution of {} set'.format(s))
        data = self.get_data(s, processed)
        show_classes(data)
    
    def show_pca(self, x='X', y='y', processed=False):
        X = self.get_data(x, processed)
        Y = self.get_data(y, processed)
        lenx, leny = X.shape[0], Y.shape[0]
        if lenx == leny:
            print('Principal components analysis of {} and {} sets'.format(x, y))
            show_pca(X, Y)
        else:
            print('Could not show PCA because X has {} rows and Y has {} rows'.format(lenx, leny))
        
    def show_tsne(self, x='X', y='y', processed=False):
        X = self.get_data(x, processed)
        Y = self.get_data(y, processed)
        lenx, leny = X.shape[0], Y.shape[0]
        if lenx == leny:
            print('t-distributed stochastic neighbor embedding of {} and {} sets'.format(x, y))
            show_tsne(X, Y)
        else:
            print('Could not show t-SNE because X has {} rows and Y has {} rows'.format(lenx, leny))
        
    def show_lda(self, x='X', y='y', processed=False):
        X = self.get_data(x, processed)
        Y = self.get_data(y, processed)
        lenx, leny = X.shape[0], Y.shape[0]
        if lenx == leny:
            print('Linear discriminant analysis of {} and {} sets'.format(x, y))
            show_lda(X, Y)
        else:
            print('Could not show LDA because X has {} rows and Y has {} rows'.format(lenx, leny))
    
    #show skree
    
    #show bi plot
    
    def show_plots(self, sets=['X_train', 'X_test', 'y_train', 'y_test'], processed=False, max_features=20):
        """
            Show plots that describe the dataset.
            
            Plots:
            - Scatter plot features matrix
            - Classes distribution
            - Correlation matrix
            - Hierarchical clustering heatmap
            - First two principal components
            - First two LDA components
            - T-SNE plot
        """
        x_sets, y_sets = self.choose_sets(sets)
        
        if len(x_sets) > 0:
        
            printmd('** Scatter plot matrix **')
            for x in x_sets:
                self.show_pairplot(x, processed, max_features=max_features)
                    
            printmd('** Correlation matrix **')
            for x in x_sets:
                self.show_correlation(x, processed)

            printmd('** Hierarchical clustering heatmap **')
            for x in x_sets:
                self.show_hierarchical_clustering(x, processed)

        # If there is a class
        if len(y_sets) > 0:
        
            printmd('** Classes distribution **')
            for y in y_sets:
                self.show_classes(y, processed)
        
        if len(x_sets) > 0 and len(y_sets) > 0:
        
            printmd('** Principal components analysis **')
            for i in range(len(x_sets)):
                self.show_pca(x_sets[i], y_sets[i], processed)

            printmd('** t-distributed stochastic neighbor embedding **')
            for i in range(len(x_sets)):
                self.show_tsne(x_sets[i], y_sets[i], processed)

            printmd('** Linear discriminant analysis **')
            for i in range(len(x_sets)):
                self.show_lda(x_sets[i], y_sets[i], processed)
                
       
    def choose_sets(self, sets=[]):
        """ 
            Return sets for plot
            Examples: 
                all, X, y, train, test, X_train, X_test, y_train, y_test
            
            :param sets: Sets defined by user, may be wrong
            :return: Sets without errors in x_sets and y_sets
        """
        x_sets = []
        y_sets = []
        
        for s in sets:
            try:
                self.get_data(s)
                if 'y' in s:
                    y_sets.append(s)
                else:
                    x_sets.append(s)
                                        
            except Exception as e:
                print('Set {} does not exist.'.format(s))
                print(e)
                
        return x_sets, y_sets
                
    def show_characteristics(self, sets=['X_train', 'X_test', 'y_train', 'y_test'], processed=False, max_features=20):
        """ 
            Show characteristics of the dataset (numerical and plots).
            
            Numerical:
              See show_descriptors method
            
            Plots:
              See show_plots method
            
            :param sets: Sets to describe, by default 'X_train', 'X_test', 'y_train', 'y_test'
            :param processed: Boolean defining whether to display the
                                    descriptors of the raw data or the processed data
        """

        # Text
        printmd('** Descriptors **')
        self.show_descriptors(processed)

        print('')

        # Plots
        printmd('** Plots **')
        x_sets, y_sets = self.choose_sets(sets)
        self.show_plots(sets, processed, max_features=max_features)
              
