import logging
from setuptools import (
    setup,
    find_packages,
)

from siena.shared.constants import (
    PACKAGE_VERSION,
    PACKAGE_NAME_PYPI,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

requirements = None
long_description = None

try:
    with open("README.md", "r") as fh:
        long_description = fh.read()

    with open("requirements.txt", mode="r", encoding="utf8") as requirements_file:
        requirements = requirements_file.readlines()
    requirements = [str.strip(req) for req in requirements]

except Exception as e:
    long_description = "not provided"
    logger.error(f"couldn't retrieve the long package "
                 f"description or requirements list. {e}")

setup(
    name=PACKAGE_NAME_PYPI,
    version=PACKAGE_VERSION,
    packages=find_packages(),
    include_package_data=True,
    package_data={
        # Include special files needed
        # for init project:
        "": [
            "*.SIENA",
            "*.siena",
            "*.tmp",
            "*.md",
            "*.html",
            "*.css",
            "*.js"
        ],
    },
    description="SIENA tool for efficient "
                "entity annotation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siena-nlp/siena",
    author="Akalanka Sakalasooriya",
    author_email="himesha@outlook.com",
    license='Apache License 2.0',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "beautifulsoup4==4.11.1",
        "flask>=2.1.2",
        "Flask-Cors==3.0.10",
        "Flask-WTF==1.0.1",
        "nltk==3.6.3",
        "pandas==1.4.3",
        "waitress>=2.1.2",
        "rasa~=2.8.8",
        "ruamel.yaml<0.17.0,>=0.16.5",
    ],
    entry_points={'console_scripts': ['siena = siena.siena_cli:run_siena_cli']}
)
