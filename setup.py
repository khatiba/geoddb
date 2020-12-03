import setuptools


setuptools.setup(
    name='geoddb',
    version='0.1.0',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: MIT License',
    ]
 )
