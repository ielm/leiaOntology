from os.path import join
from pymongo import MongoClient
from typing import Set, Tuple

import boto3
import os
import pymongo.errors
import subprocess
import time

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

def compile(collection: str, compile_inherited_values: bool=False, compile_domains_and_ranges: bool=False, compile_inverses: bool=False):
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

    # Connect to the API
    from ont.api import OntologyAPI
    api = OntologyAPI(collection=db[collection])

    # List all of the concepts
    concepts = set(api.list())

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

    # Calculate the relations and inverses
    relations = api.relations_to_inverses()

    # Calculate the full ancestry and define a helper method
    ancestry = api.full_ancestry()

    def ancestors_or_default(c):
        try:
            return ancestry[c]
        except:
            return set()

    # Define a helper method for reducing any set of concepts to their common set of ancestors
    def reduce_to_common_ancestors(concepts: Set[str]) -> Set[str]:
        to_prune = set()

        for c in concepts:
            # If any of the filler's ancestors are in the list of concepts it can be pruned
            ancestors = ancestors_or_default(c)
            if len(ancestors.intersection(concepts)) > 0:
                to_prune.add(c)

        return concepts.difference(to_prune)

    # Define a helper method for determining the domains and ranges of a given property
    def get_domain_range(property: str) -> Tuple[Set[str], Set[str]]:
        coll = api.collection

        pipeline = [
            {"$match": {"localProperties.slot": property}},
            {"$project": {"localProperties": 1, "_id": "$name"}},
            {"$unwind": "$localProperties"},
            {"$match": {"localProperties.slot": property}},
            {"$project": {"range": "$localProperties.filler"}}
        ]
        results = list(coll.aggregate(pipeline))

        domains = set(map(lambda r: r["_id"], results))
        ranges = set(map(lambda r: r["range"], results))

        domains = reduce_to_common_ancestors(domains)

        if "relation" in ancestors_or_default(property):
            ranges = reduce_to_common_ancestors(ranges)

        return domains, ranges

    # Define a helper method for explicitly populating a frame with its inverses (NOT USED AT THIS TIME)
    def populate_inverses(c: str, frame: dict):
        usages = api.report(c, include_usage=True, usage_with_inheritance=compile_inherited_values)
        inv_slots = set()
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

            # Note which inverses have been used in this frame
            inv_slots.add(slot)

        # Reduce all inverse to their common ancestors
        for slot in inv_slots:
            for facet in frame[c][slot].keys():
                fillers = set(frame[c][slot][facet])
                fillers = reduce_to_common_ancestors(fillers)
                frame[c][slot][facet] = list(fillers)

    # Define a helper method to declare a slot/facet if needed
    def declare_slot_facet(frame: dict, slot: str, facet: str):
        if slot not in frame:
            frame[slot] = {}
        if facet not in frame[slot]:
            frame[slot][facet] = []

    # Define a helper method to format the frame (with upper casing, etc.)
    def format_frame_for_insert(frame: dict) -> dict:
        frame = frame[c]
        for slot_name in list(frame.keys()):
            slot = frame.pop(slot_name)
            frame[slot_name.upper()] = slot

            for facet_name in list(slot.keys()):
                facet = slot.pop(facet_name)
                slot[facet_name.upper()] = list(map(lambda filler: filler.upper() if filler in concepts or slot_name == "inverse" else filler, facet))

        frame["_id"] = c.upper()
        return frame

    # Initialize the state
    count = 0
    properties = []

    # Compile each concept
    local = not compile_inherited_values
    for c in concepts:
        frame = api.get(c, local=local)[0]

        if compile_domains_and_ranges and "property" in ancestors_or_default(c):
            domains, ranges = get_domain_range(c)

            declare_slot_facet(frame[c], "domain", "sem")
            frame[c]["domain"]["sem"] = domains

            declare_slot_facet(frame[c], "range", "sem")
            frame[c]["range"]["sem"] = ranges

        # Convert frame names, slots, facets, and relation fillers to upper case
        frame = format_frame_for_insert(frame)

        if compile_inverses and "relation" in ancestors_or_default(c):
            properties.append(frame)

        count += 1
        compiled.insert_one(frame)
        compiled.update_one(
            {"_id": "PROGRESS"},
            {"$set": {"status.count": count, "status.last": c}}
        )

    # Compile each inverse property (this list will be empty if compile_inverses is False)
    import copy
    for property in properties:
        inverse = copy.deepcopy(property)
        inverse["_id"] = relations[property["_id"].lower()].upper()

        if inverse["_id"].lower() in relations.keys():
            continue

        inverse["INVERSE"] = {"VALUE": [property["_id"]]}

        declare_slot_facet(inverse, "DOMAIN", "SEM")
        declare_slot_facet(inverse, "RANGE", "SEM")

        inverse["DOMAIN"]["SEM"] = property["RANGE"]["SEM"]
        inverse["RANGE"]["SEM"] = property["DOMAIN"]["SEM"]

        try:
            compiled.insert_one(inverse)
        except pymongo.errors.DuplicateKeyError as e:
            print("Duplicate key %s" % inverse["_id"])

        # Add the inverse as an explicit SUBCLASSES value of its parent
        compiled.update_one(
            {"_id": property["IS-A"]["VALUE"][0]},
            {"$push": {"SUBCLASSES.VALUE": inverse["_id"]}}
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

            for slot in c.keys():
                for facet in c[slot].keys():
                    fillers = c[slot][facet]
                    if len(fillers) == 1:
                        c[slot][facet] = fillers[0]

        # Pickle
        import pickle
        filename = path + "/" + "ontology_" + collection + ".p"
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

        filename = path + "/" + "ontology_" + collection + ".lisp"
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