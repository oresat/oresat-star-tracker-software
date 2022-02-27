from setuptools import Extension, find_packages, setup
from setuptools.command.build_py import build_py


BEAST_EXT = Extension(
    name='_beast',
    swig_opts=['-py3', '-c++'],
    sources=[
        'star_tracker/beast/beast.i',
    ],
    include_dirs=[
        'star_tracker',
    ],
    extra_compile_args=[
        '-std=c++11',
    ]
)


# Build extensions before python modules,
# or the generated SWIG python files will be missing.
class BuildPy(build_py):
    def run(self):
        self.run_command('build_ext')
        super(build_py, self).run()


setup(
    name='star-tracker',
    description='The OreSat Star Tracker app',
    version='0.1.0',
    license='GPLv3',
    author='PSAS',
    author_email='oresat@pdx.edu',
    url='https://github.com/oresat/oresat-star-tracker-software',
    keywords=['SWIG', 'oresat', 'star tracker'],
    packages=find_packages('.'),
    ext_modules=[BEAST_EXT],
    cmdclass={
        'build_py': BuildPy,
    },
    install_requires=[
        'numpy',
        'opencv-python-headless',
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
