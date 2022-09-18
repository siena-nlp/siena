import logging
from setuptools import (
    setup,
    find_packages,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

try:
    with open("README.md", "r") as fh:
        long_description = fh.read()
except Exception as e:
    long_description = "not provided"
    logger.error(f"couldn't retrieve the long package description. {e}")

setup(
    name='siena',
    version='0.0.1a3',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        # Include special files needed for init project:
        "": ["*.SIENA", "*.siena", "*.tmp", "*.md","*.html","*.css","*.js"],
    },
    description="SIENA tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/akalankasakalasooriya/siena_text_annotation_tool",
    author="Akalanka Sakalasooriya",
    author_email="himesha@outlook.com",
    # license="MIT",  # TODO: add license
    classifiers=[
        # "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "beautifulsoup4~=4.11.1",
        "bs4~=0.0.1",
        "certifi~=2022.5.18.1",
        "click~=8.1.3",
        "colorama~=0.4.4",
        "Flask~=2.1.2",
        "Flask-Cors~=3.0.10",
        "Flask-WTF~=1.0.1",
        "importlib-metadata~=4.11.4",
        "install~=1.3.5",
        "itsdangerous~=2.1.2",
        "Jinja2~=3.1.2",
        "MarkupSafe~=2.1.1",
        "pymongo<3.11,>=3.8",
        "python-dateutil~=2.8.2",
        "PyYAML~=6.0",
        "six~=1.15.0",
        "soupsieve~=2.3.2.post1",
        "Werkzeug~=2.1.2",
        "wincertstore~=0.2",
        "WTForms~=3.0.1",
        "zipp~=3.8.0",
        "nltk~=3.7",
        "pandas~=1.4.2",
        "ruamel.yaml~=0.17.21"
    ],
    entry_points={'console_scripts': ['siena = siena.siena_cli:run_siena_cli']}
)