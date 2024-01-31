import sys
from microtune.audio import InputStream
from microtune.driver import *
from microtune.uitools import Application


app = Application()

instream = InputStream(device=0)
drv = MainWindow(
    instream,
    instream_widget=True,
    pitch_widget=True,
)
drv.start()
sys.exit(app.exec())