"""Package setup file. Only used for SWIG."""

from setuptools import Extension, setup  # type: ignore
from setuptools.command.build_py import build_py  # type: ignore

BEAST_EXT = Extension(
    name="_beast",
    swig_opts=["-c++"],
    sources=[
        "oresat_star_tracker/beast/beast.i",
    ],
    include_dirs=[
        "oresat_star_tracker/beast",
    ],
    extra_compile_args=[
        "-std=c++11",
    ],
)


# Build extensions before python modules,
# or the generated SWIG python files will be missing.
class BuildPy(build_py):
    """Class to add swig configs."""

    def run(self):
        self.run_command("build_ext")
        super(build_py, self).run()


setup(
    ext_modules=[BEAST_EXT],
    cmdclass={
        "build_py": BuildPy,
    },
)
