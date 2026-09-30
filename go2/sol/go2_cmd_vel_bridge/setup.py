from setuptools import find_packages, setup

package_name = 'go2_cmd_vel_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ema-student',
    maintainer_email='shll@zhaw.ch',
    description='Translates geometry_msgs/Twist on cmd_vel to Unitree Go2 sport API requests',
    license='BSD-3-Clause',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cmd_vel_bridge = go2_cmd_vel_bridge.cmd_vel_bridge:main',
        ],
    },
)
