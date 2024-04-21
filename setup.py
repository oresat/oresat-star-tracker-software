"""Package setup file. Only used for SWIG."""

from setuptools.command.build_py import build_py  # type: ignore


# Build extensions before python modules,
# or the generated SWIG python files will be missing.
class BuildPy(build_py):
    """Class to add swig configs."""

    def run(self):
        self.run_command("build_ext")
        super(build_py, self).run()


setup(
    cmdclass={
        "build_py": BuildPy,
    },
)
