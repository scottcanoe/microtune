from pathlib import Path
from typing import Dict, Optional

import numpy as np
import scipy.stats
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QFont
from qtpy.QtWidgets import (
    # main
    QWidget,

    # widgets
    QComboBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,

    # layout
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
)
import pyqtgraph as pg
from pyqtgraph.parametertree import (
    Parameter,
    ParameterTree,
)

from .common import Block, scale_dir
from .scales import Scale
from .uitools import HBoxLayout


__all__ = [
    "InputWidget",
    "PitchWidget",
    "IntonationWidget",
]


class InputWidget(QWidget):


    instream: "InputStream"

    label_widths = 125
    field_widths = 50
    
    ignore_update: bool = False

    def __init__(self,
                 instream: "InputStream",
                 parent: Optional[QWidget] = None,
                 ):
        super().__init__(parent=parent)


        self.instream = instream

        # - Controls

        # - - start button
        self.start_btn = QPushButton('Start')
        self.start_btn.clicked.connect(self.on_start_btn_clicked)

        # - - buffer size controller
        bufsize = instream.bufsize
        bufsecs = bufsize / instream.samplerate
        bufsecs_label = QLabel('buffer size (sec)')
        bufsecs_label.setFixedWidth(self.label_widths)
        self.bufsecs_field = bufsecs_field = QLineEdit()
        bufsecs_field.setText('{:.3f}'.format(bufsecs))
        bufsecs_field.setFixedWidth(self.field_widths)
        bufsecs_field.returnPressed.connect(self.on_bufsecs_field_edited)        

        # - waveform viewer
        X = np.linspace(-bufsecs, 0, bufsize)
        Y = np.zeros(len(X))
        self.signal_plot = pg.PlotItem()
        self.signal_curve = self.signal_plot.plot(X, Y)
        self.signal_plot.setLabel('bottom', 'time (sec)')
        self.signal_plot.setLabel('left', 'intensity')
        self.signal_plot.setYRange(-0.5, 0.5)

        # - RMS indicator
        X = np.array([0.5])
        Y = np.array([0])
        self.rms_val = 0.0
        self.rms_plot = pg.PlotItem()
        self.rms_bar = pg.BarGraphItem(x=X, width=1, height=Y, brush='r')
        self.rms_plot.addItem(self.rms_bar)
        self.rms_plot.setTitle('RMS')
        self.rms_plot.setYRange(0.0, 0.1)
        axis = self.rms_plot.getAxis('bottom')
        axis.setStyle(tickLength=0, showValues=False)

        # - Create layouts        
        layout = HBoxLayout()
        self.setLayout(layout)
        ctl_layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.signal_view = pg.GraphicsLayoutWidget()
        self.rms_view = pg.GraphicsLayoutWidget()

        # - - add enable button to layout
        ctl_layout.addWidget(self.start_btn, Qt.AlignTop)
        ctl_layout.addLayout(form_layout)

        # - - add buffer size controller to layout
        form_layout.addRow(bufsecs_label, self.bufsecs_field)

        # - - add waveform viewer to layout
        self.signal_view.addItem(self.signal_plot)

        # -- add RMS indicator to layout
        self.rms_view.addItem(self.rms_plot)

        layout.extend([ctl_layout, self.signal_view, self.rms_view])
        layout.setStretch(1, 5)
        layout.setStretch(2, 1)

    
    @Slot()
    def on_start_btn_clicked(self) -> None:
        self.parent.toggle_start_stop()        


    @Slot()
    def on_bufsecs_field_edited(self) -> None:
        """
        Notify stream of change in requested buffer size.
        """
        try:
            secs = float(self.bufsecs_field.text())
            if secs <= 0:
                raise ValueError
        except:
            print('Warning: Invalid value for buffer size')
            return

        fs = self.instream.samplerate
        self.instream.bufsize = int(secs * fs)


    @Slot(object)
    def update_ui(self, block: Block) -> None:
        """
        Update waveform view and RMS indicator.
        """
        
        if self.ignore_update:
            return
        
        data = block.data
        N = len(data)
        secs = N / block.samplerate
        X = np.linspace(-secs, 0, N)
        self.signal_curve.setData(X, data)
        self.signal_plot.setXRange(-secs, 0)
        
        if len(data) > 1:
        
            self.rms_val = np.sqrt(np.mean(data**2))
        else:
            self.rms_val = 0
        self.rms_bar.setOpts(x=np.array([0.5]),
                             height=np.array([self.rms_val]))
        self.rms_plot.setXRange(0, 1)

            

class PitchWidget(QWidget):

    """
    YIN pitch estimator.

    For a sound pitched at f, lag (in secs.) is 1 / f. To get this
    in samples, we have lag = fs * 1 / f = fs / f.

    Make the window size twice the longest lag. That way we don't have to worry
    about indexing errors
    The block/window size must be at least twice the longest lag.

    """
    
    
    estimator: "PitchEstimator"
    
    # Widgets
    pitch_label: QLabel
    param_group: "GroupParameter"
    param_tree: ParameterTree
    params: Dict[str, Parameter]
    axes: pg.PlotItem
    lines: Dict[str, pg.PlotItem]
    
    # etc.
    ignore_update: bool = False
    
    
    def __init__(self,
                 estimator: "PitchEstimator",
                 parent: Optional[QWidget] = None
                 ):
        super().__init__(parent=parent)
        
        self.estimator = estimator

        # Initialize UI
        layout = QHBoxLayout()
        self.setLayout(layout)


        """
        -----------------------------------------------------------------------------
        - Initialize control panel
        
        """
        
        panel_layout = QVBoxLayout()
        self.layout().addLayout(panel_layout)

        # - Pitch readout
        self.pitch_label = QLabel('Pitch (Hz):')
        self.pitch_label.setFont(QFont("Courier", 14))
        #self.pitch_label.setFixedWidth(125)
        panel_layout.addWidget(self.pitch_label)

        # - Pyqtgraph parameters
        specs = [
            dict(name="fmin", type="float", value=estimator.fmin, step=1),
            dict(name="fmax", type="float", value=estimator.fmax, step=1),
            dict(name="min_thresh", type="float", value=estimator.min_thresh, step=0.05),
            dict(name="abs_thresh", type="float", value=estimator.abs_thresh, step=0.05),
        ]

        self.param_group = param_group = Parameter.create(
            name="params",
            type="group",
            children=specs,
        )
        self.param_tree = param_tree = ParameterTree()
        param_tree.setParameters(param_group)
        self.params = {}
        
        fmin = param_group.child("fmin")
        fmin.sigValueChanged.connect(self.on_flim_changed)
        self.params["fmin"] = fmin
        
        fmax = param_group.child("fmax")
        fmax.sigValueChanged.connect(self.on_flim_changed)
        self.params["fmax"] = fmax
        
        min_thresh = param_group.child("min_thresh")
        min_thresh.sigValueChanged.connect(self.on_thresh_changed)
        self.params["min_thresh"] = min_thresh
        
        abs_thresh = param_group.child("abs_thresh")
        abs_thresh.sigValueChanged.connect(self.on_thresh_changed)
        self.params["abs_thresh"] = abs_thresh

        panel_layout.addWidget(param_tree)

    

        """
        -----------------------------------------------------------------------------
        - Initialize graphics
        
        """        
        
        # - Plot
        self.axes = pg.PlotItem()
        self.axes.setLabel('bottom', 'Lag')
        self.axes.setLabel('left', 'CNMDF')
        self.axes.setXRange(1, 1200)
        self.axes.setYRange(0, 3)
        
        self.lines = {}
        
        # - - NMDF curve
        X = self.estimator.lags        
        Y = np.ones_like(X)
        line = self.axes.plot(X, Y)
        self.lines["dn"] = line
        
        # - - Vertical line indicating pitch
        line = pg.InfiniteLine(pos=0, angle=90)
        self.axes.addItem(line)
        self.lines["pitch"] = line
                
        line = pg.InfiniteLine(pos=estimator.min_thresh, angle=0)
        self.axes.addItem(line)
        self.lines["min_thresh"] = line
                
        line = pg.InfiniteLine(pos=estimator.abs_thresh, angle=0)
        self.axes.addItem(line)
        self.lines["abs_thresh"] = line
        
        # Layout
        self.graphics_layout = graphics_layout = pg.GraphicsLayoutWidget()
        self.layout().addWidget(graphics_layout)
        graphics_layout.addItem(self.axes)

                
        """
        -----------------------------------------------------------------------------
        - Finalize
        
        """
        layout.setStretch(0, 1)
        layout.setStretch(1, 4)


    @Slot(object)
    def update_ui(self, block: Block) -> None:
        """
        """
        
        if self.ignore_update:
            return
                
        # Update pitch readout label.      
        if block.tunable:
            s = 'Pitch (Hz): {:.2f}'.format(block.pitch)
        else:
            s = 'Pitch (Hz):'
        self.pitch_label.setText(s)
        
        # Update nmdf curve.        
        dn_line = self.lines["dn"]
        lags = np.arange(len(block.dn))
        dn_line.setData(lags, block.dn)
                
        # Update pitch indicator on axes.
        vline = self.lines["pitch"]
        vline.setVisible(block.tunable)
        #vline.setValue(block.pitch)
        vline.setValue(block.ix_best)
                    
        # Update threshold indicators on axes.
        self.lines["min_thresh"].setValue(self.estimator.min_thresh)
        self.lines["abs_thresh"].setValue(self.estimator.abs_thresh)
        
        
    @Slot()
    def on_flim_changed(self) -> None:
        """
        Modifies:
         - self._fmin
         - self._fmax
        """
        self.estimator._fmin = self.params["fmin"].value()
        self.estimator._fmax = self.params["fmax"].value()
        self.estimator.prepare()
        
        
    @Slot()
    def on_thresh_changed(self) -> None:
        """
        Modifies:
         - self._fmin
         - self._fmax
        """
        self.estimator.min_thresh = self.params["min_thresh"].value()
        self.estimator.abs_thresh = self.params["abs_thresh"].value()
         

            
            

class IntonationWidget(QWidget):
    
    estimator: "IntonationEstimator"

    #: Flag to prevent trying to update.
    ignore_update: bool = False
    
    #: UI specs.

    
    
    def __init__(self,
                 estimator: "IntonationEstimator",
                 parent: Optional[QWidget] = None,
                 ):
        super().__init__(parent=parent)
        
        self.estimator = estimator

        # - Initialize UI.
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.init_panel()
        layout.addLayout(self.panel_layout)

        self.init_graphics()
        layout.addWidget(self.graphics_layout)
        
        layout.setStretch(1, 1)
        layout.setStretch(2, 1)
        
        # - Update UI with scale.
        scale = self.estimator.scale        
        self.scale_label.setText("Scale: " + scale.scale_name)
        self.tn_note_combo.clear()
        for name in scale.names:
            self.tn_note_combo.addItem(name)
        self.tn_note_combo.setCurrentIndex(self.estimator.tn_note)
        self.tn_pitch_field.setText("{:.2f}".format(self.estimator.tn_pitch))
        
    
    """
    ---------------------------------------------------------------------------------
    - Initialization
    
    """

    def init_panel(self):

        
        self.panel_layout = QVBoxLayout() # left panel
        
        # - readout area
        
        self.readout_layout = QVBoxLayout()
        self.panel_layout.addLayout(self.readout_layout)
        
        self.note_label = QLabel("Note: ")
        self.note_label.setFont(QFont("Courier", 14))
        self.readout_layout.addWidget(self.note_label)
        
        self.cents_label = QLabel("Cents: ")
        self.cents_label.setFont(QFont("Courier", 14))
        self.readout_layout.addWidget(self.cents_label)
        
        self.pitch_label = QLabel('Pitch (Hz):')
        self.pitch_label.setFont(QFont("Courier", 14))
        self.readout_layout.addWidget(self.pitch_label)
        
        self.scale_label = QLabel("Scale: ")
        #self.scale_label.setFont(QFont("Courier", 14))
        self.readout_layout.addWidget(self.scale_label)
        
        # - control area
        
        self.control_layout = QFormLayout()
        self.panel_layout.addLayout(self.control_layout)
                
        self.tn_note_combo = QComboBox()
        self.tn_note_combo.activated.connect(self.on_tn_changed)
        self.control_layout.addRow(QLabel("Tuning note"), self.tn_note_combo)
        
        self.tn_pitch_field = QLineEdit("")
        self.tn_pitch_field.returnPressed.connect(self.on_tn_changed)
        self.control_layout.addRow(QLabel("Tuning pitch"), self.tn_pitch_field)
        
        # -- Scale button UI
        self.load_scale_btn = QPushButton('Load Scale')
        self.load_scale_btn.clicked.connect(self.on_load_scale_btn_clicked)
        self.panel_layout.addWidget(self.load_scale_btn)

        # start/stop button
        # - - start button
        self.start_btn = QPushButton('Start')
        self.start_btn.clicked.connect(self.on_start_btn_clicked)
        self.panel_layout.addWidget(self.start_btn)
        

    def init_graphics(self):


        #-----------------------------------------------------------------------
        # - Widgets

        self.axes = pg.PlotItem()
        self.axes.setLabel('bottom', 'cents')
        self.axes.setLabel('left', '')
        self.axes.setXRange(-50, 50)
        self.axes.setYRange(0, 1.1)

        # - - Vertical line indicating pitch
        self.vline = pg.InfiniteLine(pos=0, angle=90)
        self.axes.addItem(self.vline)

        X = np.linspace(-50, 50, 1000)
        Y = np.zeros_like(X)
        self.ncurve = self.axes.plot(X, Y)
        
        #-----------------------------------------------------------------------
        # - Layout
        
        self.graphics_layout = pg.GraphicsLayoutWidget(parent=self)
        self.graphics_layout.addItem(self.axes)


    """
    ---------------------------------------------------------------------------------
    - UI
    
    """


    @Slot(object)
    def update_ui(self, block: Block) -> None:
        """
        Triggered by the pitch estimator when estimation has completed.
        """
        
        if self.ignore_update:
            return
                                  
        # If no pitch was given, clear the display and return.
        if not block.tunable:
            self.clear_readout()
            return
        
        # - Update note label
        note_name = self.estimator.scale.names[block.note]
        self.note_label.setText("Note: " + note_name)
        
        # - Update cents label
        # Round error to nearest half-cent.
        cents_off = round(block.error * 2) / 2                
        if cents_off > 0:
            sign_char = "+"
        elif cents_off < 0:
            sign_char = ""            
        else:
            sign_char = " "                
        self.cents_label.setText("Cents: {}{:.1f}".format(sign_char, cents_off))
        
        # - Update pitch label
        if block.tunable:
            s = 'Pitch (Hz): {:.2f}'.format(block.pitch)
        else:
            s = 'Pitch (Hz):'
            
        self.pitch_label.setText(s)        
        # - Update graphics.
        self.vline.setVisible(True)
        self.vline.setValue(block.error_adj)
        self.ncurve.setVisible(True)
        errors = np.array(self.estimator.error_buf)
        n_samples = len(errors)

        if n_samples > 1:
            mu = np.mean(errors)
            std = np.std(errors)            
            #sem = std / np.sqrt(n_samples)
            #sigma = 1.96 * sem
            sigma = max(std, 0.001)

            X = np.linspace(-50, 50, 1000)
            height = max(1.0 - sigma * 0.1, 0)
            
            Y = height * np.exp(-(X-mu)**2/(2*sigma**2))
            #Y = scipy.stats.t.pdf(X, n_samples-1, loc=mu, scale=sigma)

            self.ncurve.setData(X, Y)


    @Slot()
    def on_start_btn_clicked(self) -> None:
        self.parent.toggle_start_stop()        


    def clear_readout(self):

        self.note_label.setText("Note: ")
        self.cents_label.setText("Cents: ")
        self.pitch_label.setText("Pitch (Hz): ")
        self.vline.setVisible(False)
        self.ncurve.setVisible(False)


    @Slot()
    def on_load_scale_btn_clicked(self) -> None:

        self.ignore_update = True
        
        # Get path to scale.
        fname = QFileDialog.getOpenFileName(
            self,
            "Open Scale",
            str(scale_dir()),
            "Scale Files (*.json)",
        )
        path = Path(fname[0])
        try:            
            new_scale = Scale.from_file(path)
        except:
            self.ignore_update = False
            return
        cur_scale = self.estimator.scale
                
        # Update labels.
        scale_name = new_scale.scale_name
        self.scale_label.setText("Scale: " + scale_name)
        self.tn_note_combo.clear()
        for name in new_scale.names:
            self.tn_note_combo.addItem(name)
        
        # If previous note name is in new scale
        cur_tn_name = cur_scale.names[self.estimator.tn_note]
        if cur_tn_name in new_scale.names:
            ind = tuple(new_scale.names).index(cur_tn_name)
            self.tn_note_combo.setCurrentIndex(ind)            
        else:
            self.tn_note_combo.setCurrentIndex(0)            
        
        self.estimator.scale = new_scale 
        self.estimator.tn_note = self.tn_note_combo.currentIndex()

        self.ignore_update = False
        
    
    
    @Slot()
    def on_tn_changed(self):
        
        # Grab values from widget.
        tn_note = self.tn_note_combo.currentIndex()
        tn_pitch = float(self.tn_pitch_field.text())
        
        # Notify estimator of new values.
        self.estimator.tn_note = tn_note
        self.estimator.tn_pitch = tn_pitch
        
