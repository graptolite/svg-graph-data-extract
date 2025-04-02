import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

line = pd.read_csv("faults.csv")
line_idxs = range(int(len(line.columns)/2))

fig = plt.figure()
map_ax = fig.add_subplot(1,2,1)
faults = []
for idx in line_idxs:
    map_ax.plot(line["x%u" % idx],line["y%u" % idx],c="darkred")
    faults.append([p for p in line[["x%u" % idx,"y%u" % idx]].to_numpy() if ~np.isnan(p[0])])

coast = pd.read_csv("coastline.csv")
map_ax.plot(coast["x0"],coast["y0"],c="lightgreen",zorder=-1)

map_ax.set_xlabel("lon")
map_ax.set_ylabel("lat")
map_ax.set_aspect("equal")
map_ax.set_title("Map")

fault_strikes = [np.arctan2(*((f[-1]-f[0]))) for f in faults]
# Convert to 0,180 range
fault_strikes = np.degrees(np.array(fault_strikes))%(180)
circ_ax = fig.add_subplot(1,2,2,projection="polar")
counts,edges = np.histogram(fault_strikes,bins=np.arange(0,361,30))
circ_ax.bar(np.radians((edges[1:]+edges[:-1])/2),counts)
circ_ax.set_theta_zero_location("N")
circ_ax.set_theta_direction(-1)
circ_ax.set_thetamin(0)
circ_ax.set_thetamax(180)
circ_ax.set_title("(Overall) Fault orientations")
plt.savefig("example-replotted.png")
plt.show()
