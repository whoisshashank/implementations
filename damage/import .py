import tensorflow as tf
from tensorflow import keras
import pandas as pd
import wget
import numpy as np

url = 'https://raw.githubusercontent.com/Apress/artificial-neural-networks-with-tensorflow-2/main/Ch05/student.csv'
filename = wget.download(url, 'student.csv')
print(f'\nFile downloaded to: {filename}')

df = pd.read_csv('student.csv')
print(df.head())

dataset = df.values
x= dataset[:,1]
y= dataset[:,0]

model = tf.keras.Sequential([tf.keras.layers.Dense(units=1, input_shape=[1])])
model.compile(optimizer = 'sgd', loss= 'mean_squared_error')

model.fit(x,y, epochs = 15)

result = model.predict(np.array([5.0]))
print("expected sat score for 5.0 gpa : {:.0f}".format(result[0][0]))