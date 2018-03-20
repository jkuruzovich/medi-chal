# Imports
import numpy as np
import os
from sklearn.model_selection import train_test_split
import pandas as pd
from utilities import *
import matplotlib.pyplot as plt
import seaborn as sns


class AutoML():
	def __init__(self, input_dir="", basename="", test_size=0, verbose=False):
		if os.path.isdir(input_dir):
			self.input_dir = input_dir
		else:
			raise OSError('Input directory {} does not exist.'.format(input_dir))

		self.basename = basename
		if os.path.exists(os.path.join(self.input_dir, basename + '_train.data')) or \
			os.path.exists(os.path.join(self.input_dir, basename + '.data')):
			self.basename = basename
		else:
			raise OSError('No .data files found')

		self.data = dict()
		self.init_data(test_size)

		self.info = dict()
		self.init_info(os.path.join(self.input_dir, self.basename + '_public.info'))
		self.init_type(os.path.join(self.input_dir, self.basename + '_feat.type'))

		self.feat_name = self.load_name(os.path.join(self.input_dir, self.basename + '_feat.name'))
		self.label_name = self.load_name(os.path.join(self.input_dir, self.basename + '_label.name'))

		self.descriptors = dict()
		self.compute_descriptors()

	@classmethod
	def from_df(cls, input_dir, basename, X, y=None):
		def write(filepath, X):
			np.savetxt(filepath, X, fmt='%s')

		path = input_dir + '/' + basename
		write(path + ".data", X.values)
		write(path + "_feat.name", X.columns.values)
		write(path + "_feat.type", X.dtypes)

		if y:
			write(path + ".solution", y.values)
			write(path + "_label.name", y.columns.values)

		return cls(input_dir, basename)

	@classmethod
	def from_csv(cls, input_dir, basename, X_path, y_path=None, X_header=None, y_header=None):
		if os.path.exists(X_path):
			X = pd.read_csv(input_dir + '/' + X_path, X_header)
		else:
			raise OSError('{} file does not exist'.format(X_path))
		y = pd.read_csv(input_dir + '/' + y_path, y_header) if os.path.exists(y_path) else None
		return cls.from_df(input_dir, basename, X, y)

	def init_data(self, test_size):
		if os.path.exists(os.path.join(self.input_dir, self.basename + '_train.data')):
			self.data['X_train'] = self.load_data(os.path.join(self.input_dir, self.basename + '_train.data'))
			self.data['y_train'] = self.load_label(os.path.join(self.input_dir, self.basename + '_train.solution'))
			self.data['X_test'] = self.load_data(os.path.join(self.input_dir, self.basename + '_test.data'))
			self.data['y_test'] = self.load_label(os.path.join(self.input_dir, self.basename + '_test.solution'))
		elif os.path.exists(os.path.join(self.input_dir, self.basename + '.data')):
			X = self.load_data(os.path.join(self.input_dir, self.basename + '.data'))
			if os.path.exists(os.path.join(self.input_dir, self.basename + '.solution')):
				y = self.load_label(os.path.join(self.input_dir, self.basename + '.solution'))
				self.data['X_train'], self.data['X_test'], self.data['y_train'], self.data['y_test'] = \
					train_test_split(X, y, test_size=test_size)
			else:
				self.data['X_train'] = X
		else:
			raise OSError('No .data files in {}.'.format(self.input_dir))

	def load_data(self, filepath):
		return pd.read_csv(filepath, sep=' ', header=None).values

	def load_label(self, filepath):
		return pd.read_csv(filepath, sep=' ', header=None).values if os.path.exists(filepath) else []

	def load_name(self, filepath):
		return pd.read_csv(filepath, header=None).values.ravel() if os.path.exists(filepath) else []

	def init_type(self, filepath):
		if os.path.exists(filepath):
			self.info['feat_type'] = pd.read_csv(filepath, header=None).values.ravel()
		else:
			print('No features type file found.')
			self.info['feat_type'] = [self.info['feat_type']] * self.info['feat_num']

	def init_info(self, filepath):
		if os.path.exists(filepath):
			df = pd.read_csv(os.path.join(self.input_dir, self.basename + '_public.info'), header=None, sep='=').values
			for x in df:
				x[0] = x[0].replace("'", '').strip()
				x[1] = x[1].replace("'", '').strip()
			self.info = dict(zip(df[:, 0], df[:, 1]))
		else:
			print('No info file file found.')

			if os.path.exists(os.path.join(self.input_dir, self.basename + '.data')):
				self.get_type_problem(os.path.join(self.input_dir, self.basename + '.solution'))
				# Finds the data format ('dense', 'sparse', or 'sparse_binary')   
				self.get_format_data(os.path.join(self.input_dir, self.basename + '.data'))

				self.get_nbr_features(os.path.join(self.input_dir, self.basename + '.data'))
			else:
				self.get_type_problem(os.path.join(self.input_dir, self.basename + '_train.solution'))
				# Finds the data format ('dense', 'sparse', or 'sparse_binary')   
				self.get_format_data(os.path.join(self.input_dir, self.basename + '_train.data'))

				self.get_nbr_features(
				os.path.join(self.input_dir, self.basename + '_train.data'), 
				os.path.join(self.input_dir, self.basename + '_test.data'), 
				os.path.join(self.input_dir, self.basename + '_valid.data'))

			self.info['usage'] = 'No info file'
			self.info['name'] = self.basename
			self.info['has_categorical'] = 0
			self.info['has_missing'] = 0   
			self.info['feat_type'] = 'Mixed'  
			self.info['time_budget'] = 600
			self.info['metric'] = 'r2_metric' if self.info['task'] == 'regression' else 'auc_metric'

		return self.info
		
	def get_data(self):
		return self.data
		
	def get_data_as_df(self):
		''' Get data as a dictionary of pandas DataFrame'''
		data = dict()
		data['X_train'] = pd.DataFrame(self.data['X_train'], columns=self.feat_name)
		data['y_train'] = pd.DataFrame(self.data['y_train'], columns=self.label_name)
		data['X_test'] = pd.DataFrame(self.data['X_test'], columns=self.feat_name)
		data['y_test'] = pd.DataFrame(self.data['y_test'], columns=self.label_name)
		return data
		
	def get_info(self):
		return self.info

	def get_format_data(self,filename):
		''' Get the data format directly from the data file (in case we do not have an info file)'''
		self.info['format'] = 'dense'
		self.info['is_sparse'] = 0			
		return self.info['format']

	def get_nbr_features(self, *filenames):
		''' Get the number of features directly from data (in case we do not have an info file)'''
		if 'feat_num' not in self.info.keys():
			self.get_format_data(filenames[0])
			if self.info['format'] == 'dense':
				data = pd.read_csv(filenames[0], sep=' ', header=None)
				self.info['feat_num'] = data.shape[1]
		return self.info['feat_num']
		
	def get_nbr_instances(self):
		''' Get the number of instances directly from data (in case we do not have an info file)'''
		
		self.info['train_num'] = self.data['X_train']
		self.info['valid_num'] 
		self.info['test_num']

	def get_type_problem(self, solution_filename):
		''' Get the type of problem directly from the solution file (in case we do not have an info file) '''
		if 'task' not in self.info.keys():
			solution = pd.read_csv(solution_filename, sep=' ', header=None).values
			target_num = solution.shape[1]
			self.info['target_num'] = target_num
			if target_num == 1: # if we have only one column
				solution = np.ravel(solution) # flatten
				nbr_unique_values = len(np.unique(solution))
				if nbr_unique_values < len(solution)/8:
					# Classification
					self.info['label_num'] = nbr_unique_values
					if nbr_unique_values == 2:
						self.info['task'] = 'binary.classification'
						self.info['target_type'] = 'Binary'
					else:
						self.info['task'] = 'multiclass.classification'
						self.info['target_type'] = 'Categorical'
				else:
					# Regression
					self.info['label_num'] = 0
					self.info['task'] = 'regression'
					self.info['target_type'] = 'Numerical'     
			else:
				# Multilabel or multiclass       
				self.info['label_num'] = target_num
				self.info['target_type'] = 'Binary' 
				if any(item > 1 for item in map(np.sum, solution.astype(int))):
					self.info['task'] = 'multilabel.classification'     
				else:
					self.info['task'] = 'multiclass.classification'        
		return self.info['task']
		
	def get_processed_data(self):
		''' Return preprocessed data as a dictionary or pandas DataFrame
			- Missing values inputation
			- +Inf and -Inf replaced by maximum and minimum
			- One hot encoding for categorical variables
		'''
		processed_data = dict()
		data_df = self.get_data_as_df()
		
		for k in list(data_df.keys()):
			processed_data[k] = preprocessing(data_df[k])
		
		return processed_data
		
	def compute_descriptors(self):
		''' Compute descriptors of the dataset and store them
			- Dataset ratio
		'''
		self.descriptors['ratio'] = int(self.info['feat_num']) / int(self.info['train_num'])
		
	def show_info(self):
		''' Show AutoML info '''
		for k in list(self.info.keys()):
			key = k.capitalize().replace('_', ' ')
			value = self.info[k]
			if isinstance(value, str):
				value = value.capitalize().replace('_', ' ').replace('.', ' ')

			print('{}: {}'.format(key, value))
		
	def show_descriptors(self):
		''' Show descriptors of the dataset 
			- Dataset ratio
			- Scatter plot features matrix
			- Classes distribution
			- Correlation matrix
			- Hierarchical clustering heatmap
			- First two principal components
			- First two LDA components
			- T-SNE plot
		'''
		
		# Text
		
		print('Dataset ratio (nbr features / nbr instances): {}\n'.format(self.descriptors['ratio']))
		
		# Plots
		
		x_sets = ['X_train']
		y_sets = ['y_train']
		# If there is a test set
		if(len(self.data['X_test']) > 0):
			x_sets.append('X_test')
			y_sets.append('y_test')
			
		data_df = self.get_data_as_df()
		
		print('Scatter plot matrix')
		sns.set(style="ticks")
		for x in x_sets:
			print(x)
			sns.pairplot(data_df[x])
			plt.show()
		
		print('Classes distribution')
		for y in y_sets:
			print(y)
			show_classes(data_df[y])
			
		print('Correlation matrix')
		for x in x_sets:
			print(x)
			show_correlation(data_df[x])
		
		print('Hierarchical clustering heatmap')
		row_method = 'average'
		column_method = 'single'
		row_metric = 'euclidean'#'cityblock' #cosine
		column_metric = 'euclidean'
		color_gradient = 'coolwarm'#'red_white_blue
		for x in x_sets:
			print(x)
			heatmap(data_df[x], row_method, column_method, row_metric, column_metric, color_gradient)
			
		print('Principal components analysis')
		for i in range(len(x_sets)):
			print(x_sets[i])
			print(y_sets[i])
			show_pca(data_df[x_sets[i]], data_df[y_sets[i]])
		
		# Linear discriminant analysis
		#if int(self.info['target_num']) > 2: # or label_num ?
		if False: # TODO
			print('Linear discriminant analysis')
			for i in range(len(x_sets)):
				print(x_sets[i])
				print(y_sets[i])
				show_lda(data_df[x_sets[i]], data_df[y_sets[i]])
			
		print('T-distributed stochastic neighbor embedding')
		for i in range(len(x_sets)):
			print(x_sets[i])
			print(y_sets[i])
			show_tsne(data_df[x_sets[i]], data_df[y_sets[i]])
