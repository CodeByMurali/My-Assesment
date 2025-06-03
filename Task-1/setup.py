# setup() is used to define package metadata and configuration
# find_packages() automatically detects all packages (folders with __init__.py)
from setuptools import setup, find_packages

setup(
    name="data_processor_project",
    version="0.0.1",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'run_processing=process:main',
        ],
    },
)
