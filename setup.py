from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as f:
    requirements = f.readlines()

setup(
    name='reactive-uart2ip',
    version='0.2.1',
    author="Gianluca Scopelliti",
    author_email="gianlu.1033@gmail.com",
    description="TCP server that mediates UART serial communication",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AuthenticExecution/reactive-uart2ip",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': ['reactive-uart2ip = uart2ip.main:main']
    },
)
