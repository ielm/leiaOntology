from typing import List, Union

import ont.management


class OntologyAPI(object):

    def __init__(self, collection=None):
        if collection is None:
            self.collection = ont.management.handle()
        else:
            self.collection = collection
        self._cache = {}

    def list(self) -> List[str]:
        pipeline = [
            {"$project": {"name": 1, "_id": 0}},
            {"$group": {"_id": None, "all": {"$addToSet": "$name"}}}
        ]
        results = list(self.collection.aggregate(pipeline))

        return sorted(results[0]["all"])

    def get(self, concepts: Union[str, List[str]], local: bool=False, metadata: bool=False) -> List[dict]:
        if isinstance(concepts, str):
            concepts = [concepts]

        results = []
        for record in self.collection.find({"$or": list(map(lambda concept: {"name": concept}, concepts))}):
            results.append(self.format(record, local=local, metadata=metadata))

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
                    "from": self.collection.name,
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
                    "from": self.collection.name,
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
                    "from": self.collection.name,
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
                    "from": self.collection.name,
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
                    "from": self.collection.name,
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
                    "from": self.collection.name,
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

    def full_ancestry(self) -> dict:
        pipeline = [
            {
                "$graphLookup": {
                    "from": self.collection.name,
                    "startWith": "$parents",
                    "connectFromField": "parents",
                    "connectToField": "name",
                    "as": "ancestors"
                }
            },
            {"$project": {"ancestry": "$ancestors.name", "name": 1}}
        ]

        ancestry = {}
        for d in self.collection.aggregate(pipeline):
            ancestry[d["name"]] = set(d["ancestry"])
        return ancestry

    def relations_to_inverses(self) -> dict:

        pipeline = [
            {
                "$match": {
                    "name": "relation"
                }
            }, {
                "$graphLookup": {
                    "from": self.collection.name,
                    "startWith": "$name",
                    "connectFromField": "name",
                    "connectToField": "parents",
                    "as": "descendants"
                }
            }, {
                "$unwind": {
                    "path": "$descendants"
                }
            }, {
                "$replaceRoot": {
                    "newRoot": "$descendants"
                }
            },

            {
                "$graphLookup": {
                    "from": "canonical-v.1.0.1",
                    "startWith": "$parents",
                    "connectFromField": "parents",
                    "connectToField": "name",
                    "as": "ancestors"
                }
            },
            {"$addFields": {"ancestry": {"$setUnion": ["$ancestors.name", ["$name"]]}}},
            {"$project": {"ancestors": 0}}
        ]

        results = list(self.collection.aggregate(pipeline))

        relations = {"relation": "relation"}
        for r in results:
            for lp in r["localProperties"]:
                if lp["slot"] == "inverse":
                    relations[r["name"]] = lp["filler"]

        for r in results:
            if r["name"] not in relations:
                for ancestor in reversed(r["ancestry"]):
                    if ancestor in relations:
                        relations[r["name"]] = relations[ancestor]

        return relations

    def report(self, concept: str, include_usage: bool=False, usage_with_inheritance: bool=False):
        report = {}

        if include_usage:
            report["usage"] = {}

            pipeline = [
                {"$match": {"parents": concept}},
                {"$project": {"name": 1, "_id": 0}}
            ]
            report["usage"]["subclasses"] = list(map(lambda o: o["name"], self.collection.aggregate(pipeline)))


            pipeline: List[dict] = [
                {"$match": {"name": concept}},
            ]

            if not usage_with_inheritance:
                pipeline.append({"$addFields": {"ancestry": [concept]}})
            else:
                pipeline.extend([
                    {
                        "$graphLookup": {
                            "from": self.collection.name,
                            "startWith": "$parents",
                            "connectFromField": "parents",
                            "connectToField": "name",
                            "as": "ancestors"
                        }
                    },
                    {"$addFields": {"ancestry": {"$setUnion": ["$ancestors.name", [concept]]}}}
                ])

            pipeline.extend([
                {"$lookup": {
                    "from": self.collection.name,
                    "localField": "ancestry",
                    "foreignField": "localProperties.filler",
                    "as": "usages"
                }
                },
                {"$unwind": "$usages"},
                {"$project":
                    {
                        "ancestry": 1,
                        "name": "$usages.name",
                        "localProperties": "$usages.localProperties"
                    }
                },
                {"$unwind": "$ancestry"},
                {"$unwind": "$localProperties"},
                {"$project":
                    {
                        "ancestry": 1,
                        "name": 1,
                        "slot": "$localProperties.slot",
                        "facet": "$localProperties.facet",
                        "filler": "$localProperties.filler",
                    }
                },
                {"$match": {"$expr": {"$eq": ["$filler", "$ancestry"]}}},
                {"$project": {"ancestry": 0, "_id": 0}}
            ])

            report["usage"]["inverses"] = list(map(lambda o: {
                "concept": o["name"],
                "slot": o["slot"],
                "facet": o["facet"],
                "filler": o["filler"],
            }, self.collection.aggregate(pipeline)))

        return report

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

    def unblock_property(self, concept: str, slot: str, facet: str, filler: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$pull": {
                "totallyRemovedProperties": {
                    "slot": slot.lower(),
                    "facet": facet.lower(),
                    "filler": filler
                }
            }
        })

    def add_parent(self, concept: str, parent: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$push": {
                "parents": parent
            }
        })

    def remove_parent(self, concept: str, parent: str):
        self.collection.update_one({
            "name": concept.lower(),
        }, {
            "$pull": {
                "parents": parent
            }
        })

    def add_concept(self, concept: str, parent: Union[str, None], definition: str):
        parents = [parent]
        if parent is None:
            parents = []

        self.collection.insert_one({
            "name": concept,
            "parents": parents,
            "definition": definition,
            "notes": "",
            "reified": False,
            "reified_in": "",
            "localProperties": [],
            "overriddenFillers": [],
            "totallyRemovedProperties": []
        })

    def remove_concept(self, concept: str, include_usages: bool=False):
        if include_usages:
            report = self.report(concept, include_usage=True)
            for child in report["usage"]["subclasses"]:
                self.collection.update_one({
                    "name": child
                }, {
                    "$pull": {
                        "parents": concept
                    }
                })
            for inverse in report["usage"]["inverses"]:
                self.collection.update_one({
                    "name": inverse["concept"]
                }, {
                    "$pull": {
                        "localProperties": {
                            "slot": inverse["slot"],
                            "facet": inverse["facet"],
                            "filler": inverse["filler"]
                        }
                    }
                })

        self.collection.delete_one({
            "name": concept
        })

    def cache(self, concepts):
        for concept in concepts:
            self._cache[concept["name"]] = concept

    def format(self, concept, local: bool=False, metadata: bool=False):
        output = {
            "is-a": {"value": concept["parents"]},
            "subclasses": {"value": list(map(lambda record: record["name"], self.collection.find({"parents": concept["name"]})))}
        }

        if local:
            properties = concept["localProperties"]
            for p in properties:
                if metadata:
                    p["metadata"] = {
                        "defined_in": concept["name"]
                    }
                self._add_property(output, p, metadata=metadata)
        else:
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

