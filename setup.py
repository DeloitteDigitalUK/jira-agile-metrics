from codecs import open
from os import path

from setuptools import setup, find_packages


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(here, "requirements.txt")) as f:
    install_requires = f.readlines()

setup(
    name="jira-agile-metrics",
    version="0.25",
    description="Agile metrics and summary data extracted from JIRA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Martin Aspeli",
    author_email="optilude@gmail.com",
    url="https://github.com/optilude/jira-agile-metrics",
    license="MIT",
    keywords="agile jira analytics metrics",
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    install_requires=install_requires,
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    include_package_data=True,
    package_data={
        "jira_agile_metrics.webapp": ["templates/*.*", "static/*.*"],
        "jira_agile_metrics.calculators": ["*.html"],
    },
    entry_points={"console_scripts": ["jira-agile-metrics=jira_agile_metrics.cli:main"]},
)
