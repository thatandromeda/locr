import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="locr",
    version="0.1.0",
    author="Andromeda Yelton",
    description="Tools for fetching OCRed text of Library of Congress items.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thatandromeda/locr",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "locr"},
    packages=setuptools.find_packages(where="locr"),
    python_requires=">=3.0",
)

requires = [
    'bs4',
    'requests'
]
