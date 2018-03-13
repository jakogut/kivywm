from kivy.graphics.texture cimport Texture as KivyTexture
from kivywm.graphics.extensions cimport *
from kivywm.graphics.tfp cimport bindTexImage, releaseTexImage

def texture_create_from_pixmap(pixmap, size):
    cdef GLuint target = GL_TEXTURE_2D
    cdef int allocate = 0, mipmap = 0
    callback = None
    colorfmt = 'rgba'
    bufferfmt = 'ubyte'
    icolorfmt = colorfmt

    cdef Texture texture = Texture(size[0], size[1], target,
          colorfmt=colorfmt, bufferfmt=bufferfmt, mipmap=mipmap,
          callback=callback, icolorfmt=icolorfmt)

    texture.min_filter = 'linear'
    texture.mag_filter = 'linear'

    texture.bind_pixmap(pixmap)
    return texture

cdef class Texture(KivyTexture):
    cdef object _pixmap

    create_from_pixmap = staticmethod(texture_create_from_pixmap)

    def __init__(self, *args, **kwargs):
        super(Texture, self).__init__(*args, **kwargs)
        self._pixmap = None

    def bind_pixmap(self, pixmap):
        self.bind()
        glxpixmap = bindTexImage(pixmap)
        self.flip_vertical()
        self._pixmap = glxpixmap

    def release_pixmap(self):
        if self._pixmap:
            releaseTexImage(self._pixmap)
