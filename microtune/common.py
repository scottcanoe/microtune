from numbers import Number
from pathlib import Path
from typing import (
    Optional,
    Union,
)
import numpy as np

__all__ = [
    
    # Typing
    "PathLike",
    
    # Files and resources
    "resource_dir",
    "scale_dir",
        
    # etc.
    "Block",
    "cents_difference",
]


PathLike = Union[str, Path]


"""
-------------------------------------------------------------------------------------
- Files and resources
"""


_RESOURCE_ROOT = Path(__file__).parent.parent / "resources"
def resource_dir() -> Path:
    return _RESOURCE_ROOT


def scale_dir() -> Path:
    return resource_dir() / "scales"



"""
-------------------------------------------------------------------------------------
- Audio

"""

        
        
def cents_difference(x: Number, y: Number) -> float:
    """
    Get the displacement between two frequencies in cents. If `x` < `y`, cents
    will be negative.
    """
    return 1200 * np.log2(y / x)


    

class Block:
    
    """
    A chunk of audio input, typically the complete contents of an input buffer.
    """
    
    _data: np.ndarray
    _index: int
    _timestamp: Number
    _samplerate: Number
    
    # preprocessing
    rms: float = 0.0
    
    # pitch estimation
    d: Optional[np.ndarray] = None
    dn: Optional[np.ndarray] = None
    ixs: Optional[np.ndarray] = None
    tunable: bool = False
    
    ix_best = 0
    pitch: float = -1.0
    
    # intonation estimation
    note: int = -1
    error: float = 0.0
    error_adj: float = 0.0
    
    
    def __init__(self,
                 data: np.ndarray,
                 index: int,
                 timestamp: float,
                 samplerate: float,
                 ):
        
        self._data = data
        self._index = index
        self._timestamp = timestamp
        self._samplerate = samplerate
    
    
    @property
    def data(self) -> np.ndarray:
        return self._data
    
    @property
    def index(self) -> int:
        return self._index

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def samplerate(self) -> int:
        return self._samplerate



    def __repr__(self) -> str:
        
        s = f"<Block({self.index}): " + \
            "timestamp={:.2f} sec, ".format(self.timestamp)
        
        if self.pitch is None:
            s += "pitch=None, "
        else:
            s += "pitch={:.2f} Hz, ".format(self.pitch)
        
        s += ">"
        
        return s
    
            
            

