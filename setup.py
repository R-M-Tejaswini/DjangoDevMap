from setuptools import setup, find_packages

setup(
    name='DjangoDevMap',
    version='0.1.0',
    description='Visualize and understand Django codebases through static analysis and runtime tracing',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'django>=3.2',
        'click>=8.0',
        'astor>=0.8.1',
        'colorama>=0.4.4',
        'jinja2>=3.0',
        'pyyaml>=5.4',
    ],
    entry_points={
        'console_scripts': [
            'django-mapper=django_mapper.cli.main:cli',
        ],
    },
    package_data={
        'django_mapper': ['visualizers/templates/*.html'],
    },
    python_requires='>=3.8',
)