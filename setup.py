import os
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.md")).read()

setup(
    name='django-dynamic-list-display',
    version='0.1',
    packages=['dynamic-list-display'],
    description='A line of description',
    long_description=README,
    author='nik',
    author_email='nikitagoncarov657@gmail.com',
    url='https://github.com/Nikita-Goncharov/django-dynamic-list-display',
    license='MIT',
    install_requires=[
        'Django',
    ]
)