"""
Module that defines ``InputStream``, a class that listens
for audio from a sound device. It produces ``Block`` objects (a named tuple
also defined here) that contain discrete chunks of audio data which are
loaded into ``InputStream.q`` as well as sent to a callback function.

"""
import logging
from numbers import Number
import threading
from typing import (    
    Optional,
)

import numpy as np
import sounddevice as sd
from .circular_buffer import CircularBuffer



__all__ = [
    "InputStream",
]




class InputStream:

    """

    Wraps python-sounddevice input stream objects to enable the user to 
    modify attributes that can normally only be set at initialization-time.
    This is achieved by recreating the wrapped stream when necessary.

    In addition to this behavior, streams write to a circular buffer that
    is only copied and returned as a contiguous array when the buffer is read.
    This is meant to allow one to accumulate data from the callback function
    into a FIFO-like object with a capacity that is independent from the size
    of the individual writes. For example, the python-sounddevice streams often
    write in bursts shorter than one needs for estimating pitches. This class'
    buffer accumulates said bursts and stitches them together while continously
    writing over the oldest data.
    
    
    This object is thread-safe.
    
    
    
    
    Parameters
    ----------
    
    device: int (optional)
      Device number. If not given, will use first device found in query.
    channels: int (optional)
      Number of channels to read. If not given, all channels present in
      the device will be used.
    samplerate: Number (optional)
      If not specified, default for specified device will be used.
    burstsize: int (optional)
      Chunk size written to the buffer during the sound device's callback. If
      not specified, will write as often as possible.
    bufsecs: Number (optional)
      Size of buffered array in seconds. Determines how much audio will be processed
      during each iteration of the tuning loop.
    bufsize: Number (optional)
      Size of buffered array in samples. If both `bufsize` and `bufsecs` are given,
      `bufsize` will take precedence.
    
      
    """

    #: Wrapped sounddevice input stream.
    _stream: sd.InputStream

    #: `_buf` is a ciruclar array of a given size that stores
    #: the most recent audio signal. Its contents can be accessed as an array
    #: via `CircularBuffer.read()`.
    _buf: CircularBuffer

    #: Synchronization primitives.
    _lock: threading.Lock



    def __init__(self,
                 device: Optional[int] = None,
                 channels: Optional[int] = 1,
                 samplerate: Optional[Number] = None,
                 burstsize: int = 0,
                 bufsecs: Number = 0.1,
                 bufsize: Optional[int] = None,
                 ):

        
        # Initialize stream.
        if device is None:
            info = sd.query_devices(kind="input")
            info = info if isinstance(info, dict) else info[-1]
            name = info["name"]
            for i, d in enumerate(sd.query_devices()):
                if d["name"] == name:
                    device = i

        if not channels:
            channels = sd.query_devices(device)["max_input_channels"]

        self._stream = sd.InputStream(
            device=device,
            channels=channels,
            samplerate=samplerate,
            blocksize=burstsize,
            callback=self._write,
        )

        if bufsize is None:
            bufsize = round(bufsecs * self.samplerate)                
        self._buf = CircularBuffer((bufsize, self._stream.channels),
                                   fill_value=0,
                                   dtype=self._stream.dtype)

        # Thread-safety.
        self._lock = threading.Lock()


    @property
    def name(self) -> str:
        info = sd.query_devices(device=self.device)
        name = info["name"]
        return name

    @property
    def active(self) -> bool:
        """Whether the input device is streaming.
        """
        return self._stream.active


    @property
    def burstsize(self) -> int:
        """Number of samples written to the input buffer per write.
        """
        return self._stream.blocksize


    @burstsize.setter
    def burstsize(self, N: int) -> None:
        self._reinit(burstsize=N)


    @property
    def bufsize(self) -> int:
        """Maximum length of input buffer in samples.
        """
        return self._buf.maxshape[0]


    @bufsize.setter
    def bufsize(self, N: int) -> None:
        with self._lock:
            self._buf = CircularBuffer([N, self._stream.channels],
                                       dtype=self._stream.dtype)                                         

    @property
    def bufsecs(self) -> float:
        """Maximum length of input buffer in seconds.
        """        
        return self.bufsize / self.samplerate


    @bufsecs.setter
    def bufsecs(self, secs: Number) -> None:
        self.bufsize = round(secs * self.samplerate)


    @property
    def channels(self) -> int:
        """Number of channels streaming.
        """
        return self._stream.channels


    @channels.setter
    def channels(self, ch: int) -> None:
        self._reinit(channels=ch)


    @property
    def closed(self) -> bool:
        """Whether the stream is open.
        """        
        return self._stream.closed


    @property
    def device(self) -> int:
        """Device ID.
        """        
        return self._stream.device


    @device.setter
    def device(self, dev: int) -> None:
        self._reinit(device=dev)


    @property
    def dtype(self) -> type:
        """Datatype.
        """        
        return self._stream.dtype


    @property
    def samplerate(self) -> float:
        return self._stream.samplerate


    @samplerate.setter
    def samplerate(self, fs: Number) -> None:
        return self._reinit(samplerate=fs)



    def start(self) -> None:
        """
        Start the input stream.
        """

        if self.closed:
            self._reinit()
        logging.debug(f"starting stream: device={self.device}")
        with self._lock:
            self._stream.start()


    def stop(self) -> None:
        """
        Stop the input stream. Returns quietly if already stopped.
        """
        logging.debug(f"stopping stream: device={self.device}")
        with self._lock:
            self._stream.stop()
            self._buf.clear()
            


    def close(self) -> None:
        """
        Close the input stream. Returns quietly if already closed.
        """
        logging.debug(f"closing stream: device={self.device}")
        with self._lock:
            self._stream.stop()
            self._stream.close()


    def read(self) -> np.ndarray:
        # Read contents of buffer as an array.
        with self._lock:       
            return self._buf.read()
        

    def _reinit(self, **kw) -> None:
        """

        """
        with self._lock:

            settings = {
                "device" : self._stream.device,
                "blocksize" : self._stream.blocksize,
                "channels" : self._stream.channels,
                "samplerate" : self._stream.samplerate,
                "callback" : self._write,
            }
            if "burstsize" in kw:
                kw["blocksize"] = kw["burstsize"]
                del kw["burstsize"]
            settings.update(kw)          
            needs_start = self._stream.active
            self._stream.close()
            self._stream = sd.InputStream(**settings)
            self._buf = CircularBuffer((self.bufsize, self._stream.channels),
                                       fill_value=0,
                                       dtype=self._stream.dtype)
            if needs_start:
                self._stream.start()



    def _write(self, data: np.ndarray, *args) -> None:
        """
        Callback called by sd.InputStream.
        """
        with self._lock:            
            self._buf.write(data)



    def __repr__(self) -> str:

        s = f"<{self.name}: "
        s += f'device={self.device}, '
        s += f'active={self.active}, '
        s += f'closed={self.closed}, '
        s += f'channels={self.channels}, '
        s += f'samplerate={self.samplerate} Hz, '
        s += f'bufsize={self.bufsize} ({self.bufsize / self.samplerate} sec.)>'

        return s
