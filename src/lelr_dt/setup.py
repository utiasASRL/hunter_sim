from setuptools import find_packages, setup
from os.path import join, dirname
from glob import glob


package_name = 'lelr_dt'

def get_all_files_in_path(glob_string, path_string):
    return [ (join(path_string, dirname(g)), [g]) for g in glob(glob_string, recursive=True)]

def create_datafiles():
    df = [ ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
            (join('share/' , package_name,"launch"), glob("launch/*.*")),
            ('share/' + package_name, ['package.xml']),
            ]
    for complex_path in ["robot_description","models", package_name]:
        res = get_all_files_in_path(glob_string=f"{complex_path}/**/*.*", path_string=join("share",package_name))
        df.extend(res) 
    return df


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=create_datafiles(),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rover',
    maintainer_email='rover@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
)