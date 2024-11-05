from setuptools import setup, find_packages

long_description = 'Performance monitoring CLI tool for Apple Silicon'

setup(
    name='asitop-exporter',
    version='1.0.0',
    author='xuwei fang',
    description='Performance monitoring CLI tool for Apple Silicon',
    packages=find_packages(),
    entry_points={
            'console_scripts': [
                'asitop-exporter = asitop_exporter.__main__:main'
            ]
    },
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
    ),
    keywords='asitop-exporter',
    install_requires=[
        "dashing",
        "psutil",
        "prometheus_client",
        "termcolor",
    ],
    zip_safe=False
)
