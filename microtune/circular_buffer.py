from numbers import Number
import threading
from typing import (
    Any,
    Optional,
    Tuple,
    Union,
)

import numpy as np



__all__ = [
    "CircularBuffer",
]



class CircularBuffer:
    
    """
    Thread-safe circular buffer with a numpy array-like interface.
    
    Optimized for many writes relative to reads. Once the data is read,
    a cached numpy array is created which expires once a write has occurred.
    
    Unlike typical buffers used for I/O, reading does not consume data.
    
    By default, getting the array-representation of a not-full 
    CircularBuffer will return an array with length equal to the number
    of elements written. However, if the user would prefer an array returned
    having the `maxshape` length, set `fill_value` to a non-`None` value.
                
    This was designed to outperform an alternative implementation that
    relied on numpy.roll after every write which creates a new array. This 
    is expensive when there are many small writes relative to the number
    of reads.
    
    """
    
    #: Underlying numpy array.
    _arr: np.ndarray
    
    #: Padding/value. If `None`, no padding/filling is done (the default behavior).
    _fill_value: Optional[Any]
    
    #: Indicates current read/write head.
    _head: int
    
    #: Indicates whether buffer is at capacity.
    _full: bool
    
    #: Cached array from last read request. Staleness is implemented
    #: by setting this to `None`.
    _cached: Optional[np.ndarray]

    #: Thread-safety
    _lock: threading.Lock
    
    
    def __init__(self,
                 maxshape: Union[int, Tuple[int, ...]],
                 dtype: Optional[type] = None,
                 fill_value = None,
                 ) -> None:
        
        
        # Initialize underlying array.
        self._fill_value = fill_value
        if self._fill_value is None:
            self._arr = np.zeros(maxshape, dtype=dtype)
        else:
            if np.isnan(self._fill_value) and np.issubdtype(dtype, np.integer):
                raise TypeError("cannot pad integer arrays with NaNs")
            self._arr = np.full(maxshape, self._fill_value, dtype=dtype)    
        
        # Initialize state.
        self._head = 0
        self._full = False
        
        # Initialize thread-safety and cacheing.
        self._lock = threading.Lock()
        self._cached = None


    @property
    def shape(self) -> Tuple[int, ...]:
        
        if self._full or self._fill_value is not None:
            return self._arr.shape
        return (self._head, *self._arr.shape[1:])
        
    
    @property
    def maxshape(self) -> Tuple[int, ...]:
        return self._arr.shape
    
    
    @property
    def dtype(self) -> type:
        return self._arr.dtype
    
    
    @property
    def fill_value(self) -> Optional[Number]:
        return self._fill_value
    
    
    @property
    def full(self) -> bool:
        return self._full
    
    
    def read(self) -> np.ndarray:
        """
        Thread-safe, cacheing read-interface.
        """
        with self._lock:
            if self._cached is None:
                self._cached = self._read()
            return self._cached
        
        
    def write(self, block: np.ndarray) -> None:
        """
        Thread-safe, cacheing write-interface.
        """
        with self._lock:
            self._write(block)
            self._cached = None
    
    
    def append(self, val: Any) -> None:
        """
        Append a single value to the buffer. Currently not-optimized, so it's
        equivalent to `CircularBuffer.write((val,)`.
        """
        self.write((val,))
        
        
    def clear(self) -> None:
        """
        Thread-safe clearing of data.
        """
        with self._lock:
            
            if self._fill_value is None:
                self._arr = np.zeros_like(self._arr)
            else:
                self._arr = np.full_like(self._arr, self._fill_value)
            
            self._head = 0
            self._full = False
            self._cached = None    
    
    
    def _read(self) -> np.ndarray:
        
        """
        Implements core reading logic.
        """
                
        # Read from full buffer.
        if self._full:
            if self._head == 0:   # - shortcut
                return np.copy(self._arr)
            return np.roll(self._arr, -self._head, axis=0)

        # Read from partially-full buffer.
        if self._fill_value is None:
            return self._arr[:self._head]
        return self._arr.copy()
            
    

    def _write(self, block: np.ndarray) -> None:
        
        """
        Implements core writing logic.
        """       
        
        blocklen = len(block)
        maxlen = self._arr.shape[0]
        
        # If length of the data to write is greater than or equal to the 
        # buffer capacity, simply reinitialize the buffer with the 
        # tail end of the block data.
        if blocklen >= maxlen:
            self._arr[:] = block[blocklen - maxlen:]
            self._head = 0
            self._full = True
            return
        
        # If there's enough free space to write without reaching capacity,
        # append it, and move the head.
        free = maxlen - self._head
        if blocklen <= free:
            self._arr[self._head:self._head + blocklen] = block
            self._head += blocklen
            if self._head == maxlen:
                self._head = 0
                self._full = True
            return
        
        # Write with wrap-around by doing two writes.
        new_head = blocklen - free
        self._arr[self._head:] = block[:free]
        self._arr[:new_head] = block[free:free + new_head]
        self._head = new_head
        self._full  = True
            
    
    def __array__(self) -> np.ndarray:
        return self.read()
    
    
    def __getitem__(self, key):
        return self.read()[key]
    
    
    def __len__(self) -> int:
        
        if self._full or self._fill_value is not None:
            return len(self._arr)
        return self._head


    def __repr__(self) -> str:
        header = f"CircularBuffer: " + \
                 f"length={len(self)}, " + \
                 f"dtype={self.dtype}, " + \
                 f"fill_value={self.fill_value}, " + \
                 f"maxshape={self.maxshape}\n"
        
        arr_str = repr(self.read())
        arr_str = arr_str.lstrip("array(")
        arr_str = arr_str.rstrip(")")
        out = header + " * " + arr_str
        
        return out
        
        
"""
To Do: testing
"""
        
def test_circular_buffer():
            
    
    # Test default behavior.
    a = CircularBuffer(5)

    a.write([0, 1, 2])
    assert np.array_equal(a, np.array([0, 1, 2]))

    a.write([3, 4, 5, 6])
    assert np.array_equal(a, np.array([2, 3, 4, 5, 6]))
    
    # Test use of fill-values.
    a = CircularBuffer(5, fill_value=0)
    
    a.write([0, 1, 2])
    assert np.array_equal(a, np.array([0, 1, 2, 0, 0]))    
    
    a.write([3, 4, 5, 6])
    assert np.array_equal(a, np.array([2, 3, 4, 5, 6]))

    # Test np.nan fill-values given integer input (cast to float)
    a = CircularBuffer(5, fill_value=np.nan)
    
    a.write([0, 1, 2])
    b = np.array([0.0, 1.0, 2.0, np.nan, np.nan])
    assert np.array_equal(a[:3], b[:3])
    assert np.all(np.isnan(a[3:]))
    
    a.write([3, 4, 5, 6])
    assert np.array_equal(a, np.array([2, 3, 4, 5, 6], dtype=float))
    