import setuptools


setuptools.setup(
    name='geoddb',
    version='1.0.0',
    scripts=[] ,
    author='Ahmad Khatib',
    author_email='ackhatib@gmail.com',
    description='Geohash and DynamoDB Utility Package',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/khatiba/geoddb',
    install_requires=['boto3>=1.16'],
    packages=setuptools.find_packages(),
    license='MIT License',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'License :: OSI Approved :: MIT License',
    ]
 )
