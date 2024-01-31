import time
from typing import Optional
from qtpy import QtGui
from qtpy.QtCore import (
    Qt,
    Signal,
    QTimer,
)
from qtpy.QtWidgets import (
    # main
    QApplication,
    QMainWindow,
    QWidget,    

    # layout
    QGroupBox,    
    QVBoxLayout,
)
from .audio import InputStream
from .common import Block
from .estimators import *
from .timing import Clock
from .uitools import *
from .widgets import *


"""

Pipeline:


  - estimate_pitch:
    Estimate pitch in a block. Modifies block.
  - estimate_note:
    Estimate target note and cents from it.
  - update_ui:
    Render any widgets.
 
"""



class MainWindow(QMainWindow):
    
    """
    Parameters
    ----------
    instream: InputStream
      Must have a `read` method that returns an array.
    show: bool (optional)
    start: bool (optional)
    
    """
 
    # Estimators and processors
    instream: InputStream
    pitch_estimator: PitchEstimator
    intonation_estimator: IntonationEstimator

    # Widgets
    instream_widget: Optional[InputWidget]
    pitch_widget: Optional[PitchWidget]
    intonation_widget: IntonationWidget
    
    # State
    block: Optional[Block]
    _block_counter: int
    _block_timer: Clock
    
    _processing: bool = False
    
    
    # Signals
    processingStarted = Signal()
    processingStopped = Signal()
    blockProcessed = Signal(object)

            

    def __init__(self,
                 instream: Optional[InputStream] = None,
                 instream_widget: bool = False,
                 pitch_widget: bool = False,
                 ):
        super().__init__()
        
                                
        # Initialize core objects
        #------------------------
        
        # - Audio Input
        self.instream = instream or InputStream()
        self.block = None
        self._block_counter = 0
        self._block_timer = Clock(start=True)
        
        # - Pitch Estimator
        self.pitch_estimator = PitchEstimator(self.instream.samplerate)
        
        # - Intonation Estimator
        self.intonation_estimator = IntonationEstimator()
        
        
        self.init_ui(instream_widget=instream_widget, pitch_widget=pitch_widget)
        self.show()
        


    @property
    def processing(self) -> bool:
        return self._processing

    

    def init_ui(self,
                instream_widget: bool = False,
                pitch_widget: bool = False,
                ) -> None:
        
        self.setWindowTitle('MicroTune')
        
        # - Initialize a central widget and a main layout.
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.setAutoFillBackground(True)        
        
        # - Initialize widgets.
        
        self.instream_widget = None
        self.pitch_widget = None
        self.intonation_widget = None
        
        if instream_widget:
            
            # - Input Stream Widget
            self.instream_widget = InputWidget(self.instream, parent=self)
            self.blockProcessed.connect(self.instream_widget.update_ui)
            group = QGroupBox()
            group.setLayout(self.instream_widget.layout())
            group.setTitle("Input")
            layout.addWidget(group)
            
        if pitch_widget:
            
            # - Pitch Widget
            self.pitch_widget = PitchWidget(self.pitch_estimator, parent=self)
            self.blockProcessed.connect(self.pitch_widget.update_ui)
            group = QGroupBox()
            group.setLayout(self.pitch_widget.layout())
            group.setTitle("Pitch Estimator")
            layout.addWidget(group)
                    
        # - Intonation Widget
        self.intonation_widget = IntonationWidget(self.intonation_estimator, parent=self)
        self.blockProcessed.connect(self.intonation_widget.update_ui)
        group = QGroupBox()
        group.setTitle("Tuner")
        group.setLayout(self.intonation_widget.layout())
        layout.addWidget(group)
    
        n_widgets = 1 + int(instream_widget) + int(pitch_widget)
        width = 900
        height = n_widgets * 300
        self.setGeometry(50, 50, width, height)
        
        self.setFocusPolicy(Qt.ClickFocus)
        

        
    def start(self) -> None:
        """
        Create a timer that grabs data from the buffer.
        """
        if self._processing:
            return
        
        # Start input stream, and let it warm up long enough to fill the buffer.
        self.instream.start()
        time.sleep(0.4)
        
        # Update labels, state variables.
        self._processing = True
        self.processingStarted.emit()
        
        # Create and start the timer.
        self.timer = QTimer()
        self.timer.timeout.connect(self.process)
        self.timer.start(10)
        


    def stop(self) -> None:
        """
        Pause execution.
        """
        if not self._processing:
            return
        
        self.timer.stop()
        self._processing = False
        self.processingStopped.emit()
    
    
    def toggle_start_stop(self) -> None:
        
        if self._processing:
            self.stop()
        else:
            self.start()
        
        
        
    def process(self) -> None:
        """
        `self.timer.timeout` is connected to this method.
        
        Forces input to be mono, and handles optional resampling.
        Emits `audioChanged`.
                
        """
        
        if self._processing:
            
            # - create new block (including any preprocessing)
            # - estimate pitch
            # - estimate intonation
            # - update UI

            # Read from stream, and gather metadata to form the block.
            data = self.instream.read()
            if data.ndim > 1:
                data = data[:, 0]
            self.block = Block(
                data,
                index=self._block_counter,
                timestamp=self._block_timer(),
                samplerate=self.instream.samplerate,
            )
            self._block_counter += 1
            
            # Check for 'volume' gate.
            if len(self.block.data) == 0:
                return

            # Estimate pitch.            
            self.pitch_estimator.process(self.block)
                        
            # Estimate intonation.            
            self.intonation_estimator.process(self.block)

            self.blockProcessed.emit(self.block)


    #--------------------------------------------------------------------------#
    # Reimplemented methods


    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        
        key = event.key()
        mods = QApplication.queryKeyboardModifiers()        
        # Slide forward.
        if key == Qt.Key_Left:
            pass

        # Slide back.
        elif key == Qt.Key_Right:
            pass

        # Toggle looping.
        elif key == Qt.Key_Space:
            self.toggle_start_stop()
            

        # Quit/close.
        elif key == Qt.Key_Q and mods == Qt.ControlModifier:
            self.closeEvent(QtGui.QCloseEvent())


    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.stop()
        self.instream.close()





