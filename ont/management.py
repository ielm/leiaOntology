from os.path import join
from pymongo import MongoClient

import boto3
import os
import subprocess

ARCHIVE_PATH = "ARCHIVE_PATH"
ONTOLOGY_ACTIVE = "ONTOLOGY_ACTIVE"

MONGO_HOST = os.environ["MONGO_HOST"] if "MONGO_HOST" in os.environ else "localhost"
MONGO_PORT = int(os.environ["MONGO_PORT"]) if "MONGO_PORT" in os.environ else 27017
DATABASE = "leia-ontology"


def activate(collection):
    os.environ[ONTOLOGY_ACTIVE] = collection


def active():
    return os.environ[ONTOLOGY_ACTIVE] if ONTOLOGY_ACTIVE in os.environ else None


def getclient():
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    with client:
        return client


def handle():
    client = getclient()
    db = client[DATABASE]
    return db[active()]


def list_collections():
    client = getclient()
    db = client[DATABASE]
    return sorted(db.list_collection_names())


def rename_collection(original_name, new_name):
    client = getclient()
    db = client[DATABASE]
    collection = db[original_name]

    if new_name in db.list_collection_names():
        raise Exception("Cannot rename to " + new_name + ", that ontology already exists.")

    collection.rename(new_name)

    if active() == original_name:
        activate(new_name)


def delete_collection(name):
    client = getclient()
    db = client[DATABASE]
    collection = db[name]
    collection.drop()


def copy_collection(original_name, copied_name):
    client = getclient()
    db = client[DATABASE]
    collection = db[original_name]

    if copied_name in db.list_collection_names():
        raise Exception("Cannot copy to " + copied_name + ", that ontology already exists.")

    match = {
        "$match": {}
    }

    out = {
        "$out": copied_name
    }

    collection.aggregate([match, out])


def publish_archive(name):
    path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

    if path is None:
        raise Exception("Unknown ARCHIVE_PATH variable.")

    path = path + "/" + name + ".gz"

    s3 = boto3.resource('s3')
    s3.Object("leia-ontology-repository", name + ".gz").put(Body=open(path, 'rb'))


def list_remote_archives():
    s3 = boto3.resource('s3')
    bucket = s3.Bucket("leia-ontology-repository")

    return map(lambda object: object.key.replace(".gz", ""), bucket.objects.all())


def download_archive(name):
    path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

    if path is None:
        raise Exception("Unknown ARCHIVE_PATH variable.")

    path = path + "/" + name + ".gz"

    s3 = boto3.resource('s3')
    s3.Bucket("leia-ontology-repository").download_file(name + ".gz", path)


def collection_to_file(collection, path):
    path = join(path, collection + ".gz")

    cmd = "mongodump --archive=" + path + " --gzip --db " + DATABASE + " --collection " + collection + " --host " + MONGO_HOST + " --port " + str(MONGO_PORT)
    print (subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True))


def file_to_collection(path):
    name = os.path.basename(path).replace(".gz", "")
    cmd = "mongorestore --gzip --archive=" + path + " --db " + DATABASE + " --host " + MONGO_HOST + " --port " + str(MONGO_PORT)
    print (subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True))


def list_local_archives():
    path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

    if path is None:
        raise Exception("Unknown ARCHIVE_PATH variable.")

    from os import listdir
    from os.path import isfile, join
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]

    return map(lambda file: file.replace(".gz", ""), filter(lambda file: file.endswith(".gz"), onlyfiles))


def delete_local_archive(name):
    path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

    if path is None:
        raise Exception("Unknown ARCHIVE_PATH variable.")

    path = path + "/" + name + ".gz"
    os.remove(path)