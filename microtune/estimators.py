from collections import deque
import logging
from numbers import Number
from typing import Optional, Tuple
import numpy as np
import scipy.interpolate
import scipy.signal

from .common import Block
from .scales import Scale


__all__ = [
    "PitchEstimator",
    "IntonationEstimator",
]


class Peak:
            
    def __init__(self):
        pass



class PitchEstimator:

    """
    YIN pitch estimator.

    For a sound pitched at f, lag (in secs.) is 1 / f. To get this
    in samples, we have lag = fs * 1 / f = fs / f.

    Make the window size twice the longest lag. That way we don't have to worry
    about indexing errors
    The block/window size must be at least twice the longest lag.

    """
        
    # User-defined parameters for pitch detection.
    _samplerate: Number
    _fmin: Number    # cutoff for lowest frequency in restricted search range
    _fmax: Number    # cutoff for highest frequency in restricted search range
    min_thresh: Number
    abs_thresh: Number
    
    
    
    interp_half_width: int = 10    # in lag units
    interp_upsample_fac: int = 20
    
    # Computed attributes derived from user-defined attributes.    
    _lags: np.ndarray
    _lagmin: Number  # cutoff for highest frequency in restricted search range
    _lagmax: Number  # cutoff for lowest frequency in restricted search range
    
    history: dict
    
    # Keep for plotting.
    dn: np.ndarray

    onset_flag: bool = False  # true when onset has been found and pitch detection in progress
    onset_ix: int = 0
    onset_t: float = 0.0
    offset_t: float = 0.0
    
    onset_thresh = 0.15
    offset_thresh = 0.35
    offset_thresh_2 = 0.45
    integer_thresh = 0.1
    
    _history_attrs = (
        "ix_best",
        "dn_score",
        "pitch",
    )

    def __init__(self,
                 samplerate: float,
                 fmin: Number = 60.0,
                 fmax: Number = 1500.0,
                 min_thresh: float = 0.3,
                 abs_thresh: float = 0.1,
                 histlen: int = 20,
                 ):
                
        # Store user-defined parameters.
        self._samplerate = samplerate
        self._fmin = fmin
        self._fmax = fmax
        self.min_thresh = min_thresh
        self.abs_thresh = abs_thresh     

        self.history = {}
        for name in self._history_attrs:
            self.history[name] = deque(maxlen=histlen)
                
        
        self.init()
    
        

    @property
    def samplerate(self) -> Number:
        return self._samplerate

    @property
    def fmin(self) -> Number:
        return self._fmin

    @property
    def fmax(self) -> Number:
        return self._fmax

    @property
    def lags(self) -> np.ndarray:
        return self._lags



    """
    ---------------------------------------------------------------------------------
    - Estimator
    
    """
    
    def init(self) -> None:
        """
        Compute attributes necessary to run YIN pitch-estimation algorithm.
        Modifies:
         - self._lags    # Lags for preliminary search area.
         - self._weights # Normalization coefficients for preliminary search area.
         - self._lagmin  # Shortest lag in restricted search area.
         - self._lagmax  # Longest lag in restricted search area.

        """
        fs = self._samplerate
        fmin, fmax = self._fmin, self._fmax

        # Computation is on lags up to 40 Hz.
        self._lags = np.arange(int(np.ceil(fs / 40.0)), dtype=int)

        # Search range for valid pitches.
        self._cutoff = np.array([int(np.floor(fs / fmax)),
                                 int(np.ceil(fs / fmin))])
        

                
        

    def process(self, block: Block) -> None:
        """
        Use YIN error coefficients to estimate pitch.
        
        Modifies
         - block
         
         
        Note:

        - Peak indices are off from lag values by 1 (`self._lags[ix] = ix + 1`).
        
        """

        # Computed cumulative mean difference function and normalize it.
        # Keep a copy of the non-normalized version since we'll use it
        # during the interpolation stage.
        # - difference function
        data = block.data
        W = len(data) // 2 - 1
        
        d = np.array([np.sum((data[:W] - data[tau:tau+W])**2) for tau in self._lags])
        dn = np.ones_like(d)
        dn[1:] = d[1:] * self._lags[1:] / np.cumsum(d)[1:]
        
        block.d = d
        block.dn = dn

        #self.select_lag_yin(block)
        self.select_lag_0(block)
        
        if not block.tunable:
            return
        
        ix_best = block.ix_best
        pitch = self.peak_to_pitch(d, ix_best)
        dn_score = dn[ix_best]
        
        # Update state variables.
        self.append_history(ix_best=ix_best, pitch=pitch, dn_score=dn_score)
        
        # Update block.
        block.pitch = pitch
        block.dn_score = dn_score
        
        #if len(self.history["ix_best"]) < 5:
         #   block.tunable = False
        
        
    def find_minima(self, 
                    dn: np.ndarray,
                    height: Optional[float] = None,
                    ) -> np.ndarray:
        
        # Find minima in normalized difference function within search range.
        ixs, _ = scipy.signal.find_peaks(-dn, distance=5)
        lagmin, lagmax = self._cutoff
        ixs = ixs[(ixs >= lagmin) & (ixs <= lagmax)]
        if height is not None:
            ixs = ixs[dn[ixs] <= height]
        return ixs
    
    
    def upsample_peak(self,
                      d: np.ndarray,
                      ix: int,
                      ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns upsampled array of lags and difference function around
        the `ix`th index.
        """
        hw = self.interp_half_width
        lower = max(0, ix - hw)
        upper = min(ix + hw + 1, len(self._lags))
        x_in = np.arange(lower, upper)
        y_in = d[lower:upper]           # difference function in neighborhood
        interp_fn = scipy.interpolate.interp1d(x_in, y_in, kind="quadratic")
        x_out = np.linspace(x_in[0],
                            x_in[-1],
                            int(np.ceil(len(x_in) * self.interp_upsample_fac)))
        y_out = interp_fn(x_out)
        return x_out, y_out
    
    
    def peak_to_pitch(self,
                      d: np.ndarray,
                      ix: int,
                      ) -> Tuple[float, float]:
        
        X, Y = self.upsample_peak(d, ix)
        lag = X[np.argmin(Y)]
        return self._samplerate / lag
        

    
    def onset(self, ix: int, t: float) -> None:
        
        logging.debug("IntonationEstimator.onset()")
        self.onset_flag = True
        self.onset_ix = ix
        self.onset_t = t
        self.offset_t = 0
        
    
    def offset(self, t: float) -> None:
        
        logging.debug("IntonationEstimator.offset()")        
        for d in self.history.values():
            d.clear()
        self.onset_flag = False
        self.onset_ix = 0
        self.onset_t = 0.0
        self.offset_t = t
        
    
    
    def append_history(self, **kw):
        
        for key, val in kw.items():
            self.history[key].append(val)
        
    
    #--------------
    
    def select_lag_yin(self, block: Block):
        
        dn = block.dn
        ixs = self.find_minima(dn, height=self.min_thresh)
        if len(ixs) == 0:
            return            
        
        sub_ixs = ixs[dn[ixs] < self.abs_thresh]
        if len(sub_ixs) > 0:
            ix_best = sub_ixs[0]
        else:
            ix_best = ixs[np.argmin(dn[ixs])]
            
        block.ix_best = ix_best
        block.tunable = True
        
    
    
    def select_lag_0(self, block: Block):
                     
        
        dn = block.dn
        
        ixs = self.find_minima(dn, height=self.min_thresh)
        if len(ixs) == 0:
            if self.onset_flag:                
                self.offset(block.timestamp)
            return
                
        if self.onset_flag:
            # Onset found/pitch detection already in progress.
            # Check if 
            # 1) Same pitch found.
            # 2) harmonic found
            # 3) New pitch found
            
            # Start with YIN.
            sub_ixs = ixs[dn[ixs] < self.abs_thresh]
            if len(sub_ixs) > 0:
                ix_best = sub_ixs[0]
            else:                    
                ix_best = ixs[np.argmin(dn[ixs])]
                
            #ix_best = ixs[0]
            ix_ref = self.onset_ix
            log_ratio = np.log2((ix_best) / (ix_ref))

            if np.abs(log_ratio - np.round(log_ratio)) < self.integer_thresh:
                ix_near_ref = ixs[np.argmin(np.abs(ix_ref - ixs))]
                if dn[ix_near_ref] < self.offset_thresh_2:
                    ix_best = ix_near_ref
                    
                    # Logging...
                    cur_pitch = self._samplerate / ix_best
                    last_pitch = self._samplerate / ix_ref
                    stem = "found {} ({:.2f} Hz), ".format(ix_best, cur_pitch) + \
                           "target {} ({:.2f} Hz)".format(ix_ref, last_pitch) + \
                            ", delta={:.4f}".format(log_ratio)
                    if log_ratio < -self.integer_thresh:
                        logging.debug(" + too-high error corrected: " + stem)                        
                    elif log_ratio > self.integer_thresh:
                        logging.debug(" + too-low error corrected: " + stem)
                
                else:
                    # Pitch found is an integer multiple of the old, but the 
                    # old pitch is not well-represented in the difference function.
                    self.offset(block.timestamp)
            
            block.ix_best = ix_best
            block.tunable = True
        
        if not self.onset_flag:
            # First-time finding new pitch. Use stringent onset threshold.
            sub_ixs = ixs[dn[ixs] < self.onset_thresh]
            if len(sub_ixs) > 0:
                block.ix_best = sub_ixs[0]
                block.tunable = True
                self.onset(block.ix_best, block.timestamp)
                

    
class IntonationEstimator:

    #: Associated tuning system/scale.
    _scale: Optional[Scale] = None
    
    # State
    note: int
    note_buf: deque
    
    error: float
    error_buf: deque
    
    error_adj: float
    error_adj_buf: deque
    
    def __init__(self,                 
                 histlen: int = 20,
                 ):
        
        self.note = 0    
        self.note_buf = deque(maxlen=histlen)
        
        self.error = 0.0
        self.error_buf = deque(maxlen=histlen)
        
        self.error_adj = 0.0
        self.error_adj_buf = deque(maxlen=histlen)
        
        # Initialize default scale and tuning note.
        self._scale = Scale.from_file("EDO12")
        self._tn_note = 9
        self._tn_pitch = 440.0

            

    @property
    def scale(self) -> Scale:
        """
        Current scale.
        """
        return self._scale


    @scale.setter
    def scale(self, obj: Scale) -> None:
        self._scale = obj
        


    @property
    def tn_note(self) -> int:
        """
        Index of tuning note w.r.t. the scale.
        """
        return self._tn_note

    
    @tn_note.setter
    def tn_note(self, index: int) -> None:
        self._tn_note = index
        


    @property
    def tn_pitch(self) -> float:
        """
        Contents of tuning frequency text field as a number.
        """
        return self._tn_pitch
    
    
    @tn_pitch.setter
    def tn_pitch(self, freq: float) -> None:
        self._tn_pitch = freq
        
    
        


    """
    ---------------------------------------------------------------------------------
    - Processing/computation
    
    """


    def process(self, block: Block) -> None:
        """
        Find the note nearest to the estimated pitch (if any) and compute
        cents error.
        
        Modifies:
         - block
         - self
         
        """
        if not block.tunable:            
            self.note = -1
            self.note_buf.clear()
            
            self.error = 0.0
            self.error_buf.clear()
            
            self.error_adj = 0.0
            self.error_adj_buf.clear()

            block.note = -1
            block.error = 0.0
            block.error_adj = 0.0
            
            return
        
        scale = self._scale        
        tn_note: int = self._tn_note
        tn_cents: float = scale.cents[tn_note]
        tn_pitch: float = self._tn_pitch
        
        # Get the distance from the tonic to the pitch (in cents). Value will be in
        # [0, 1200) to match the scale note specification format.
        dist_from_tn = 1200 * np.log2(block.pitch / tn_pitch)
        dist_from_tonic = dist_from_tn + tn_cents
        dist_from_tonic = np.mod(dist_from_tonic, 1200)
        
        # Find scale note closest to the given pitch.
        scale = self._scale
        
        note = np.argmin(np.abs(dist_from_tonic - scale.cents))
        if note == len(scale) - 1 and \
            np.abs(dist_from_tonic - 1200) < np.abs(dist_from_tonic - scale.cents[-1]):
            note = 0
            error = dist_from_tonic - 1200
        else:            
            error = dist_from_tonic - scale.cents[note]
        
        # If this scale note is different from the last, clear history.
        if len(self.note_buf) > 0 and self.note_buf[-1] != note:            
            self.note_buf.clear()
            self.error_buf.clear()
            self.error_adj_buf.clear()
                    
        self.note_buf.append(note)
        self.error_buf.append(error)
        
        # Use contents of buffer to make estimates.
        arr = np.array(self.error_buf)              
        error_adj = np.mean(arr)
        
        self.note = note
        self.error = error
        self.error_adj = error_adj
        self.error_adj_buf.append(error_adj)
        
        block.note = note
        block.error = error
        block.error_adj = error_adj
