from setuptools import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext

import sys
import os

supported_platforms = ['linux']
platform = sys.platform

if platform not in supported_platforms:
    print('Unsupported platform: {}, exiting'.format(platform))
    sys.exit()

libraries = ['GL', 'X11']

# Allows the include dir to be overridden, i.e., by Buildroot
kivy_include_dir = os.environ.get('KIVY_INCLUDE_DIR')

if kivy_include_dir is None:
    import kivy
    kivy_include_dir = os.path.join(os.path.dirname(kivy.__file__), 'include')

include_dirs = [
    'kivywm/include',
    kivy_include_dir,
]

extensions = [
    Extension(
        'kivywm.graphics.texture',
        ['kivywm/graphics/texture.pyx'],
        include_dirs=include_dirs,
        libraries=libraries,
        library_dirs=[],
    ),
    Extension(
        'kivywm.graphics.tfp',
        ['kivywm/graphics/tfp.pyx'],
        include_dirs=include_dirs,
        libraries=libraries,
        library_dirs=[],
    ),
    Extension(
        'kivywm.graphics.extensions',
        ['kivywm/graphics/extensions.pyx'],
        include_dirs=include_dirs,
        libraries=libraries,
        library_dirs=[],
    )
]

setup(
    name='KivyWM',
    version = '0.7.5',
    description='Kivy Window Manager',
    packages=[
        'kivywm',
        'kivywm.graphics',
        'kivywm.uix',
    ],
    author='Joseph Kogut',
    author_email='joseph.kogut@gmail.com',
    ext_modules=cythonize(extensions),
)

