from ont.api import OntologyAPI
from tests.TestUtils import mock_concept

import ont.management
import os
import unittest


class APITestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_inherit(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1])
        parent = mock_concept("parent", localProperties=[property2])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 in properties)

    def test_inherit_deep(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}
        property3 = {"slot": "prop3", "facet": "sem", "filler": "value3"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[property2])
        grandparent = mock_concept("grandparent", localProperties=[property3])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 in properties)
        self.assertTrue(property3 in properties)

    def test_inherit_multiple(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}
        property3 = {"slot": "prop3", "facet": "sem", "filler": "value3"}
        property4 = {"slot": "prop4", "facet": "sem", "filler": "value4"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"], localProperties=[property2])
        grandparent1 = mock_concept("grandparent1", localProperties=[property3])
        grandparent2 = mock_concept("grandparent2", localProperties=[property4])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 in properties)
        self.assertTrue(property3 in properties)
        self.assertTrue(property4 in properties)

    def test_inherit_override(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1], overriddenFillers=[property2])
        parent = mock_concept("parent", localProperties=[property2])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 not in properties)

    def test_inherit_override_in_ancestor(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}
        property3 = {"slot": "prop3", "facet": "sem", "filler": "value3"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[property2], overriddenFillers=[property3])
        grandparent = mock_concept("grandparent", parents=[], localProperties=[property3])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 in properties)
        self.assertTrue(property3 not in properties)

    def test_inherit_totally_removed(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1], totallyRemovedProperties=[property2])
        parent = mock_concept("parent", localProperties=[property2])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 not in properties)

    def test_inherit_totally_removed_in_ancestor(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}
        property3 = {"slot": "prop3", "facet": "sem", "filler": "value3"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[property2], totallyRemovedProperties=[property3])
        grandparent = mock_concept("grandparent", parents=[], localProperties=[property3])

        properties = OntologyAPI()._inherit(concept)
        self.assertTrue(property1 in properties)
        self.assertTrue(property2 in properties)
        self.assertTrue(property3 not in properties)

    def test_format_subclasses(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        formatted = OntologyAPI().format(grandparent)
        self.assertTrue("parent" in formatted["grandparent"]["subclasses"]["value"])
        self.assertTrue("concept" not in formatted["grandparent"]["subclasses"]["value"])

    def test_format_metadata(self):
        concept = mock_concept("concept", definition="test definition")
        formatted = OntologyAPI().format(concept, metadata=True)
        self.assertEqual({
            "definition": "test definition"
        }, formatted["concept"]["_metadata"])


class APIGetTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_get(self):
        concept = mock_concept("concept")
        self.assertEqual([OntologyAPI().format(concept)], OntologyAPI().get("concept"))

    def test_get_multiple(self):
        concept1 = mock_concept("concept1")
        concept2 = mock_concept("concept2")

        results = OntologyAPI().get(["concept1", "concept2"])
        self.assertTrue(OntologyAPI().format(concept1) in results)
        self.assertTrue(OntologyAPI().format(concept2) in results)

    def test_get_metadata(self):
        concept = mock_concept("concept", definition="test definition")

        results = OntologyAPI().get("concept", metadata=True)
        self.assertEqual([OntologyAPI().format(concept, metadata=True)], results)

    def test_get_metadata_specifies_original_definition_per_filler(self):
        grandparent = mock_concept("grandparent", localProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}])
        child = mock_concept("child", parents=["parent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value3"}])

        results = OntologyAPI().get("child", metadata=True)
        self.assertEqual(3, len(results[0]["child"]["test"]["sem"]))
        self.assertIn({
            "filler": "value1",
            "defined_in": "grandparent"
        }, results[0]["child"]["test"]["sem"])
        self.assertIn({
            "filler": "value2",
            "defined_in": "parent"
        }, results[0]["child"]["test"]["sem"])
        self.assertIn({
            "filler": "value3",
            "defined_in": "child"
        }, results[0]["child"]["test"]["sem"])


class APIAncestorsTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_ancestors(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        results = OntologyAPI().ancestors("concept")

        self.assertEqual(3, len(results))
        self.assertTrue("parent" in results)
        self.assertTrue("grandparent1" in results)
        self.assertTrue("grandparent2" in results)

    def test_ancestors_immediate(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        results = OntologyAPI().ancestors("concept", immediate=True)

        self.assertEqual(1, len(results))
        self.assertTrue("parent" in results)

    def test_ancestors_details(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        results = OntologyAPI().ancestors("concept", details=True)

        self.assertEqual(3, len(results))
        self.assertTrue(OntologyAPI().format(parent) in results)
        self.assertTrue(OntologyAPI().format(grandparent1) in results)
        self.assertTrue(OntologyAPI().format(grandparent2) in results)

    def test_ancestors_paths(self):
        concept = mock_concept("concept", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent1", "grandparent2"])
        grandparent1 = mock_concept("grandparent1")
        grandparent2 = mock_concept("grandparent2")

        results = OntologyAPI().ancestors("concept", paths=True)

        self.assertEqual(2, len(results))
        self.assertTrue(["parent", "grandparent1"] in results)
        self.assertTrue(["parent", "grandparent2"] in results)

        results = OntologyAPI().ancestors("parent", paths=True)

        self.assertEqual(2, len(results))
        self.assertTrue(["grandparent1"] in results)
        self.assertTrue(["grandparent2"] in results)

        results = OntologyAPI().ancestors("grandparent1", paths=True)

        self.assertEqual(0, len(results))


class APIDescendantsTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_descendants(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        results = OntologyAPI().descendants("grandparent")

        self.assertEqual(3, len(results))
        self.assertTrue("parent" in results)
        self.assertTrue("concept1" in results)
        self.assertTrue("concept2" in results)

    def test_descendants_immediate(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        results = OntologyAPI().descendants("grandparent", immediate=True)

        self.assertEqual(1, len(results))
        self.assertTrue("parent" in results)

    def test_descendants_details(self):
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        parent = mock_concept("parent", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        results = OntologyAPI().descendants("grandparent", details=True)

        self.assertEqual(3, len(results))
        self.assertTrue(OntologyAPI().format(parent) in results)
        self.assertTrue(OntologyAPI().format(concept1) in results)
        self.assertTrue(OntologyAPI().format(concept2) in results)

    def test_descendants_paths(self):
        concept1 = mock_concept("concept1", parents=["parent1"])
        concept2 = mock_concept("concept2", parents=["parent2"])
        parent1 = mock_concept("parent1", parents=["grandparent"])
        parent2 = mock_concept("parent2", parents=["grandparent"])
        grandparent = mock_concept("grandparent")

        results = OntologyAPI().descendants("grandparent", paths=True)

        self.assertEqual(4, len(results))
        self.assertTrue(["parent1"] in results)
        self.assertTrue(["parent2"] in results)
        self.assertTrue(["parent1", "concept1"] in results)
        self.assertTrue(["parent2", "concept2"] in results)

        results = OntologyAPI().descendants("parent1", paths=True)

        self.assertEqual(1, len(results))
        self.assertTrue(["concept1"] in results)

        results = OntologyAPI().descendants("concept1", paths=True)

        self.assertEqual(0, len(results))


class APIInversesTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_inverses(self):
        mock_concept("rel1", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4")

        results = OntologyAPI().inverses()

        self.assertEqual(3, len(results))
        self.assertTrue("rel1-of" in results)
        self.assertTrue("rel2-of" in results)
        self.assertTrue("rel3-of" in results)
        self.assertTrue("rel4-of" not in results)


class APIRelationsTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_relations(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", parents=["rel2"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4", parents=["relation"],)

        results = OntologyAPI().relations()

        self.assertEqual(5, len(results))
        self.assertTrue("relation" in results)
        self.assertTrue("rel1" in results)
        self.assertTrue("rel2" in results)
        self.assertTrue("rel3" in results)
        self.assertTrue("rel4" in results)
        self.assertTrue("rel1-of" not in results)
        self.assertTrue("rel2-of" not in results)
        self.assertTrue("rel3-of" not in results)

    def test_relations_include_inverses(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])
        mock_concept("rel3", parents=["rel2"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel3-of"}])
        mock_concept("rel4", parents=["relation"])

        results = OntologyAPI().relations(inverses=True)

        self.assertEqual(8, len(results))
        self.assertTrue("relation" in results)
        self.assertTrue("rel1" in results)
        self.assertTrue("rel2" in results)
        self.assertTrue("rel3" in results)
        self.assertTrue("rel4" in results)
        self.assertTrue("rel1-of" in results)
        self.assertTrue("rel2-of" in results)
        self.assertTrue("rel3-of" in results)


class APISiblingsTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_siblings(self):
        parent = mock_concept("parent")
        concept1 = mock_concept("concept1", parents=["parent"])
        concept2 = mock_concept("concept2", parents=["parent"])
        concept3 = mock_concept("concept3", parents=["parent"])

        results = OntologyAPI().siblings("concept1")

        self.assertEqual(2, len(results))
        self.assertTrue("concept2" in results)
        self.assertTrue("concept3" in results)

        results = OntologyAPI().siblings("concept2")

        self.assertEqual(2, len(results))
        self.assertTrue("concept1" in results)
        self.assertTrue("concept3" in results)

        results = OntologyAPI().siblings("concept3")

        self.assertEqual(2, len(results))
        self.assertTrue("concept1" in results)
        self.assertTrue("concept2" in results)

        results = OntologyAPI().siblings("parent")

        self.assertEqual(0, len(results))

