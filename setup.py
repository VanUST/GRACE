# ~/tools/grace-context-master/setup.py
from setuptools import setup, find_packages

setup(
    name='grace-context-master',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4',
        'markdownify',
        'docling' 
    ],
    entry_points={
        'console_scripts': [
            # This creates the terminal command 'grace-ctx'
            'grace-ctx=grace_master.main:main_entry_point',
        ],
    },
)