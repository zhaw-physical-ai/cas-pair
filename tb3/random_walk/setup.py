from setuptools import find_packages, setup

package_name = 'random_walk'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # TODO: install launch/*.launch.py to share/random_walk/launch, or
        # `ros2 launch random_walk ...` does not find it
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your name',
    maintainer_email='you@example.com',
    description='TurtleBot3 random walk',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # TODO: the executable `random_walk`, running main() in random_walk/node.py
        ],
    },
)
