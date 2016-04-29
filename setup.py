from setuptools import setup, find_packages

LONG_DESCRIPTION = """\
"""

setup(name='swimpy',
      description='Python SWIM implementation',
      long_description=LONG_DESCRIPTION,
      version='0.1.0',
      url='https://github.com/jefffm/swimpy',
      license='MIT license',
      platforms=['unix', 'linux', 'osx'],
      author='Jeff Lynn',
      author_email='jeff.michael.lynn at gmail',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      install_requires=[
          'booby',
          'msgpack-python',
          'tornado',
      ],
      setup_requires=[
          'pytest-runner'
      ],
      tests_require=[
          'flaky',
          'mock',
          'pytest',
          'pytest-cov',
          'pytest-timeout',
          'pytest-xdist',
      ],
      zip_safe=False)
