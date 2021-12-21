import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

packages = ['locr']

requires = [
    'bs4',
    'requests'
]

setuptools.setup(
    name="locr",
    version="0.4.3",
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
    packages=packages,
    package_dir={"locr": "locr"},
    python_requires=">=3.0",
    install_requires=requires,
)
