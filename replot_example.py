import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

points = pd.read_csv("points.csv")
points = points.to_numpy().reshape((int(len(points.columns)/2),2))
line = pd.read_csv("line.csv")

plt.scatter(*points.T,c=range(0,len(points)),cmap="viridis")
plt.plot(line["x0"],line["y0"])
plt.xlabel("x")
plt.ylabel("y")
plt.show()
