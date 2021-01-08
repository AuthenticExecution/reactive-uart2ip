from setuptools import setup, find_packages

setup(
    name='reactive-uart2ip',
    version='0.1',
    packages=find_packages(),
    install_requires=['colorlog==4.6.2', 'pyserial-asyncio==0.5'],
    entry_points={
        'console_scripts': ['reactive-uart2ip = uart2ip.main:main']
    },

    author='Gianluca Scopelliti',
    author_email='gianlu.1033@gmail.com'
)
