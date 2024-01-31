import json
from numbers import Number
from pathlib import Path
import platform
from typing import (
    ClassVar,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Union,
)

import numpy as np

from qtpy.QtCore import (
    Signal,
    QFile,
    QTextStream,
)

from qtpy.QtGui import (
    QPixmap,
)

from qtpy.QtWidgets import (
    # main
    QApplication,
    QWidget,

    # layout
    QLayout,
    QBoxLayout,
    QLayoutItem,
    QHBoxLayout,
    QVBoxLayout,
    QSpacerItem,
)

import pyqtgraph as pg
pg.setConfigOption("antialias", True)


__all__ = [
    "Application",
    "HBoxLayout",
    "VBoxLayout",
]





class BoxLayoutMixin:


    def add(self: QBoxLayout, obj: Union[QLayoutItem, QWidget]) -> None:

        if isinstance(obj, QWidget):
            self.addWidget(obj)
        elif isinstance(obj, QLayout):
            self.addLayout(obj)
        elif isinstance(obj, QSpacerItem):
            self.addSpacerItem(obj)
        elif isinstance(obj, QLayoutItem):
            self.addItem(obj)
        else:
            raise ValueError(f"could not add object of type {type(obj)} to layout")


    def extend(self, items: Iterable[Union[QLayout, QWidget]]) -> None:
        for obj in items:
            self.add(obj)

    def __getitem__(self, index: int) -> Union[QLayoutItem, QWidget]:
        return self.takeAt(index)

    def __iter__(self) -> Iterator:
        return iteritems(self)

    def __len__(self) -> int:
        return self.count()


def iteritems(layout: QBoxLayout):
    """
    Iterate through items in a box layout.
    """
    N = layout.count()
    for i in range(N):
        item = layout.takeAt(i)
        yield item






class HBoxLayout(QHBoxLayout, BoxLayoutMixin):

    def __init__(self,
                 items: Iterable[QWidget] = (),
                 parent: Optional[QWidget] = None,
                 ):

        super().__init__()
        if parent is not None:
            self.setParent(parent)
        if items:
            self.extend(items)



class VBoxLayout(QVBoxLayout, BoxLayoutMixin):

    def __init__(self,
                 items: Iterable[QWidget] = (),
                 parent: Optional[QWidget] = None,
                 ):

        super().__init__()
        if parent is not None:
            self.setParent(parent)

        if items:
            self.extend(items)



"""
--------------------------------------------------------------------------------
"""

import matplotlib as mpl


ColorLike = Union[str, Sequence[Number]]


def to_rgba(
    c: ColorLike,
    alpha: Optional[Number] = None,
    ) -> np.ndarray:
    """
    floating point, with alpha
    """
    out = mpl.colors.to_rgba(c, alpha=alpha)
    out = np.array(out) if isinstance(out, tuple) else out
    return out



def to_rgb(
    c: ColorLike,
    alpha: Optional[Number] = None,
    ) -> np.ndarray:
    """
    floating point, no alpha
    """
    out = to_rgba(c, alpha)
    out = out[..., 0:3]
    return out


def to_RGBA(
    c: ColorLike,
    alpha: Optional[Number] = None,
    ) -> np.ndarray:
    """
    8-bit, with alpha
    """
    out = to_rgba(c, alpha)
    out = (255 * out).astype(np.uint8)
    return out


def to_RGB(
    c: ColorLike,
    alpha: Optional[Number] = None,
    ) -> Union[np.ndarray]:
    """
    8-bit, no alpha
    """
    out = to_RGBA(c, alpha)[..., 0:3]
    return out




class Style:


    def __init__(self):
        self.path = Path(__file__).parent.parent / 'resources' / 'style'

        # Load 'qstyle.qss'.
        f = QFile(str(self.path / 'qstyle.qss'))
        f.open(QFile.ReadOnly | QFile.Text)
        self._style_sheet = QTextStream(f).readAll()

        if platform.system().lower() == 'darwin':
            mac_fix = '''
            QDockWidget::title
            {
                background-color: #31363b;
                text-align: center;
                height: 12px;
            }
            '''
            self._style_sheet += mac_fix

        # If theme has a colors.json file, read it. ??
        self.colors = {}
        with open(str(self.path / 'colors.json'), 'r') as f:
            self.colors = json.load(f)


    @property
    def style_sheet(self):
        return self._style_sheet

    def load_pixmap(self, name):
        return QPixmap(str(self.path / name))



_STYLE = None


def get_style() -> Style:
    global _STYLE
    if _STYLE is None:
        _STYLE = Style()
    return _STYLE



"""
--------------------------------------------------------------------------------
"""


class Application:

    """
    Singleton-class designed to enable programs to create and destroy 
    Qt-based applications several times throughout the program's execution.
    
    
    
    QApplication designed to enable Qt-based tools to be
    created and destroyed multiple times during a program's execution.

    Manages execution and cleanup of qt, including gevent integration
    for interactive consoles. The cleanup allows one to start and run
    a qt applications several times in the same session by
    connecting QApplication.aboutToQuit to QApplication.deleteLater.

    """



    #: Singleton application instance.
    _instance: ClassVar[Optional["Application"]] = None

    #: Wrapped QApplication.
    _qapp: ClassVar[Optional[QApplication]] = None

    _reusable: bool = False


    def __new__(cls, *args, **kw):

        if cls._instance is not None:
            return cls._instance

        cls._instance = self = object.__new__(cls)
        self.init_qapp(*args, **kw)

        return self


    def reusable(self) -> bool:
        return self._reusable


    def setReusable(self, tf: bool) -> None:
        self._reusable = tf


    @property
    def aboutToQuit(self) -> Signal:
        return self._qapp.aboutToQuit


    def qapp(self) -> QApplication:
        return self._qapp


    def init_qapp(self):

        if self._qapp is not None:
            return self._qapp

        # Create the qapp.
        self._qapp = qapp = QApplication.instance()
        if qapp is None:
            self._qapp = qapp = QApplication([])
            self._created_qapp = True
        else:
            self._created_qapp = False

        # Schedule for destruction.
        if self._created_qapp:
            qapp.aboutToQuit.connect(qapp.deleteLater)


    def exec(self) -> None:

        self.init_qapp()

        try:
            self._qapp.exec_()
            error = None
        except Exception as e:
            error = e

        self.cleanup(error)


    def cleanup(self, error: Optional[Exception] = None) -> None:
        self._qapp = None
        if self._reusable:
            self.init_qapp()
        if error:
            raise error


    def quit(self) -> None:
        self._qapp.quit()


    @classmethod
    def instance(cls) -> Optional["Application"]:
        return cls._instance


