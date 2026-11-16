import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'random_walk'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='CAS PAIR',
    maintainer_email='cas-pair@example.com',
    description='TurtleBot3 random walk (reference solution)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'random_walk = random_walk.node:main',
        ],
    },
)
