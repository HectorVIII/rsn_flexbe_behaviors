from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'rsn_flexbe_behaviors'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('lib', package_name, 'manifest'), glob('manifest/*.xml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='huitao',
    maintainer_email='jszdhyjs@gmail.com',
    description='FlexBE states and behaviors for the RSN handover demo.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mock_core_services_node = '
            'rsn_flexbe_behaviors.mock_core_services_node:main',
            'mock_hand_node = rsn_flexbe_behaviors.mock_hand_node:main',
        ],
    },
)
