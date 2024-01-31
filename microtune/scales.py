import json
from typing import (
    Dict,
    Mapping,
    Optional,
    Union,
)

import numpy as np

from .common import (
    PathLike,
    scale_dir,
)


__all__ = [
    "Note",
    "Scale",
]


def default_note_names() -> Dict:

    return {
        0 : "C",
        1 : "C#/Db",
        2 : "D",
        3 : "D#/Eb",
        4 : "E",
        5 : "F",
        6 : "F#/Gb",
        7 : "G",
        8 : "G#/Ab",
        9 : "A",
        10 : "A#/Bb",
        11 : "B",
    }



class Note:
            
    # From definition
    index: Optional[int] = None
    name: Optional[str] = None
    cents: Optional[float] = None
    
    # From estimation
    pitch: float = 0.0

    
    
    def __init__(self, index: int, name: str, cents: float):
        self._index = index
        self._name = name
        self._cents = cents


    @property
    def index(self) -> int:
        return self._index
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def cents(self) -> float:
        return self._cents
        
        
    def __repr__(self) -> str:
        
        attrs = [            
            "index",
            "name",
            "cents",
        ]
        
        lst = [f"{key}={getattr(self, key)}" for key in attrs]
        lst_s = ", ".join(lst)
        
        s = f"<Note: {lst_s}>"
        return s
    
        
class Scale:

    """

    Represents a tuning system/scale. Each note is associated defined
    by its number of cents above the zeroth note. Note names can
    also be supplied, and default note names are applied if needed/possible.

    Internally, an index

    """

    _scale_name: str
    _cents: np.ndarray
    _names: np.ndarray
    _note_objects: np.ndarray

    @property
    def scale_name(self) -> str:
        return self._scale_name

    
    @property
    def cents(self) -> np.ndarray:
        """Cents above fundamental."""
        return self._cents

    
    @property
    def names(self) -> np.ndarray:
        return self._names
    
    
    @property
    def notes(self) -> np.ndarray:
        return self._note_objects
    
    
    @classmethod
    def from_dict(cls, dct: Mapping) -> "Scale":
        """
        Create a `Scale` object given a dictionary containing well-formed
        data.
        
        "name" : Name of scale. Optional.
        
        "notes" : Dictionary with integer (scale degree) -> float (cent above 
        fundamental) pairs.
        
        "note_names" : Dictionary with integer (scale degree) -> string (note name)
        pairs.
        
        
        """
        
        out = Scale()
        
        # - set name
        out._scale_name = dct["name"]

        # - read cent values
        cents_dict = dct["notes"]        
        out._cents = np.zeros(len(cents_dict), dtype=float)
        for key, val in cents_dict.items():
            out._cents[int(key)] = val
        
        # - read note names
        names_dict = dct.get("note_names", default_note_names())
        out._names = np.zeros(len(names_dict), dtype=object)
        for key, val in names_dict.items():
            out._names[int(key)] = val

        # - Get mapping from note names to indices.        
        out._name_to_index = {}
        for i, name in enumerate(out._names):
            out._name_to_index[name] = i
            if "/" in name:
                for elt in name.split("/"):
                    out._name_to_index[elt] = i
        
        # Do some light checking?
        assert len(out._cents) == len(out._names)
        assert out._cents[0] == 0.0
        assert np.all(np.ediff1d(out._cents) > 0)
        assert np.all(out._cents >= 0)
        assert np.all(out._cents < 1200)
        
        # Make note objects.
        out._note_objects = np.zeros(len(out._cents), dtype=object)
        for i in range(len(out._cents)):
            obj = Note(i, out._names[i], out._cents[i])
            out._note_objects[i] = obj
        
        return out


    @classmethod
    def from_file(cls, path: PathLike) -> "Scale":

        path = scale_dir() / path
        if not path.exists() and path.with_suffix(".json").exists():
            path = path.with_suffix(".json")

        with open(path, "r") as f:
            dct = json.load(f)

        return Scale.from_dict(dct)


    #-------------------------------------------------------------------------------#

        

    
    #-------------------------------------------------------------------------------#
    
    
    def __getitem__(self, key: Union[int, str]) -> Note:
        if isinstance(key, int):
            return self._note_objects[key]
        if isinstance(key, str):    
            ind = self._name_to_index[key]
            return self._note_objects[ind]
        raise IndexError(key)

    
    def __len__(self):
        return len(self._cents)


    def __repr__(self):
        s  = f"Scale('{self._scale_name}')\n"
        s += "-" * (len(s) - 1) + "\n"
        lst = []
        for i in range(len(self)):
            name = self._names[i]
            cents = self._cents[i]            
            lst.append('- {:<3} | {:<5} | {:>6.1f}'.format(i, name, cents))

        s += "\n".join(lst)

        return s


