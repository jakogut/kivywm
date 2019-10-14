'''
texture_from_pixmap
'''

from libc.stdint cimport uintptr_t
from libc.stdio cimport fprintf, stderr
from libc.string cimport strlen

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

from kivy.core.window.window_info cimport WindowInfoX11
cdef WindowInfoX11 window_info
cdef GLXFBConfig *configs

cpdef void tfp_init():
    from kivy.core.window import Window
    global window_info
    window_info = Window.get_window_info()

    cdef int *pixmap_config = [
        GLX_BIND_TO_TEXTURE_RGBA_EXT, 1,
        GLX_DRAWABLE_TYPE, GLX_PIXMAP_BIT,
        GLX_BIND_TO_TEXTURE_TARGETS_EXT, GLX_TEXTURE_2D_BIT_EXT,
        GLX_DOUBLEBUFFER, 0,
        GLX_Y_INVERTED_EXT, GLX_DONT_CARE,
        0,
    ]

    global configs

    cdef int c = 0
    configs = glXChooseFBConfig(window_info.display, 0, pixmap_config, &c);
    if not configs:
        print('No appropriate GLX FBConfig available!')

cdef extern from "GL/glx.h":
    GLXPixmap glXCreatePixmap(Display *, GLXFBConfig, Pixmap, const int *) nogil;
    GLXFBConfig *glXChooseFBConfig(Display *, int , const int *, int *) nogil;
    XVisualInfo *glXChooseVisual( Display *, int , int *) nogil;
    GLXContext glXCreateContext( Display *, XVisualInfo *, GLXContext, Bool) nogil;

cdef int *pixmap_attribs = [
    GLX_TEXTURE_TARGET_EXT, GLX_TEXTURE_2D_EXT,
    GLX_TEXTURE_FORMAT_EXT, GLX_TEXTURE_FORMAT_RGB_EXT,
    0
]

cdef GLXPixmap bindTexImage(Pixmap pixmap) nogil:
    cdef GLXPixmap glxpixmap

    with nogil:
        glxpixmap = glXCreatePixmap(window_info.display, configs[0], pixmap, pixmap_attribs)
        glx.glXBindTexImageEXT(window_info.display, glxpixmap, GLX_FRONT_EXT, NULL)
        return glxpixmap

cdef void releaseTexImage(GLXPixmap glxpixmap) nogil:
    with nogil:
        glx.glXReleaseTexImageEXT(window_info.display, glxpixmap, GLX_FRONT_EXT)
        glXDestroyPixmap(window_info.display, glxpixmap)
