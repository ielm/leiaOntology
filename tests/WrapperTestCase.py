from ont.api import OntologyAPI
from ont.ontology import Ontology
from ont.service import app
from tests.TestUtils import mock_concept

import ont.management
import os
import unittest


class OntologyWrapperTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

        os.environ["ONTOLOGY_HOST"] = "0.0.0.0"
        os.environ["ONTOLOGY_PORT"] = "8080"

        from multiprocessing import Process
        self.server = Process(target=app.run, kwargs={"host": "0.0.0.0", "port": 8080})
        self.server.start()

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

        self.server.terminate()
        self.server.join()

    def test_get(self):
        concept = mock_concept("concept")

        response = Ontology().get(["concept"])
        self.assertEqual(response, [OntologyAPI().format(concept)])

        response = Ontology().get(["concept"], local=True)
        self.assertEqual(response, [OntologyAPI().format(concept, local=True)])

    def test_search(self):
        c = mock_concept("concept")

        response = Ontology().search(name_like="concept")
        self.assertEqual(response, OntologyAPI().search(name_like="concept"))

    def test_ancestors(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = Ontology().ancestors(["concept"])
        self.assertEqual(2, len(response))
        self.assertTrue("parent" in response)
        self.assertTrue("grandparent" in response)

        response = Ontology().ancestors(["concept"], immediate=True)
        self.assertEqual(response, ["parent"])

        response = Ontology().ancestors(["parent"], details=True)
        self.assertEqual(response, [OntologyAPI().format(grandparent)])

        response = Ontology().ancestors(["concept"], paths=True)
        self.assertEqual(response, [["parent", "grandparent"]])

    def test_descendants(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        response = Ontology().descendants(["grandparent"])
        self.assertEqual(2, len(response))
        self.assertTrue("parent" in response)
        self.assertTrue("concept" in response)

        response = Ontology().descendants(["grandparent"], immediate=True)
        self.assertEqual(response, ["parent"])

        response = Ontology().descendants(["parent"], details=True)
        self.assertEqual(response, [OntologyAPI().format(concept)])

        response = Ontology().descendants(["grandparent"], paths=True)
        self.assertTrue(["parent", "concept"] in response)
        self.assertTrue(["parent"] in response)

    def test_is_parent(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        self.assertTrue(Ontology().is_parent("concept", "parent"))
        self.assertTrue(Ontology().is_parent("concept", "grandparent"))
        self.assertTrue(Ontology().is_parent("parent", "grandparent"))
        self.assertFalse(Ontology().is_parent("parent", "concept"))

    def test_exists(self):
        concept = mock_concept("concept")

        self.assertTrue(Ontology().exists("concept"))
        self.assertFalse(Ontology().exists("other"))

    def test_get_subtree(self):
        concept = mock_concept("concept", parents=["object"])
        object = mock_concept("object")

        self.assertEqual("object", Ontology().get_subtree("concept"))

        outside = mock_concept("outside", parents=["other"])
        other = mock_concept("other")
        with self.assertRaises(Exception):
            Ontology().get_subtree("outside")

    def test_has_property(self):
        property = {"slot": "prop", "facet": "sem", "filler": "value"}
        concept = mock_concept("concept", localProperties=[property])

        self.assertTrue(Ontology().has_property("concept", "prop"))
        self.assertFalse(Ontology().has_property("concept", "other"))

    def test_get_constraints(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "other", "filler": "value2"}
        property3 = {"slot": "prop1", "facet": "sem", "filler": "value3"}

        concept1 = mock_concept("concept1", localProperties=[property1, property2, property3])
        concept2 = mock_concept("concept2", localProperties=[property1, property2])
        concept3 = mock_concept("concept3", localProperties=[])

        self.assertEqual(Ontology().get_constraints("concept1", "prop1"), ["value1", "value3"])
        self.assertEqual(Ontology().get_constraints("concept2", "prop1"), ["value1"])
        self.assertEqual(Ontology().get_constraints("concept3", "prop1"), [])

        self.assertEqual(Ontology().get_constraints("concept1", "prop2"), [])
        self.assertEqual(Ontology().get_constraints("concept2", "prop2"), [])
        self.assertEqual(Ontology().get_constraints("concept3", "prop2"), [])

    def test_get_inverses(self):
        property1 = {"slot": "inverse", "facet": "sem", "filler": "inverse-name1"}
        property2 = {"slot": "inverse", "facet": "sem", "filler": "inverse-name2"}

        concept1 = mock_concept("concept1", localProperties=[property1])
        concept2 = mock_concept("concept2", localProperties=[property1, property2])
        concept3 = mock_concept("concept3", localProperties=[])

        self.assertEqual(Ontology().get_inverses("concept1"), {"sem": ["inverse-name1"]})
        self.assertEqual(Ontology().get_inverses("concept2"), {"sem": ["inverse-name1", "inverse-name2"]})
        self.assertEqual(Ontology().get_inverses("concept3"), {})

    def test_all_inverses(self):
        mock_concept("rel1", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4")

        inverses = Ontology().all_inverses()
        self.assertEqual(3, len(inverses))
        self.assertTrue("rel1-of" in inverses)
        self.assertTrue("rel2-of" in inverses)
        self.assertTrue("rel3-of" in inverses)
        self.assertTrue("rel4-of" not in inverses)

    def test_all_relations(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", parents=["rel2"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4", parents=["relation"])

        relations = Ontology().all_relations()
        self.assertEqual(5, len(relations))
        self.assertTrue("relation" in relations)
        self.assertTrue("rel1" in relations)
        self.assertTrue("rel2" in relations)
        self.assertTrue("rel3" in relations)
        self.assertTrue("rel4" in relations)
        self.assertTrue("rel1-of" not in relations)
        self.assertTrue("rel2-of" not in relations)
        self.assertTrue("rel3-of" not in relations)

        relations = Ontology().all_relations(inverses=True)
        self.assertEqual(8, len(relations))
        self.assertTrue("relation" in relations)
        self.assertTrue("rel1" in relations)
        self.assertTrue("rel2" in relations)
        self.assertTrue("rel3" in relations)
        self.assertTrue("rel4" in relations)
        self.assertTrue("rel1-of" in relations)
        self.assertTrue("rel2-of" in relations)
        self.assertTrue("rel3-of" in relations)

    def test_dict_behavior(self):
        concept = mock_concept("concept")

        response = Ontology()["concept"]
        self.assertEqual(response, OntologyAPI().format(concept)[concept["name"]])

        self.assertTrue("concept" in Ontology())
        self.assertTrue("xyz" not in Ontology())

    def test_edit_update_definition(self):
        concept1 = mock_concept("concept1", "definition 1")
        concept1 = mock_concept("concept2", "definition 1")

        self.assertEqual("definition 1", OntologyAPI().get("concept1", metadata=True)[0]["concept1"]["_metadata"]["definition"])
        self.assertEqual("definition 1", OntologyAPI().get("concept2", metadata=True)[0]["concept2"]["_metadata"]["definition"])

        Ontology().update_definition("concept1", "definition 2")

        self.assertEqual("definition 2", OntologyAPI().get("concept1", metadata=True)[0]["concept1"]["_metadata"]["definition"])
        self.assertEqual("definition 1", OntologyAPI().get("concept2", metadata=True)[0]["concept2"]["_metadata"]["definition"])

    def test_edit_insert_property(self):
        concept = mock_concept("concept", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
            {"slot": "test", "facet": "sem", "filler": "value2"},
        ])

        Ontology().insert_property("concept", "test", "sem", "value3")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))

        Ontology().insert_property("concept", "test", "value", "value4")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))
        self.assertEqual({"value4"}, set(result["test"]["value"]))

        Ontology().insert_property("concept", "other", "value", "value5")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))
        self.assertEqual({"value4"}, set(result["test"]["value"]))
        self.assertEqual({"value5"}, set(result["other"]["value"]))

        result = OntologyAPI().get("concept", metadata=True)[0]["concept"]
        self.assertEqual("concept", result["other"]["value"][0]["defined_in"])

    def test_edit_remove_property(self):
        concept1 = mock_concept("concept1", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
            {"slot": "test", "facet": "sem", "filler": "value2"},
            {"slot": "test", "facet": "value", "filler": "value1"},
            {"slot": "other", "facet": "sem", "filler": "value1"},
        ])

        concept2 = mock_concept("concept2", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
            {"slot": "test", "facet": "sem", "filler": "value2"},
            {"slot": "test", "facet": "value", "filler": "value1"},
            {"slot": "other", "facet": "sem", "filler": "value1"},
        ])

        Ontology().remove_property("concept1", "test", "sem", "value1")

        result = OntologyAPI().get("concept1")[0]["concept1"]
        self.assertEqual({"value2"}, set(result["test"]["sem"]))
        self.assertEqual({"value1"}, set(result["test"]["value"]))
        self.assertEqual({"value1"}, set(result["other"]["sem"]))

        result = OntologyAPI().get("concept2")[0]["concept2"]
        self.assertEqual({"value1", "value2"}, set(result["test"]["sem"]))
        self.assertEqual({"value1"}, set(result["test"]["value"]))
        self.assertEqual({"value1"}, set(result["other"]["sem"]))

    def test_edit_block_property(self):
        parent = mock_concept("parent", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
        ])

        child = mock_concept("child", parents=["parent"], localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value2"},
        ])

        Ontology().block_property("child", "test", "sem", "value1")

        result = OntologyAPI().get("parent")[0]["parent"]
        self.assertEqual({"value1"}, set(result["test"]["sem"]))

        result = OntologyAPI().get("child")[0]["child"]
        self.assertEqual({"value2"}, set(result["test"]["sem"]))

        result = OntologyAPI().get("child", metadata=True)[0]["child"]
        self.assertEqual(2, len(result["test"]["sem"]))
        self.assertIn({
            "filler": "value1",
            "defined_in": "parent",
            "blocked": True
        }, result["test"]["sem"])
        self.assertIn({
            "filler": "value2",
            "defined_in": "child",
            "blocked": False
        }, result["test"]["sem"])

    def test_edit_unblock_property(self):
        parent = mock_concept("parent", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
        ])

        child = mock_concept("child",
                             parents=["parent"],
                             localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}],
                             totallyRemovedProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}]
                             )

        Ontology().unblock_property("child", "test", "sem", "value1")

        result = OntologyAPI().get("parent")[0]["parent"]
        self.assertEqual({"value1"}, set(result["test"]["sem"]))

        result = OntologyAPI().get("child")[0]["child"]
        self.assertEqual({"value1", "value2"}, set(result["test"]["sem"]))

        result = OntologyAPI().get("child", metadata=True)[0]["child"]
        self.assertEqual(2, len(result["test"]["sem"]))
        self.assertIn({
            "filler": "value1",
            "defined_in": "parent",
            "blocked": False
        }, result["test"]["sem"])
        self.assertIn({
            "filler": "value2",
            "defined_in": "child",
            "blocked": False
        }, result["test"]["sem"])

    def test_edit_add_parent(self):
        parent1 = mock_concept("parent1")
        parent2 = mock_concept("parent2")
        child = mock_concept("child")

        self.assertEqual([], OntologyAPI().ancestors("child", immediate=True))

        Ontology().add_parent("child", "parent1")
        self.assertEqual(["parent1"], OntologyAPI().ancestors("child", immediate=True))

        Ontology().add_parent("child", "parent2")
        self.assertEqual({"parent1", "parent2"}, set(OntologyAPI().ancestors("child", immediate=True)))

        with self.assertRaises(Exception):
            Ontology().add_parent("child", "child")

    def test_edit_remove_parent(self):
        parent1 = mock_concept("parent1")
        parent2 = mock_concept("parent2")
        child = mock_concept("child", parents=["parent1", "parent2"])

        self.assertEqual({"parent1", "parent2"}, set(OntologyAPI().ancestors("child", immediate=True)))

        Ontology().remove_parent("child", "parent1")
        self.assertEqual(["parent2"], OntologyAPI().ancestors("child", immediate=True))

        Ontology().remove_parent("child", "parent2")
        self.assertEqual([], OntologyAPI().ancestors("child", immediate=True))

    def test_edit_add_concept(self):
        parent = mock_concept("parent")

        self.assertEqual([], OntologyAPI().get("concept"))

        Ontology().add_concept("concept", "parent", "a definition")

        results = OntologyAPI().get("concept", metadata=True)
        self.assertEqual(1, len(results))
        self.assertEqual("a definition", results[0]["concept"]["_metadata"]["definition"])

        self.assertEqual(["parent"], OntologyAPI().ancestors("concept"))

        with self.assertRaises(Exception):
            Ontology().add_concept("x", "x", "a definition")

    def test_edit_remove_concept(self):
        concept = mock_concept("concept")

        self.assertEqual(1, len(OntologyAPI().get("concept")))

        Ontology().remove_concept("concept")

        self.assertEqual(0, len(OntologyAPI().get("concept")))

    def test_edit_remove_concept_with_usages(self):
        concept = mock_concept("concept")
        other = mock_concept("other")
        child1 = mock_concept("child1", parents=["concept"])
        child2 = mock_concept("child2", parents=["concept", "other"])
        other1 = mock_concept("other1", localProperties=[
            {"slot": "slot1", "facet": "sem", "filler": "concept"},
            {"slot": "slot2", "facet": "sem", "filler": "concept"},
            {"slot": "slot3", "facet": "sem", "filler": "other1"},
        ])
        other2 = mock_concept("other2", localProperties=[
            {"slot": "slot1", "facet": "sem", "filler": "other1"},
        ])

        Ontology().remove_concept("concept", include_usages=True)

        self.assertEqual(0, len(OntologyAPI().get("concept")))
        self.assertEqual([], OntologyAPI().ancestors("child1"))
        self.assertEqual(["other"], OntologyAPI().ancestors("child2"))

        self.assertNotIn("slot1", OntologyAPI().get("other1")[0]["other1"])
        self.assertNotIn("slot2", OntologyAPI().get("other1")[0]["other1"])
        self.assertIn("other1", OntologyAPI().get("other1")[0]["other1"]["slot3"]["sem"])
        self.assertIn("other1", OntologyAPI().get("other2")[0]["other2"]["slot1"]["sem"])