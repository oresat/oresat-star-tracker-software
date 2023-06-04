from setuptools import Extension, setup
from setuptools.command.build_py import build_py

from oresat_star_tracker import __version__

BEAST_EXT = Extension(
    name='_beast',
    swig_opts=['-py3', '-c++'],
    sources=[
        'oresat_star_tracker/beast/beast.i',
    ],
    include_dirs=[
        'oresat_star_tracker',
    ],
    extra_compile_args=[
        '-std=c++11',
    ],
)


# Build extensions before python modules,
# or the generated SWIG python files will be missing.
class BuildPy(build_py):
    def run(self):
        self.run_command('build_ext')
        super(build_py, self).run()


setup(
    name='oresat-star-tracker',
    description='The OreSat Star Tracker app',
    version=__version__,
    license='GPLv3',
    author='PSAS',
    author_email='oresat@pdx.edu',
    url='https://github.com/oresat/oresat-star-tracker-software',
    keywords=['SWIG', 'oresat', 'star tracker'],
    packages=['oresat_star_tracker'],
    package_data={
        'oresat_star_tracker': [
            'beast/*.cpp',
            'beast/*.cxx',
            'beast/*.h',
            'beast/*.i',
            'beast/*.o',
            'beast/*.so',
            'beast/Makefile',
            'data/*',
            'templates/*',
        ]
    },
    ext_modules=[BEAST_EXT],
    cmdclass={
        'build_py': BuildPy,
    },
    install_requires=[
        'oresat-olaf',
        'opencv-python-headless==4.6.0.66',
        'swig',
    ],
    entry_points={
        'console_scripts': [
            'oresat-star-tracker = oresat_star_tracker.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
    python_requires='>=3.7',
)
