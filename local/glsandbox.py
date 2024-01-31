import ctypes
import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
from qtpy import QtWidgets
from qtpy.QtWidgets import QApplication, QOpenGLWidget

vert_shader = """
attribute vec2 pos;

void main(){
    gl_Position = vec4(pos.x, pos.y, 0.0, 1.0);
}
"""

frag_shader = """

void main(){
    gl_FragColor = vec4(1.0f, 0.5f, 0.2f, 1.0f);
} 
"""


vertex_data = np.array([-0.1, -0.1,  0.0,
                         0.3,  0.0,  0.0,
                         0.0,  0.4,  0.0], dtype=np.float32)


class glWidget(QOpenGLWidget):
    
    _handle: int = -1
    
    def __init__(self, parent=None):
        QOpenGLWidget.__init__(self, parent)
        self.setMinimumSize(600, 600)
        

    def initializeGL(self):
        #self.vbo = vbo.VBO(vertex_data)
        self.create_program(vert_shader, frag_shader)
        glUseProgram(self._handle)
        
        buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, buffer)
        
        glShadeModel(GL_SMOOTH)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()        
        glMatrixMode(GL_MODELVIEW)

                        
    def create_shader(self, source, mode):
        handle = glCreateShader(mode)
        glShaderSource(handle, source)
        glCompileShader(handle)
        if glGetShaderiv(handle, GL_COMPILE_STATUS) != GL_TRUE:
            info = glGetShaderInfoLog(handle)
            raise RuntimeError('Shader compilation failed: {}'.format((info)))
        return handle
    

    def create_program(self, vert: str, frag: str):
        
        self._handle = glCreateProgram()
        vert_id = self.create_shader(vert, GL_VERTEX_SHADER)
        frag_id = self.create_shader(frag, GL_FRAGMENT_SHADER)        
        glAttachShader(self._handle, vert_id)
        glAttachShader(self._handle, frag_id)
        glLinkProgram(self._handle)
        if glGetProgramiv(self._handle, GL_LINK_STATUS) != GL_TRUE:
            info = glGetProgramInfoLog(self._handle)
            glDeleteProgram(self._handle)
            glDeleteShader(vert_id)
            glDeleteShader(frag_id)
            raise RuntimeError('Error linking program: {}'.format((info)))
        glDeleteShader(vert_id)
        glDeleteShader(frag_id)
        
        
    def paintGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        self.vbo.bind()
        glUseProgram(self._handle)
        glDrawArrays(GL_TRIANGLES, 0, len(vertex_data))





app = QApplication(sys.argv)
win = glWidget()
win.show()
app.exec()