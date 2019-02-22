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


if __name__ == "__main__":
    o = Ontology(port=5003)
    o.cookie = "webpy_session_id=0f2ba5e1330a12db1fa1aabbb2532e117da65aa9; Path=/; httponly"

    print(o.get(["xyzabc"]))
    print(o.get(["tick", "automobile"]))
    # print(o.ancestors("tick", immediate=True, details=True))
    # print(o.descendants("mite", immediate=True, details=True))
    # print(o.is_parent("mite", "event"))
    # print(o.exists("mite"))
    # print(o.get_subtree("mite"))
    # print(o.has_property("mite", "has-object-as-part"))
    # print(o.get_constraints("mite", "has-object-as-part"))
    # print(o.get_inverses("has-object-as-part"))

    print("benchmarks:")

    import time
    def timeit(func, iterations, description, *args, **kwargs):
        start = time.time()
        for i in range(0, iterations, 1):
            func(*args, **kwargs)
        end = time.time()
        print("Time to " + description + " x" + str(iterations) + " = " + str(end - start))

    timeit(o.get, 5, "Get 'tick'", ["tick"])
    timeit(o.get, 5, "Get 'automobile'", ["automobile"])
    timeit(o.get, 5, "Get 'tick and automobile'", ["tick", "automobile"])
    timeit(o.ancestors, 5, "Ancestors 'tick'", ["tick"])
    timeit(o.ancestors, 5, "Ancestors 'tick' (immediate)", ["tick"], immediate=True)
    timeit(o.ancestors, 5, "Ancestors 'tick' (details)", ["tick"], details=True)
    timeit(o.ancestors, 5, "Ancestors 'tick' (paths)", ["tick"], paths=True)
    timeit(o.descendants, 5, "Descendants 'mite'", ["mite"])
    timeit(o.descendants, 5, "Descendants 'mite' (immediate)", ["mite"], immediate=True)
    timeit(o.descendants, 5, "Descendants 'mite' (details)", ["mite"], details=True)
    timeit(o.descendants, 5, "Descendants 'mite' (paths)", ["mite"], paths=True)
    timeit(o.is_parent, 5, "Is parent 'mite' / 'event'", "mite", "event")
    timeit(o.exists, 5, "Exists 'mite'", "mite")
    timeit(o.get_subtree, 5, "Get subtree 'mite'", "mite")
    timeit(o.has_property, 5, "Has property 'mite' / 'has-object-as-part'", "mite", "has-object-as-part")
    timeit(o.get_constraints, 5, "Get constraints 'mite' / 'has-object-as-part'", "mite", "has-object-as-part")
    timeit(o.get_inverses, 5, "Get inverses 'has-object-as-part'", "has-object-as-part")