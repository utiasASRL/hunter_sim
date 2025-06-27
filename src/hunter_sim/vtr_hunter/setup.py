from setuptools import find_packages, setup

package_name = 'vtr_hunter'

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
    maintainer='alec',
    maintainer_email='freakyfactoid@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'start_convoy_repeat = vtr_hunter.start_convoy_repeat:main',
            'start_convoy_repeat_three = vtr_hunter.start_convoy_repeat_three:main'
        ],
    },
)
