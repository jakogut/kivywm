'''
texture_from_pixmap
'''

from libc.stdint cimport intptr_t, uintptr_t
from libc.stdio cimport printf, fprintf, stderr
from libc.string cimport strlen
from libc.stdlib cimport malloc, free

DEF EGL_TRUE = 1
DEF EGL_FALSE = 0

DEF EGL_NONE = 0x3038
DEF EGL_NATIVE_PIXMAP_KHR = 0x30B0
DEF EGL_NO_CONTEXT = 0
DEF EGL_IMAGE_PRESERVED_KHR = 0x30D2
DEF EGL_NO_IMAGE_KHR = 0x0

cdef extern from "X11/Xlib.h":
    ctypedef struct XErrorEvent:
        Display *display
        XID resourceid
        unsigned long serial
        unsigned char error_code
        unsigned char request_code
        unsigned char minor_code

    cdef void XFree(void *data) nogil

    ctypedef int (*XErrorHandler)(Display *d, XErrorEvent *e)
    cdef XErrorHandler XSetErrorHandler(XErrorHandler)
    cdef void XGetErrorText(Display *, unsigned char, char *, int)

cdef extern from "EGL/egl.h":
    ctypedef intptr_t EGLAttrib
    EGLDisplay eglGetCurrentDisplay() nogil
    EGLint eglGetError() nogil

cdef extern from "GL/gl.h":
    ctypedef unsigned int GLenum
    GLenum glGetError() nogil

cdef EGLImageKHR bindTexImage(Pixmap pixmap) nogil:
    cdef EGLDisplay egl_display = eglGetCurrentDisplay()

    cdef EGLint *attribs = [
        EGL_IMAGE_PRESERVED_KHR, EGL_TRUE,
        EGL_NONE
    ]

    cdef EGLImageKHR image = egl.eglCreateImageKHR(
        egl_display,
        <EGLContext>EGL_NO_CONTEXT,
        EGL_NATIVE_PIXMAP_KHR,
        <EGLClientBuffer>pixmap,
        attribs,
    )

    egl.glEGLImageTargetTexture2DOES(GL_TEXTURE_2D, <GLeglImageOES>image)
    if image != <EGLImageKHR>EGL_NO_IMAGE_KHR:
        egl.eglDestroyImageKHR(egl_display, image)
