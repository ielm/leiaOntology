from ont.api import OntologyAPI
from ont.service import app as service
from tests.TestUtils import mock_concept

import json
import ont.management
import os
import unittest


class APIGetServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_get(self):
        concept = mock_concept("concept")

        response = self.app.get("/ontology/api/get?concept=concept")
        response = json.loads(response.data)
        self.assertEqual(response, [OntologyAPI().format(concept)])

    def test_get_multiple(self):
        concept1 = mock_concept("concept1")
        concept2 = mock_concept("concept2")

        response = self.app.get("/ontology/api/get?concept=concept1&concept=concept2")
        response = json.loads(response.data)
        self.assertTrue(OntologyAPI().format(concept1) in response)
        self.assertTrue(OntologyAPI().format(concept2) in response)
        
        
class APIAncestorsServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_ancestors(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        response = self.app.get("/ontology/api/ancestors?concept=concept")
        response = json.loads(response.data)

        self.assertEqual(3, len(response))
        self.assertTrue("parent" in response)
        self.assertTrue("grandparent1" in response)
        self.assertTrue("grandparent2" in response)

    def test_ancestors_immediate(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        response = self.app.get("/ontology/api/ancestors?concept=concept&immediate=True")
        response = json.loads(response.data)

        self.assertEqual(1, len(response))
        self.assertTrue("parent" in response)

    def test_ancestors_details(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        response = self.app.get("/ontology/api/ancestors?concept=concept&details=True")
        response = json.loads(response.data)

        self.assertEqual(3, len(response))
        self.assertTrue(OntologyAPI().format(parent) in response)
        self.assertTrue(OntologyAPI().format(grandparent1) in response)
        self.assertTrue(OntologyAPI().format(grandparent2) in response)

    def test_ancestors_paths(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        response = self.app.get("/ontology/api/ancestors?concept=concept&paths=True")
        response = json.loads(response.data)

        self.assertEqual(2, len(response))
        self.assertTrue(["parent", "grandparent1"] in response)
        self.assertTrue(["parent", "grandparent2"] in response)

        response = self.app.get("/ontology/api/ancestors?concept=parent&paths=True")
        response = json.loads(response.data)

        self.assertEqual(2, len(response))
        self.assertTrue(["grandparent1"] in response)
        self.assertTrue(["grandparent2"] in response)

        response = self.app.get("/ontology/api/ancestors?concept=grandparent1&paths=True")
        response = json.loads(response.data)

        self.assertEqual(0, len(response))


class APIDescendantsServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_descendants(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = self.app.get("/ontology/api/descendants?concept=grandparent")
        response = json.loads(response.data)

        self.assertEqual(3, len(response))
        self.assertTrue("parent" in response)
        self.assertTrue("concept1" in response)
        self.assertTrue("concept2" in response)

    def test_descendants_immediate(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = self.app.get("/ontology/api/descendants?concept=grandparent&immediate=True")
        response = json.loads(response.data)

        self.assertEqual(1, len(response))
        self.assertTrue("parent" in response)

    def test_descendants_details(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = self.app.get("/ontology/api/descendants?concept=grandparent&details=True")
        response = json.loads(response.data)

        self.assertEqual(3, len(response))
        self.assertTrue(OntologyAPI().format(parent) in response)
        self.assertTrue(OntologyAPI().format(concept1) in response)
        self.assertTrue(OntologyAPI().format(concept2) in response)

    def test_descendants_paths(self):
        concept1 = mock_concept("concept1", parents=["parent1"])
        concept2 = mock_concept("concept2", parents=["parent2"])
        parent1 = mock_concept("parent1", parents=["grandparent"])
        parent2 = mock_concept("parent2", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = self.app.get("/ontology/api/descendants?concept=grandparent&paths=True")
        response = json.loads(response.data)

        self.assertEqual(4, len(response))
        self.assertTrue(["parent1"] in response)
        self.assertTrue(["parent2"] in response)
        self.assertTrue(["parent1", "concept1"] in response)
        self.assertTrue(["parent2", "concept2"] in response)

        response = self.app.get("/ontology/api/descendants?concept=parent1&paths=True")
        response = json.loads(response.data)

        self.assertEqual(1, len(response))
        self.assertTrue(["concept1"] in response)

        response = self.app.get("/ontology/api/descendants?concept=concept1&paths=True")
        response = json.loads(response.data)

        self.assertEqual(0, len(response))


class APIInversesServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_inverses(self):
        mock_concept("rel1", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4")

        response = self.app.get("/ontology/api/inverses")
        response = json.loads(response.data)

        self.assertEqual(3, len(response))
        self.assertTrue("rel1-of" in response)
        self.assertTrue("rel2-of" in response)
        self.assertTrue("rel3-of" in response)
        self.assertTrue("rel4-of" not in response)


class APIRelationsServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_relations(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", parents=["rel2"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4", parents=["relation"],)

        response = self.app.get("/ontology/api/relations")
        response = json.loads(response.data)

        self.assertEqual(5, len(response))
        self.assertTrue("relation" in response)
        self.assertTrue("rel1" in response)
        self.assertTrue("rel2" in response)
        self.assertTrue("rel3" in response)
        self.assertTrue("rel4" in response)
        self.assertTrue("rel1-of" not in response)
        self.assertTrue("rel2-of" not in response)
        self.assertTrue("rel3-of" not in response)

    def test_relations_include_inverses(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", parents=["rel2"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4", parents=["relation"])

        response = self.app.get("/ontology/api/relations?inverses=True")
        response = json.loads(response.data)

        self.assertEqual(8, len(response))
        self.assertTrue("relation" in response)
        self.assertTrue("rel1" in response)
        self.assertTrue("rel2" in response)
        self.assertTrue("rel3" in response)
        self.assertTrue("rel4" in response)
        self.assertTrue("rel1-of" in response)
        self.assertTrue("rel2-of" in response)
        self.assertTrue("rel3-of" in response)


class APIEditDefineServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_define(self):
        mock_concept("test", definition="abcd")

        data = {
            "definition": "xyz"
        }

        response = self.app.post("/ontology/edit/define/test",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        results = OntologyAPI().get("test", metadata=True)
        self.assertEqual("xyz", results[0]["test"]["_metadata"]["definition"])


class APIEditInsertServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_insert(self):
        mock_concept("test")

        data = {
            "slot": "xyz",
            "facet": "sem",
            "filler": "value1"
        }

        response = self.app.post("/ontology/edit/insert/test",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        results = OntologyAPI().get("test")
        self.assertEqual(["value1"], results[0]["test"]["xyz"]["sem"])


class APIEditRemoveServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_remove(self):
        mock_concept("test", localProperties=[
            {"slot": "xyz", "facet": "sem", "filler": "value1"},
            {"slot": "xyz", "facet": "sem", "filler": "value2"}
        ])

        data = {
            "slot": "xyz",
            "facet": "sem",
            "filler": "value2"
        }

        response = self.app.post("/ontology/edit/remove/test",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        results = OntologyAPI().get("test")
        self.assertEqual(["value1"], results[0]["test"]["xyz"]["sem"])


class APIEditBlockServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_block(self):
        mock_concept("parent", localProperties=[
            {"slot": "xyz", "facet": "sem", "filler": "value1"}
        ])

        mock_concept("child", parents=["parent"])

        data = {
            "slot": "xyz",
            "facet": "sem",
            "filler": "value1"
        }

        response = self.app.post("/ontology/edit/block/child",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        results = OntologyAPI().get("child", metadata=True)
        self.assertEqual([{
            "filler": "value1",
            "defined_in": "parent",
            "blocked": True
        }], results[0]["child"]["xyz"]["sem"])


class APIEditUnblockServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_unblock(self):
        mock_concept("parent", localProperties=[
            {"slot": "xyz", "facet": "sem", "filler": "value1"}
        ])

        mock_concept("child", parents=["parent"], totallyRemovedProperties=[
            {"slot": "xyz", "facet": "sem", "filler": "value1"}
        ])

        data = {
            "slot": "xyz",
            "facet": "sem",
            "filler": "value1"
        }

        response = self.app.post("/ontology/edit/unblock/child",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        results = OntologyAPI().get("child", metadata=True)
        self.assertEqual([{
            "filler": "value1",
            "defined_in": "parent",
            "blocked": False
        }], results[0]["child"]["xyz"]["sem"])


class APIEditAddParentServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_add_parent(self):
        mock_concept("parent")
        mock_concept("child")

        data = {
            "parent": "parent"
        }

        response = self.app.post("/ontology/edit/add_parent/child",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        self.assertEqual(["parent"], OntologyAPI().ancestors("child", immediate=True))


class APIEditRemoveParentServiceTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        self.app = service.test_client()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_remove_parent(self):
        mock_concept("parent")
        mock_concept("child", parents=["parent"])

        data = {
            "parent": "parent"
        }

        response = self.app.post("/ontology/edit/remove_parent/child",
                                data=json.dumps(data),
                                content_type="application/json")
        self.assertEqual(200, response._status_code)
        self.assertEqual("OK", response.data.decode("utf-8"))

        self.assertEqual([], OntologyAPI().ancestors("child", immediate=True))