'''
texture_from_pixmap
'''

from libc.stdint cimport intptr_t, uintptr_t
from libc.stdio cimport printf, fprintf, stderr
from libc.string cimport strlen
from libc.stdlib cimport malloc, free

DEF EGL_TRUE = 1
DEF EGL_FALSE = 0

DEF EGL_BIND_TO_TEXTURE_RGB = 0x3039
DEF EGL_BIND_TO_TEXTURE_RGBA = 0x303A
DEF EGL_FRONT_BUFFER_EXT = 0x3464
DEF EGL_NONE = 0x3038
DEF EGL_PIXMAP_BIT = 0x2
DEF EGL_SURFACE_TYPE = 0x3033
DEF EGL_WINDOW_BIT = 0x4
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
    EGLBoolean eglInitialize(EGLDisplay, EGLint *, EGLint *) nogil
    EGLBoolean eglBindAPI(EGLenum) nogil
    EGLContext eglGetCurrentContext() nogil
    EGLBoolean eglChooseConfig(EGLDisplay, EGLint *, EGLConfig *, EGLint, EGLint *) nogil
    EGLSurface eglCreatePixmapSurface(EGLDisplay, EGLConfig, EGLNativePixmapType, const EGLint *) nogil
    EGLBoolean eglDestroySuface(EGLDisplay, EGLSurface) nogil
    EGLDisplay eglGetDisplay(EGLNativeDisplayType) nogil
    EGLDisplay eglGetPlatformDisplay(EGLenum, void *, const EGLAttrib *)
    EGLDisplay eglGetCurrentDisplay() nogil
    EGLBoolean eglBindTexImage(EGLDisplay, EGLSurface, EGLint) nogil
    EGLBoolean eglReleaseTexImage(EGLDisplay, EGLSurface, EGLint) nogil
    EGLBoolean eglGetConfigs(EGLDisplay, EGLConfig *, EGLint, EGLint *) nogil
    EGLBoolean eglGetConfigAttrib(EGLDisplay, EGLConfig, EGLint, EGLint *) nogil
    EGLint eglGetError() nogil

cdef extern from "GL/gl.h":
    ctypedef unsigned int GLenum
    GLenum glGetError() nogil

cdef EGLImageKHR bindTexImage(Pixmap pixmap) nogil:
    cdef EGLDisplay egl_display
    egl_display = eglGetCurrentDisplay()

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

    cdef EGLint error
    error = eglGetError()
    fprintf(stderr, "eglCreateImageKHR, image: %p error: %#08x\n", image, error)

    fprintf(stderr, "glEGLImageTargetTexture2DOES: %p\n", egl.glEGLImageTargetTexture2DOES)
    egl.glEGLImageTargetTexture2DOES(GL_TEXTURE_2D, <GLeglImageOES>image)

    error = glGetError()
    fprintf(stderr, "glEGLImageTargetTexture2DOES: error: %d\n", error)

    if image != <EGLImageKHR>EGL_NO_IMAGE_KHR:
        egl.eglDestroyImageKHR(egl_display, image)
