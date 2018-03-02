import os

from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-raster-aggregation',
    version='0.2',
    packages=['raster_aggregation', 'raster_aggregation.migrations'],
    include_package_data=True,
    license='BSD',
    description='Zonal aggregation functionality for django-raster',
    long_description=README,
    url='https://github.com/geodesign/django-raster-aggregation',
    author='Daniel Wiesmann',
    author_email='daniel@urbmet.com',
    install_requires=[
        'Django>=2.0',
        'celery>=4.0.2',
        'django-raster>=0.5',
        'django-filter>=1.0.4',
        'djangorestframework>=3.5.4',
        'djangorestframework-gis>=0.11',
        'drf-extensions>=0.3.1',
        'mapbox-vector-tile>=1.2.0',
    ],
    keywords=['django', 'raster', 'gis', 'gdal', 'celery', 'geo', 'spatial'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
