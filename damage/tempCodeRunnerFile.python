import tensorflow as tf 
import pandas as pd 
import requests 
import io
import matplotlib.pyplot as plt 
import wget

url = 'https://raw.githubusercontent.com/Apress/artificial-neural-networks-with-tensorflow-2/main/Ch05/winequality-white.csv'


dataset = pd.read_csv(url, sep = ';')
x = dataset.drop('quality', axis = 1)
y =  dataset['quality']
dataset.tail() 

from sklearn.model_selection import train_test_split
x_train_1 , x_test , y_train_1 , y_test =  train_test_split(x, y, test_size = 0.15, random_state = 0) 
x_train , x_val , y_train , y_val = train_test_split(x_train_1, y_train_1, test_size = 0.05, random_state = 0) 

from sklearn.preprocessing import StandardScaler
sc_x = StandardScaler()
x_train_new = sc_x.fit_transform(x_train)

fig, (ax1, ax2) = plt.subplots(ncols = 2, figsize = (20, 10))
ax1.scatter(x_train.index, x_train['fixed acidity'], color = 'green', label= 'raw', alpha = 0.4, marker = '.') 
ax2.scatter(x_train.index, x_train_new[:,1], color = 'red', label = 'adjusted', alpha = 0.4, marker = '.')
ax1.set_title('Training dataset')
ax2.set_title('Standardized training dataset')

for ax in (ax1, ax2):
    ax.set_xlabel('index')
    ax.set_ylabel('fixed acidity')
    ax.legend(loc = 'upper right')
    ax.grid()
plt.tight_layout()
plt.show()

fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(20, 10))

for l, c, m in zip(range(0, 2), ('blue', 'red'), ('^', 's')):
    ax1.scatter(x_train['residual sugar'], x_train['total sulfur dioxide'], 
                color=c, label=f'class {l}', alpha=0.4, marker=m)

for l, c, m in zip(range(0, 2), ('blue', 'green'), ('^', 's')):
    ax2.scatter(x_train_new[:, 3], x_train_new[:, 6], 
                color=c, label=f'class {l}', alpha=0.4, marker=m)

ax1.set_title('training dataset')
ax2.set_title('standardised training dataset')

for ax in (ax1, ax2):
    ax.set_xlabel('residual sugar')          # fixed typo
    ax.set_ylabel('total sulfur dioxide')
    ax.legend(loc='upper right')
    ax.grid()

plt.tight_layout()
plt.show()

x_test_new = sc_x.transform(x_test)
x_val_new = sc_x.transform(x_val)
