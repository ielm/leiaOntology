from os.path import join
from pymongo import MongoClient

import boto3
import os
import subprocess

ARCHIVE_PATH = "ARCHIVE_PATH"
EXPORT_PATH = "EXPORT_PATH"
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


def can_connect():
    return active() in list_collections()


def list_collections():
    client = getclient()
    db = client[DATABASE]
    return sorted(filter(lambda c: not c.startswith("compiled_"), db.list_collection_names()))


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

def compile_progress():
    results = {}

    for c in list_collections():
        client = getclient()
        db = client[DATABASE]
        compiled = db["compiled_" + c]

        progress = compiled.find_one({"_id": "PROGRESS"})
        if progress is not None:
            progress["status"]["percent"] = int(100.0 * (float(progress["status"]["count"]) / float(progress["status"]["total"])))

        results[c] = {
            "collection": c,
            "compiled_collection": compiled.name,
            "progress": progress
        }

    return results

def compile(collection: str, inh: bool=False, inv: bool=False):
    client = getclient()
    db = client[DATABASE]
    compiled = db["compiled_" + collection]

    # Check to see if a compile operation is in progress
    progress = compiled.find_one({"_id": "PROGRESS"})
    if progress is not None:
        if progress["finished"] is None:
            raise PermissionError

    # Reset the compiled database
    compiled.drop()

    import time
    from ont.api import OntologyAPI
    api = OntologyAPI(collection=db[collection])

    # List all of the concepts
    concepts = set(api.list()[0:100])

    # Prime the PROGRESS document
    compiled.insert_one({
        "_id": "PROGRESS",
        "status": {
            "count": 0,
            "total": len(concepts),
            "last": None
        },
        "started": time.time(),
        "finished": None
    })

    count = 0

    # Calculate the relations and inverses
    relations = api.relations_to_inverses()

    # Compile each concept
    local = not inh
    for c in concepts:
        frame = api.get(c, local=local)[0]

        if inv:
            usages = api.report(c, include_usage=inv, usage_with_inheritance=inh)

            for inv in usages["usage"]["inverses"]:
                try:
                    slot = relations[inv["slot"]]
                except:
                    slot = inv["slot"]
                facet = inv["facet"]
                filler = inv["concept"]

                if slot not in frame[c]:
                    frame[c][slot] = {}
                if facet not in frame[c][slot]:
                    frame[c][slot][facet] = []
                frame[c][slot][facet].append(filler)

        # Convert frame names, slots, facets, and relation fillers to upper case
        frame = frame[c]
        for slot_name in frame.keys():
            slot = frame.pop(slot_name)
            frame[slot_name.upper()] = slot

            for facet_name in slot.keys():
                facet = slot.pop(facet_name)
                slot[facet_name.upper()] = list(map(lambda filler: filler.upper() if filler in concepts else filler, facet))

        frame["_id"] = c.upper()

        count += 1
        compiled.insert_one(frame)
        compiled.update_one(
            {"_id": "PROGRESS"},
            {"$set": {"status.count": count, "status.last": c}}
        )

    # Mark the task as finished
    compiled.update_one(
        {"_id": "PROGRESS"},
        {"$set": {"finished": time.time()}}
    )

def export(collection: str, format: str):
    path = os.environ[EXPORT_PATH] if EXPORT_PATH in os.environ else None

    if path is None:
        raise Exception("Unknown EXPORT_PATH variable.")

    # Connect to compiled collection
    client = getclient()
    db = client[DATABASE]
    compiled = db["compiled_" + collection]

    # Check to see if a compile is complete
    progress = compiled.find_one({"_id": "PROGRESS"})
    if progress is None:
        raise PermissionError
    if progress is not None:
        if progress["finished"] is None:
            raise PermissionError

    # Fetch all concepts
    concepts = compiled.find({"_id": {"$ne": "PROGRESS"}})

    # Define how to export as python
    def export_as_python(cc):
        # Collect the concepts into a dictionary
        ontology = {}
        for c in cc:
            id = c.pop("_id")
            ontology[id] = c

        # Pickle
        import pickle
        filename = path + "/" + "compiled_" + collection + ".p"
        f = open(filename, "wb")
        pickle.dump(ontology, f)
        f.close()

        # Return file pointer for download
        return filename

    # Define how to export as lisp
    def export_as_lisp(cc):
        # Collect the concepts into a list

        def map_concept(concept: str, slots: dict):
            slots.pop("_id")
            slots = list(slots.items())
            return "(%s %s)" % (concept, " ".join(list(map(lambda s: map_slot(*s), slots))))

        def map_slot(slot: str, facets: dict):
            facets = list(facets.items())
            return "(%s %s)" % (slot, " ".join(list(map(lambda f: map_facet(*f), facets))))

        def map_facet(facet: str, fillers):
            return "(%s %s)" % (facet, " ".join(fillers))

        ontology = list(map(lambda c: map_concept(c["_id"], c), cc))

        filename = path + "/" + "compiled_" + collection + ".lisp"
        out = open(filename, "w")
        for line in ontology:
            out.write(line)
            out.write("\n")
        out.close()

        return filename

    if format == "python":
        return export_as_python(concepts)
    if format == "lisp":
        return export_as_lisp(concepts)

    raise Exception