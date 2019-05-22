'''
texture_from_pixmap
'''

from libc.stdint cimport uintptr_t
from libc.stdio cimport printf, fprintf, stderr
from libc.string cimport strlen
from libc.stdlib cimport malloc, free

DEF GL_TEXTURE_EXTERNAL_OES = 0x8D65

DEF GLX_BIND_TO_TEXTURE_RGB_EXT = 0x20D0
DEF GLX_BIND_TO_TEXTURE_RGBA_EXT = 0x20D1
DEF GLX_BIND_TO_TEXTURE_TARGETS_EXT = 0x20D3
DEF GLX_DONT_CARE = 0xFFFFFFFF
DEF GLX_DOUBLEBUFFER = 5
DEF GLX_DRAWABLE_TYPE = 0x8010
DEF GLX_FRONT_EXT = 0x20DE
DEF GLX_PIXMAP_BIT = 0x00000002
DEF GLX_TEXTURE_FORMAT_RGB_EXT = 0x20D9
DEF GLX_TEXTURE_TARGET_EXT = 0x20D6
DEF GLX_TEXTURE_2D_EXT = 0x20DC
DEF GLX_TEXTURE_2D_BIT_EXT = 0x00000002
DEF GLX_TEXTURE_FORMAT_EXT = 0x20D5
DEF GLX_TEXTURE_FORMAT_RGBA_EXT = 0x20DA
DEF GLX_Y_INVERTED_EXT = 0x20D4

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

from kivy.core.window.window_info cimport WindowInfoX11
cdef WindowInfoX11 window_info

cdef EGLDisplay egl_display

cpdef void tfp_init():
    from kivy.core.window import Window
    global window_info
    window_info = Window.get_window_info()

    global egl_display
    cdef int major, minor, success
    egl_display = eglGetDisplay(window_info.display)
    success = eglInitialize(egl_display, &major, &minor)
    fprintf(stderr, 'eglDisplay: %#08x, success: %d, EGL version: %d.%d\n', egl_display, success, major, minor);

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
    EGLBoolean eglInitialize(EGLDisplay, EGLint *, EGLint *) nogil
    EGLContext eglGetCurrentContext() nogil
    EGLBoolean eglChooseConfig(EGLDisplay, EGLint *, EGLConfig *, EGLint, EGLint *) nogil
    EGLSurface eglCreatePixmapSurface(EGLDisplay, EGLConfig, EGLNativePixmapType, const EGLint *) nogil
    EGLBoolean eglDestroySuface(EGLDisplay, EGLSurface) nogil
    EGLDisplay eglGetDisplay(EGLNativeDisplayType) nogil
    EGLBoolean eglBindTexImage(EGLDisplay, EGLSurface, EGLint) nogil
    EGLBoolean eglReleaseTexImage(EGLDisplay, EGLSurface, EGLint) nogil
    EGLBoolean eglGetConfigs(EGLDisplay, EGLConfig *, EGLint, EGLint *) nogil
    EGLBoolean eglGetConfigAttrib(EGLDisplay, EGLConfig, EGLint, EGLint *) nogil
    EGLint eglGetError() nogil

cdef EGLImageKHR bindTexImage(Pixmap pixmap) nogil:
    fprintf(stderr, "bindTexImage, pixmap: %#08x\n", pixmap)

    cdef EGLImageKHR image

    cdef EGLint *attribs = [
        EGL_IMAGE_PRESERVED_KHR, EGL_TRUE,
        EGL_NONE,
    ]

    image = egl.eglCreateImageKHR(
        egl_display,
        <EGLContext>EGL_NO_CONTEXT,
        EGL_NATIVE_PIXMAP_KHR,
        <EGLClientBuffer>pixmap,
        attribs,
    )

    cdef EGLint error
    error = eglGetError()
    fprintf(stderr, "eglCreateImageKHR, image: %#08x error: %#08x\n", image, error)

    cdef GLenum target = GL_TEXTURE_EXTERNAL_OES
    egl.glEGLImageTargetTexture2DOES(target, <GLeglImageOES>image)

    error = eglGetError()
    fprintf(stderr, "glEGLImageTargetTexture2DOES: error: %#08x\n", error)
    return image


cdef void releaseTexImage(EGLSurface surface) nogil:
    eglReleaseTexImage(egl_display, surface, 0)
