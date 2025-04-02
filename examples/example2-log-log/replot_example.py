import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

line = pd.read_csv("lines.csv")
line_idxs = range(int(len(line.columns)/2))

for idx in line_idxs:
    plt.plot(line["x%u" % idx],line["y%u" % idx],c="r",linestyle="-.")
    plt.scatter(line["x%u" % idx],line["y%u" % idx],c="k",s=10,zorder=100,marker="x")
plt.xlabel("x")
plt.ylabel("y")
plt.gca().set_xscale("log",base=2)
plt.gca().set_yscale("log")
plt.savefig("example-replotted.png")
plt.show()
