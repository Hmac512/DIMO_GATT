# coding=utf-8

import setuptools

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name="dimo-gatt",
    version="0.0.20a",
    author="Hmac512",
    description="Test dimo gatt",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Hmac512/DIMO_GATT",
    packages=setuptools.find_packages(exclude=['tests*']),
    entry_points={
        'console_scripts': [
            'dimo_gatt = gatt.gatt:main',
        ],
    },
    setup_requires=[
        'wheel',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
