from collections import deque
import logging
import time
import sys
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from microtune.audio import InputStream
from microtune.common import Block
from microtune.driver import *
from microtune.timing import Clock
from microtune.uitools import Application


#--------------------------------------
# - Testing parameters

TESTING = True

MAXBLOCKS = 10
MAXVALUES = 1000
BLOCK_ATTRS_TO_STORE = [
    "timestamp",
    "pitch",
    "note",
    "error",
    "error_adj",
    "rms",
    "dn",
]


def store_block(block: Block):

    block.rms = np.sqrt(np.mean(block.data**2))
    block.dn = block.dn
    
    BLOCKS.append(block)
    for key in BLOCK_ATTRS_TO_STORE:
        DATA[key].append(getattr(block, key))
    

#--------------------------------------
# - Create and run the app

logging.basicConfig(level=logging.DEBUG)

app = Application()
instream = InputStream(device=0)
drv = MainWindow(
    instream,
    instream_widget=False,
    pitch_widget=True,
)

drv.intonation_widget.pitch_estimator = drv.pitch_estimator

if TESTING:
    DATA = {}
    BLOCKS = deque(maxlen=MAXBLOCKS)
    for name in BLOCK_ATTRS_TO_STORE:
        DATA[name] = deque(maxlen=MAXVALUES)
    drv.blockProcessed.connect(store_block)

clock = Clock()
clock.start() 
drv.start()
app.exec()
t_tot = clock.stop()

pe = drv.pitch_estimator
ie = drv.intonation_estimator


if TESTING:        
    
    for key, val in DATA.items():
        DATA[key] = np.array(val)
        
    timestamps = DATA["timestamp"]
    n_iters = len(timestamps)
    dts = np.ediff1d(timestamps)
    fps = 1 / np.mean(dts)
    print("Ran {} loops in {:.1f} secs".format(n_iters, t_tot))
    print("FPS: {:.2f}".format(fps))
            
    data_arrays = np.array([b.data for b in BLOCKS])
    DATA["data"] = data_arrays
    data_file = Path(__file__).parent / "testing_data.npy"
    np.save(data_file, DATA, allow_pickle=True)
    
    