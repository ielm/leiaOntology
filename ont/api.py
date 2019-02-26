from typing import List, Union

import ont.management


class OntologyAPI(object):

    def __init__(self):
        self.collection = ont.management.handle()
        self._cache = {}

    def get(self, concepts: Union[str, List[str]], metadata: bool=False) -> List[dict]:
        if isinstance(concepts, str):
            concepts = [concepts]

        results = []
        for record in self.collection.find({"$or": list(map(lambda concept: {"name": concept}, concepts))}):
            results.append(self.format(record, metadata=metadata))

        return results

    def ancestors(self, concept: str, immediate: bool=False, details: bool=False, paths: bool=False) -> Union[List[str], List[List[str]], List[dict], List[List[dict]]]:
        pipeline = [
            {
                "$match": {
                    "name": concept
                }
            }
        ]

        if immediate:
            pipeline.append({
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$parents",
                    "connectFromField": "parents",
                    "connectToField": "name",
                    "as": "ancestors",
                    "maxDepth": 0
                }
            })
        else:
            pipeline.append({
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$parents",
                    "connectFromField": "parents",
                    "connectToField": "name",
                    "as": "ancestors"
                }
            })

        result = list(self.collection.aggregate(pipeline))[0]
        self.cache([result])
        self.cache(result["ancestors"])

        def build_paths(name, current_path=None):
            if current_path is None:
                current_path = []

            concept = self._cache[name]

            if len(concept["parents"]) == 0:
                return [current_path]

            paths = []
            for parent in concept["parents"]:
                for path in build_paths(parent, current_path + [parent]):
                    paths.append(path)

            return paths

        output = [list(map(lambda ancestor: ancestor["name"], result["ancestors"]))]
        if paths:
            output = list(filter(lambda path: len(path) > 0, build_paths(result["name"])))

        if details:
            output = list(map(lambda path: list(map(lambda concept: self.format(self._cache[concept]), path)), output))

        if not paths:
            return output[0]
        return output

    def descendants(self, concept: str, immediate: bool = False, details: bool = False, paths: bool = False) -> Union[List[str], List[List[str]], List[dict], List[List[dict]]]:
        pipeline = [
            {
                "$match": {
                    "name": concept
                }
            }
        ]

        if immediate:
            pipeline.append({
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$name",
                    "connectFromField": "name",
                    "connectToField": "parents",
                    "as": "descendants",
                    "maxDepth": 0
                }
            })
        else:
            pipeline.append({
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$name",
                    "connectFromField": "name",
                    "connectToField": "parents",
                    "as": "descendants"
                }
            })

        result = list(self.collection.aggregate(pipeline))[0]
        self.cache([result])
        self.cache(result["descendants"])

        def build_paths(name, current_path=None):
            if current_path is None:
                current_path = []

            c = self._cache[name]

            if len(c["parents"]) == 0:
                return [current_path]

            paths = []
            for parent in filter(lambda parent: parent != concept, c["parents"]):
                for path in build_paths(parent, current_path + [parent]):
                    paths.append(path)

            if len(paths) == 0:
                return [current_path]

            return paths

        output = [list(map(lambda descendant: descendant["name"], result["descendants"]))]
        if paths:
            output = map(lambda descendant: build_paths(descendant, current_path=[descendant]), output[0])
            output = [item for sublist in output for item in sublist]
            output = list(map(lambda path: list(reversed(path)), output))

        if details:
            output = list(map(lambda path: list(map(lambda concept: self.format(self._cache[concept]), path)), output))

        if not paths:
            return output[0]
        return output

    def siblings(self, concept: str) -> List[str]:
        pipeline = [
            {"$match": {"name": concept}},
            {
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$parents",
                    "connectFromField": "name",
                    "connectToField": "parents",
                    "as": "children",
                    "maxDepth": 1,
                }
            },
            {"$unwind": "$children"},
            {"$project": {"name": "$children.name", "iparents": {
            "$gt": [{"$size": {"$setIntersection": ["$parents", "$children.parents"]}}, 0]}}},
            {"$match": {"name": {"$ne": concept}}},
            {"$match": {"iparents": True}}
        ]

        siblings = list(self.collection.aggregate(pipeline))
        siblings = list(map(lambda s: s["name"], siblings))
        siblings = sorted(siblings)

        return siblings

    def inverses(self) -> List[str]:
        pipeline = [
            {"$match": {"localProperties": {"$elemMatch": {"slot": "inverse"}}}},
            {"$project": {"inverse": {"$arrayElemAt": ["$localProperties.filler", 0]}}},
            {"$group": {"_id": "result", "inverses": {"$push": "$inverse"}}}
        ]

        result = list(self.collection.aggregate(pipeline))[0]
        result = result["inverses"]

        return result

    def relations(self, inverses: bool=False) -> List[str]:
        pipeline = [
            {
                "$match": {
                    "name": "relation"
                }
            }, {
                "$graphLookup": {
                    "from": ont.management.active(),
                    "startWith": "$name",
                    "connectFromField": "name",
                    "connectToField": "parents",
                    "as": "descendants"
                }
            }, {
                "$unwind": {
                    "path": "$descendants"
                }
            },
            {
                "$project": {
                    "rel": "$descendants.name"
                }
            }
        ]

        result = list(self.collection.aggregate(pipeline))
        result = list(map(lambda r: r["rel"], result))
        result.append("relation")

        if inverses:
            pipeline = [
                {"$match": {"localProperties": {"$elemMatch": {"slot": "inverse"}}}},
                {"$project": {"inverse": {"$arrayElemAt": ["$localProperties.filler", 0]}}},
                {"$group": {"_id": "result", "inverses": {"$push": "$inverse"}}}
            ]

            inverses = list(self.collection.aggregate(pipeline))
            if len(inverses) > 0:
                inverses = inverses[0]
                inverses = inverses["inverses"]

                result.extend(inverses)

        return result

    def update_definition(self, concept: str, definition: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$set": {
                "definition": definition
            }
        })

    def insert_property(self, concept: str, slot: str, facet: str, filler: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$push": {
                "localProperties": {
                    "slot": slot.lower(),
                    "facet": facet.lower(),
                    "filler": filler
                }
            }
        })

    def remove_property(self, concept: str, slot: str, facet: str, filler: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$pull": {
                "localProperties": {
                    "slot": slot.lower(),
                    "facet": facet.lower(),
                    "filler": filler
                }
            }
        })

    def block_property(self, concept: str, slot: str, facet: str, filler: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$push": {
                "totallyRemovedProperties": {
                    "slot": slot.lower(),
                    "facet": facet.lower(),
                    "filler": filler
                }
            }
        })

    def cache(self, concepts):
        for concept in concepts:
            self._cache[concept["name"]] = concept

    def format(self, concept, metadata: bool=False):
        output = {
            "is-a": {"value": concept["parents"]},
            "subclasses": {"value": list(map(lambda record: record["name"], self.collection.find({"parents": concept["name"]})))}
        }

        for property in self._inherit(concept, metadata=metadata):
            self._add_property(output, property, metadata=metadata)

        if metadata:
            relations = self.relations(inverses=True)
            for property in output:
                output[property]["is_relation"] = property in relations

            output["_metadata"] = {
                "definition": concept["definition"]
            }

        return {
            concept["name"]: output
        }

    def _add_property(self, output, property, metadata: bool=False):
        slot = property["slot"]
        facet = property["facet"]
        filler = property["filler"]

        if metadata:
            filler = {
                "filler": filler,
                "defined_in": property["metadata"]["defined_in"],
                "blocked": property["metadata"]["blocked"] if "blocked" in property["metadata"] else False
            }

        if slot not in output:
            output[slot] = {}
        if facet not in output[slot]:
            output[slot][facet] = [filler]
        elif type(output[slot][facet]) != list:
            output[slot][facet] = [output[slot][facet], filler]
        else:
            output[slot][facet].append(filler)

    def _inherit(self, concept, metadata: bool=False):
        properties = concept["localProperties"]

        if metadata:
            for p in properties:
                p["metadata"] = {
                    "defined_in": concept["name"]
                }

        for parent_name in concept["parents"]:
            parent = self._cache[parent_name] if parent_name in self._cache else self.collection.find_one({"name": parent_name})

            if parent_name not in self._cache:
                self.cache([parent])

            inherited = self._inherit(parent, metadata=metadata)
            inherited = self._remove_overridden_fillers(inherited, concept["overriddenFillers"])
            inherited = self._remove_deleted_fillers(inherited, concept["totallyRemovedProperties"], metadata=metadata)
            inherited = self._prune_list(inherited, properties) # Clean up any duplicates, retaining local copies

            properties = properties + inherited

        return properties

    def _remove_overridden_fillers(self, properties, overridden_fillers):
        properties = self._prune_list(properties, overridden_fillers)
        return properties

    def _remove_deleted_fillers(self, properties, deleted_fillers, metadata=False):
        if metadata:
            properties = list(filter(lambda p: not ("blocked" in p["metadata"] and p["metadata"]["blocked"]), properties))
            for inherited in properties:
                if {"slot": inherited["slot"], "facet": inherited["facet"], "filler": inherited["filler"]} in deleted_fillers:
                    inherited["metadata"]["blocked"] = True
            return properties

        return self._prune_list(properties, deleted_fillers)

    def _prune_list(self, enclosing_list, to_remove):
        pruned = [e for e in enclosing_list if {"slot": e["slot"], "facet": e["facet"], "filler": e["filler"]} not in to_remove]
        return pruned

