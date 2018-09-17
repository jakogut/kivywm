from kivywm.graphics.extensions cimport *
from kivy.core.window.window_info cimport *

cpdef void tfp_init()
cdef EGLImageKHR bindTexImage(Pixmap pixmap) nogil
cdef void releaseTexImage(EGLImageKHR surface) nogil
