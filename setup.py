from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='jira-agile-metrics',
    version='0.1',
    description='Agile metrics and summary data extracted from JIRA',
    long_description=long_description,
    author='Martin Aspeli',
    author_email='optilude@gmail.com',
    url='https://github.com/optilude/jira-agile-metrics',
    license='MIT',
    keywords='agile jira analytics metrics',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=[
        'jira',
        'PyYAML',
        'pandas',
        'numpy',
        'seaborn',
        'matplotlib',
        'statsmodels',
        'python-dateutil',
        'pydicti',
        'openpyxl',
    ],

    entry_points={
        'console_scripts': [
            'jira-agile-metrics=jira_agile_metrics.cli:main',
        ],
    },
)
