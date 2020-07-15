from setuptools import setup, find_packages

setup(
    name="LEIAOntology",
    version="1.3.0",
    packages=find_packages(),

    install_requires=[
        "Flask==1.0.2",
        "Flask-Cors==3.0.7",
        "Flask-SocketIO==3.3.1",
        "pymongo==3.6.1",
        "boto3==1.7.6",
    ],

    author="Jesse English",
    author_email="drjesseenglish@gmail.com",
    description="LEIA Ontology Service and API",
    keywords="ontology",
    project_urls={
        "Documentation": "https://app.nuclino.com/LEIA/Knowledge/",
        "Source Code": "https://bitbucket.org/leia-rpi/leiaontology/src/master/",
    }
)