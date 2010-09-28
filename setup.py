from setuptools import setup, find_packages
setup(
    name='SimplePYPI',
    version='0.1',
    packages=find_packages(),
    scripts=[],
    install_requires=['Flask>=0.6','Werkzeug>=0.6.2', 'protobuf==2.3.0'],
    include_package_data=True,
    zip_safe=False,
    author = 'Charlie Knudsen',
    author_email = 'charlie.knudsen@gmail.com',
    license = 'PSF',
    url='http://www.cknudsen.net', # need to setup a site here    
    description='Simple PYPI server for use behind a firewall.',
    long_description=open('README.txt').read()
)
