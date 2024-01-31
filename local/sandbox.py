from pathlib import Path
from types import SimpleNamespace
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks

data_file = Path(__file__).parent / "testing_data.npy"
DATA = np.load(data_file, allow_pickle=True).item()
timestamps = DATA["timestamp"]
pitches = DATA["pitch"]
notes = DATA["note"]
errors = DATA["error"]
err = DATA["error_adj"]
dns = DATA["dn"]

self = SimpleNamespace()

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
dn = dns[-1]

#ax.plot(dn)

fs = 48000

W = len(dn) // 2
L = np.arange(W - 1)
x = np.array([np.sum((dn[:W] - dn[tau:tau+W]**2)) for tau in L])

ax.plot(L, x)