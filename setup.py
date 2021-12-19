from setuptools import setup, find_packages
import io
import os


setup(
    name='goban_irl',
    packages=find_packages(),
    version='0.0.5',
    entry_points={
        'console_scripts': [
            'goban_irl = goban_irl.__main__:main'
        ]
    },
    author='Seth Rothschild',
    author_email='seth.j.rothschild@gmail.com',
    description='Read and use goban state from image',
    install_requires='pyobjc',
    tests_require=[],
    test_suite='pytest'
)
