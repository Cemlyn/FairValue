from setuptools import setup, find_packages

setup(
    name="fairvalue",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic",
        # Add other dependencies here
    ],
    author="Cemlyn",
    description="A Python library for automated company valuations using DCF analysis",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Cemlyn/FairValue",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.12",
    ],
)
