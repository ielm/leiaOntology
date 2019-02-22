import ont.management


def mock_concept(name, definition=None, parents=None, localProperties=None, overriddenFillers=None, totallyRemovedProperties=None):
    if definition is None:
        definition = ""

    if parents is None:
        parents = []

    if localProperties is None:
        localProperties = []

    if overriddenFillers is None:
        overriddenFillers = []

    if totallyRemovedProperties is None:
        totallyRemovedProperties = []

    collection = ont.management.handle()

    concept = {
        "name": name,
        "definition": definition,
        "parents": parents,
        "localProperties": localProperties,
        "overriddenFillers": overriddenFillers,
        "totallyRemovedProperties": totallyRemovedProperties
    }

    collection.insert_one(concept)
    return concept