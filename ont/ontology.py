import json
import os
import sys


class Ontology():

    def __init__(self, host=None, port=None, cookie=None):
        self.host = host
        if self.host is None:
            self.host = os.environ["ONTOLOGY_HOST"] if "ONTOLOGY_HOST" in os.environ else "localhost"

        self.port = port
        if self.port is None:
            self.port = int(os.environ["ONTOLOGY_PORT"]) if "ONTOLOGY_PORT" in os.environ else 8080

        self.cookie = cookie

    def __contains__(self, item):
        return len(self.get([item])) > 0

    def __getitem__(self, item):
        results = self.get([item])
        if len(results) > 0:
            return self.__get_single(item, results)

        raise Exception("Concept " + item + " not found.")

    def __rpost(self, path, data=None):
        url = "http://" + self.host + ":" + str(self.port) + path

        if data is None:
            data = {}

        def post_python2(ontology, url, data):
            import urllib2
            data = json.dumps(data)
            request = urllib2.Request(url, data, {'Content-Type': 'application/json'})
            if self.cookie is not None:
                request.add_header("cookie", self.cookie)

            f = urllib2.urlopen(request)
            response = f.read()
            ontology.cookie = response.headers.get("Set-Cookie")

            f.close()
            return response

        def post_python3(ontology, url, data):
            from urllib.request import Request, urlopen

            data = json.dumps(data).encode('utf8')
            request = Request(url, data=data, headers={'content-type': 'application/json'})
            if self.cookie is not None:
                request.add_header("cookie", self.cookie)

            response = urlopen(request)
            ontology.cookie = response.headers.get("Set-Cookie")

            return response

        if sys.version_info[0] < 3:
            return post_python2(self, url, data)
        else:
            return post_python3(self, url, data)

    def __rget(self, path, params=None):
        url = "http://" + self.host + ":" + str(self.port) + path

        def __format_param(key):
            values = params[key]
            if type(values) is not list:
                values = [values]

            return "&".join(map(lambda value: key + "=" + str(value), values))

        if len(params) > 0:
            url = url + "?" + "&".join(map(__format_param, params.keys()))

        def get_python2(ontology, url):
            import urllib2
            request = urllib2.Request(url)
            if self.cookie is not None:
                request.add_header("cookie", self.cookie)
            response = urllib2.urlopen(request)
            ontology.cookie = response.headers.get("Set-Cookie")
            contents = response.read()
            return contents

        def get_python3(ontology, url):
            import urllib.request
            request = urllib.request.Request(url)
            if self.cookie is not None:
                request.add_header("cookie", self.cookie)
            contents = None
            with urllib.request.urlopen(request) as response:
                contents = response.read()
                self.cookie = response.headers.get("Set-Cookie")
            return contents

        if sys.version_info[0] < 3:
            return get_python2(self, url)
        else:
            return get_python3(self, url)

    def __get_single(self, concept, concepts):
        for c in concepts:
            if concept in c:
                return c[concept]

        raise Exception("Concept " + concept + " not found.")

    def get(self, concepts):
        if type(concepts) is not list:
            concepts = [concepts]

        results = self.__rget("/ontology/api/get", params={"concept": concepts})
        return json.loads(results)

    def ancestors(self, concept, immediate=False, details=False, paths=False):
        results = self.__rget("/ontology/api/ancestors", params={"concept": concept, "immediate": immediate, "details": details, "paths": paths})
        return json.loads(results)

    def descendants(self, concept, immediate=False, details=False, paths=False):
        results = self.__rget("/ontology/api/descendants", params={"concept": concept, "immediate": immediate, "details": details, "paths": paths})
        return json.loads(results)

    def is_parent(self, concept, parent):
        results = self.ancestors(concept, immediate=False, details=False)
        return parent in results

    def exists(self, concept):
        concepts = map(lambda result: result.keys(), self.get(concept))
        concepts = [item for sublist in concepts for item in sublist]   # Flattens the lists / reduces
        return concept in concepts

    def get_subtree(self, concept):
        results = self.ancestors(concept, immediate=False, details=False)

        subtrees = ["object", "event", "property"]
        for subtree in subtrees:
            if subtree in results:
                return subtree

        raise Exception("Concept " + concept + " is not in the three standard subtrees.  Ancestry is: " + results + ".")

    def has_property(self, concept, property):
        results = self.get(concept)
        concept = self.__get_single(concept, results)

        return property in concept

    def get_constraints(self, concept, property):
        results = self.get(concept)
        concept = self.__get_single(concept, results)

        if property in concept:
            if "sem" in concept[property]:
                return concept[property]["sem"]

        return []

    def get_inverses(self, property):
        results = self.get(property)
        property = self.__get_single(property, results)

        if "inverse" in property:
            return property["inverse"]

        return {}

    def all_inverses(self):
        results = self.__rget("/ontology/api/inverses", params=[])
        return json.loads(results)

    def all_relations(self, inverses=False):
        results = self.__rget("/ontology/api/relations", params={"inverses": inverses})
        return json.loads(results)

    def update_definition(self, concept: str, definition: str):
        self.__rpost("/ontology/edit/define/" + concept, data={"definition": definition})

    def insert_property(self, concept: str, slot: str, facet: str, filler: str):
        self.__rpost("/ontology/edit/insert/" + concept, data={"slot": slot, "facet": facet, "filler": filler})

    def remove_property(self, concept: str, slot: str, facet: str, filler: str):
        self.__rpost("/ontology/edit/remove/" + concept, data={"slot": slot, "facet": facet, "filler": filler})

    def block_property(self, concept: str, slot: str, facet: str, filler: str):
        self.__rpost("/ontology/edit/block/" + concept, data={"slot": slot, "facet": facet, "filler": filler})

    def unblock_property(self, concept: str, slot: str, facet: str, filler: str):
        self.__rpost("/ontology/edit/unblock/" + concept, data={"slot": slot, "facet": facet, "filler": filler})

    def add_parent(self, concept: str, parent: str):
        self.__rpost("/ontology/edit/add_parent/" + concept, data={"parent": parent})

    def remove_parent(self, concept: str, parent: str):
        self.__rpost("/ontology/edit/remove_parent/" + concept, data={"parent": parent})

    def add_concept(self, concept: str, parent: str, definition: str):
        self.__rpost("/ontology/edit/add_concept", data={"concept": concept, "parent": parent, "definition": definition})

    def remove_concept(self, concept: str, include_usages: bool=True):
        self.__rpost("/ontology/edit/remove_concept/" + concept, data={"include_usages": include_usages})
