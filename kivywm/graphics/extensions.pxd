from kivy.graphics.cgl cimport *

cdef extern from "graphics.h":
    # X11
    cdef struct _XDisplay:
        pass

    ctypedef _XDisplay Display

    ctypedef int XID
    ctypedef XID Bool
    ctypedef XID Window
    ctypedef XID Drawable
    ctypedef XID Pixmap

    ctypedef void *GLeglImageOES

    ctypedef void *EGLClientBuffer
    ctypedef void *EGLConfig
    ctypedef void *EGLContext
    ctypedef void *EGLDisplay
    ctypedef void *EGLNativeDisplayType
    ctypedef void *EGLNativePixmapType
    ctypedef void *EGLSurface
    ctypedef void *EGLImage
    ctypedef void *EGLImageKHR
    ctypedef unsigned int EGLenum
    ctypedef int EGLint
    ctypedef EGLint EGLBoolean

ctypedef EGLImageKHR (*PFNEGLCREATEIMAGEKHRPROC)(EGLDisplay,
                                                 EGLContext,
                                                 EGLenum,
                                                 EGLClientBuffer,
                                                 const EGLint *) nogil
ctypedef EGLBoolean (*PFNEGLDESTROYIMAGEKHRPROC)(EGLDisplay, EGLImageKHR) nogil
ctypedef void (*PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)(GLenum, GLeglImageOES) nogil

ctypedef struct EGL_Context:
    EGLImageKHR (*eglCreateImageKHR)(EGLDisplay,
                                     EGLContext,
                                     EGLenum,
                                     EGLClientBuffer,
                                     const EGLint *) nogil
    EGLBoolean (*eglDestroyImageKHR)(EGLDisplay, EGLImageKHR) nogil
    void (*glEGLImageTargetTexture2DOES)(GLenum, GLeglImageOES) nogil

cdef EGL_Context *egl
cdef EGL_Context *egl_get_context()
cdef void egl_set_context(EGL_Context *ctx)
cpdef void egl_init() except *
