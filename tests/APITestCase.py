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

    def test_inherit_totally_removed_with_metadata(self):
        property1 = {"slot": "prop1", "facet": "sem", "filler": "value1"}
        property2 = {"slot": "prop2", "facet": "sem", "filler": "value2"}
        property3 = {"slot": "prop3", "facet": "sem", "filler": "value3"}

        concept = mock_concept("concept", parents=["parent"], localProperties=[property1], totallyRemovedProperties=[property2])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[property2], totallyRemovedProperties=[property3])
        grandparent = mock_concept("grandparent", parents=[], localProperties=[property3])

        properties = OntologyAPI()._inherit(concept, metadata=True)
        self.assertEqual(2, len(properties))

        # Prop1 is found as normal
        # Prop2 is found, but marked as blocked in metadata
        # Prop3 is not found at all; being blocked higher up means it doesn't show up at all

        self.assertTrue({
            "slot": "prop1",
            "facet": "sem",
            "filler": "value1",
            "metadata": {
                "defined_in": "concept"
            }
        } in properties)

        self.assertTrue({
            "slot": "prop2",
            "facet": "sem",
            "filler": "value2",
            "metadata": {
                "defined_in": "parent",
                "blocked": True
            }
        } in properties)

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

    def test_prune_list(self):
        property1 = {"slot": "test", "facet": "sem", "filler": "filler1"}
        property2 = {"slot": "test", "facet": "sem", "filler": "filler2"}
        property3 = {"slot": "test", "facet": "sem", "filler": "filler3"}
        property4 = {"slot": "test", "facet": "sem", "filler": "filler4"}

        self.assertEqual([property1, property2], OntologyAPI()._prune_list([property1, property2, property3], [property3]))
        self.assertEqual([property1, property2, property3], OntologyAPI()._prune_list([property1, property2, property3], [property4]))
        self.assertEqual([property1], OntologyAPI()._prune_list([property1, property2, property3], [property2, property3]))

        meta_property1 = {"slot": "test", "facet": "sem", "filler": "filler1", "metadata": {}}
        meta_property2 = {"slot": "test", "facet": "sem", "filler": "filler2", "metadata": {}}
        meta_property3 = {"slot": "test", "facet": "sem", "filler": "filler3", "metadata": {}}

        self.assertEqual([meta_property2, meta_property3], OntologyAPI()._prune_list([meta_property1, meta_property2, meta_property3], [property1]))


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

    def test_get_local(self):
        grandparent = mock_concept("grandparent", localProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}])
        child = mock_concept("child", parents=["parent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value3"}])

        results = OntologyAPI().get("child", local=True, metadata=True)
        self.assertEqual(1, len(results[0]["child"]["test"]["sem"]))
        self.assertIn({
            "filler": "value3",
            "defined_in": "child",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])

    def test_get_metadata_specifies_original_definition_per_filler(self):
        grandparent = mock_concept("grandparent", localProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}])
        child = mock_concept("child", parents=["parent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value3"}])

        results = OntologyAPI().get("child", metadata=True)
        self.assertEqual(3, len(results[0]["child"]["test"]["sem"]))
        self.assertIn({
            "filler": "value1",
            "defined_in": "grandparent",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])
        self.assertIn({
            "filler": "value2",
            "defined_in": "parent",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])
        self.assertIn({
            "filler": "value3",
            "defined_in": "child",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])

    def test_get_metadata_marks_blocked_fillers(self):
        grandparent = mock_concept("grandparent", localProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}])
        parent = mock_concept("parent", parents=["grandparent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}], totallyRemovedProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}])
        child = mock_concept("child", parents=["parent"], localProperties=[{"slot": "test", "facet": "sem", "filler": "value3"}])

        results = OntologyAPI().get("grandparent", metadata=True)
        self.assertEqual(1, len(results[0]["grandparent"]["test"]["sem"]))
        self.assertIn({
            "filler": "value1",
            "defined_in": "grandparent",
            "blocked": False
        }, results[0]["grandparent"]["test"]["sem"])

        results = OntologyAPI().get("parent", metadata=True)
        self.assertEqual(2, len(results[0]["parent"]["test"]["sem"]))
        self.assertIn({
            "filler": "value2",
            "defined_in": "parent",
            "blocked": False
        }, results[0]["parent"]["test"]["sem"])
        self.assertIn({
            "filler": "value1",
            "defined_in": "grandparent",
            "blocked": True
        }, results[0]["parent"]["test"]["sem"])

        results = OntologyAPI().get("child", metadata=True)
        self.assertEqual(2, len(results[0]["child"]["test"]["sem"]))
        self.assertIn({
            "filler": "value3",
            "defined_in": "child",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])
        self.assertIn({
            "filler": "value2",
            "defined_in": "parent",
            "blocked": False
        }, results[0]["child"]["test"]["sem"])

    def test_get_metadata_augments_slots_with_type(self):
        mock_concept("relation")
        mock_concept("rel1", parents=["relation"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel1-of"}])
        mock_concept("rel2", parents=["rel1"], localProperties=[{"slot": "inverse", "facet": "sem", "filler": "rel2-of"}])

        concept = mock_concept("concept", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
            {"slot": "rel1", "facet": "sem", "filler": "value2"},
            {"slot": "rel2", "facet": "sem", "filler": "value3"},
            {"slot": "rel1-of", "facet": "sem", "filler": "value4"},
            {"slot": "rel2-of", "facet": "sem", "filler": "value4"},
        ])

        results = OntologyAPI().get("concept", metadata=True)
        self.assertFalse(results[0]["concept"]["test"]["is_relation"])
        self.assertTrue(results[0]["concept"]["rel1"]["is_relation"])
        self.assertTrue(results[0]["concept"]["rel2"]["is_relation"])
        self.assertTrue(results[0]["concept"]["rel1-of"]["is_relation"])
        self.assertTrue(results[0]["concept"]["rel2-of"]["is_relation"])


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


class APIReportTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_report_with_usage(self):
        concept = mock_concept("concept")
        child1 = mock_concept("child1", parents=["concept"])
        child2 = mock_concept("child2", parents=["concept"])
        other1 = mock_concept("other1", localProperties=[{
            "slot": "slot1",
            "facet": "sem",
            "filler": "concept"
        }, {
            "slot": "slot2",
            "facet": "sem",
            "filler": "concept"
        }])
        other2 = mock_concept("other2", localProperties=[{
            "slot": "slot3",
            "facet": "sem",
            "filler": "concept"
        }])
        other3 = mock_concept("other3", localProperties=[{
            "slot": "slot4",
            "facet": "sem",
            "filler": "other1"
        }])

        report = OntologyAPI().report("concept", include_usage=True)

        self.assertEqual({"child1", "child2"}, set(report["usage"]["subclasses"]))
        self.assertEqual(3, len(report["usage"]["inverses"]))
        self.assertIn({
            "concept": "other1",
            "slot": "slot1",
            "facet": "sem",
            "filler": "concept"
        }, report["usage"]["inverses"])
        self.assertIn({
            "concept": "other1",
            "slot": "slot2",
            "facet": "sem",
            "filler": "concept"
        }, report["usage"]["inverses"])
        self.assertIn({
            "concept": "other2",
            "slot": "slot3",
            "facet": "sem",
            "filler": "concept"
        }, report["usage"]["inverses"])

    def test_report_with_inherited_usage(self):
        concept = mock_concept("concept")
        child = mock_concept("child", parents=["concept"])
        user = mock_concept("user", localProperties=[{
            "slot": "slot1",
            "facet": "sem",
            "filler": "concept"
        }])

        report = OntologyAPI().report("child", include_usage=True, usage_with_inheritance=True)

        self.assertEqual(1, len(report["usage"]["inverses"]))
        self.assertIn({
            "concept": "user",
            "slot": "slot1",
            "facet": "sem",
            "filler": "concept"
        }, report["usage"]["inverses"])


class APIUpdateDefinitionTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_update_definition(self):
        concept1 = mock_concept("concept1", "definition 1")
        concept1 = mock_concept("concept2", "definition 1")

        self.assertEqual("definition 1", OntologyAPI().get("concept1", metadata=True)[0]["concept1"]["_metadata"]["definition"])
        self.assertEqual("definition 1", OntologyAPI().get("concept2", metadata=True)[0]["concept2"]["_metadata"]["definition"])

        OntologyAPI().update_definition("concept1", "definition 2")

        self.assertEqual("definition 2", OntologyAPI().get("concept1", metadata=True)[0]["concept1"]["_metadata"]["definition"])
        self.assertEqual("definition 1", OntologyAPI().get("concept2", metadata=True)[0]["concept2"]["_metadata"]["definition"])


class APIInsertPropertyTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_insert_property(self):
        concept = mock_concept("concept", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
            {"slot": "test", "facet": "sem", "filler": "value2"},
        ])

        OntologyAPI().insert_property("concept", "test", "sem", "value3")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))

        OntologyAPI().insert_property("concept", "test", "value", "value4")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))
        self.assertEqual({"value4"}, set(result["test"]["value"]))

        OntologyAPI().insert_property("concept", "other", "value", "value5")

        result = OntologyAPI().get("concept")[0]["concept"]
        self.assertEqual({"value1", "value2", "value3"}, set(result["test"]["sem"]))
        self.assertEqual({"value4"}, set(result["test"]["value"]))
        self.assertEqual({"value5"}, set(result["other"]["value"]))

        result = OntologyAPI().get("concept", metadata=True)[0]["concept"]
        self.assertEqual("concept", result["other"]["value"][0]["defined_in"])


class APIRemovePropertyTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_remove_property(self):
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

        OntologyAPI().remove_property("concept1", "test", "sem", "value1")

        result = OntologyAPI().get("concept1")[0]["concept1"]
        self.assertEqual({"value2"}, set(result["test"]["sem"]))
        self.assertEqual({"value1"}, set(result["test"]["value"]))
        self.assertEqual({"value1"}, set(result["other"]["sem"]))

        result = OntologyAPI().get("concept2")[0]["concept2"]
        self.assertEqual({"value1", "value2"}, set(result["test"]["sem"]))
        self.assertEqual({"value1"}, set(result["test"]["value"]))
        self.assertEqual({"value1"}, set(result["other"]["sem"]))


class APIBlockPropertyTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_block_property(self):
        parent = mock_concept("parent", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
        ])

        child = mock_concept("child", parents=["parent"], localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value2"},
        ])

        OntologyAPI().block_property("child", "test", "sem", "value1")

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


class APIUnblockPropertyTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_unblock_property(self):
        parent = mock_concept("parent", localProperties=[
            {"slot": "test", "facet": "sem", "filler": "value1"},
        ])

        child = mock_concept("child",
                             parents=["parent"],
                             localProperties=[{"slot": "test", "facet": "sem", "filler": "value2"}],
                             totallyRemovedProperties=[{"slot": "test", "facet": "sem", "filler": "value1"}]
                             )

        OntologyAPI().unblock_property("child", "test", "sem", "value1")

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


class APIAddParentTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_add_parent(self):
        parent1 = mock_concept("parent1")
        parent2 = mock_concept("parent2")
        child = mock_concept("child")

        self.assertEqual([], OntologyAPI().ancestors("child", immediate=True))

        OntologyAPI().add_parent("child", "parent1")
        self.assertEqual(["parent1"], OntologyAPI().ancestors("child", immediate=True))

        OntologyAPI().add_parent("child", "parent2")
        self.assertEqual({"parent1", "parent2"}, set(OntologyAPI().ancestors("child", immediate=True)))

    def test_cannot_add_self_as_parent(self):
        concept = mock_concept("concept")

        with self.assertRaises(Exception):
            OntologyAPI().add_parent("concept", "concept")


class APIRemoveParentTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_remove_parent(self):
        parent1 = mock_concept("parent1")
        parent2 = mock_concept("parent2")
        child = mock_concept("child", parents=["parent1", "parent2"])

        self.assertEqual({"parent1", "parent2"}, set(OntologyAPI().ancestors("child", immediate=True)))

        OntologyAPI().remove_parent("child", "parent1")
        self.assertEqual(["parent2"], OntologyAPI().ancestors("child", immediate=True))

        OntologyAPI().remove_parent("child", "parent2")
        self.assertEqual([], OntologyAPI().ancestors("child", immediate=True))


class APIAddConceptTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_add_concept(self):
        parent = mock_concept("parent")

        self.assertEqual([], OntologyAPI().get("concept"))

        OntologyAPI().add_concept("concept", "parent", "a definition")

        results = OntologyAPI().get("concept", metadata=True)
        self.assertEqual(1, len(results))
        self.assertEqual("a definition", results[0]["concept"]["_metadata"]["definition"])

        self.assertEqual(["parent"], OntologyAPI().ancestors("concept"))

    def test_cannot_declare_self_as_parent(self):
        parent = mock_concept("parent")

        with self.assertRaises(Exception):
            OntologyAPI().add_concept("parent", "parent", "a definition")


class APIRemoveConceptTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_remove_concept(self):
        concept = mock_concept("concept")

        self.assertEqual(1, len(OntologyAPI().get("concept")))

        OntologyAPI().remove_concept("concept")

        self.assertEqual(0, len(OntologyAPI().get("concept")))

    def test_remove_concept_with_usages(self):
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

        OntologyAPI().remove_concept("concept", include_usages=True)

        self.assertEqual(0, len(OntologyAPI().get("concept")))
        self.assertEqual([], OntologyAPI().ancestors("child1"))
        self.assertEqual(["other"], OntologyAPI().ancestors("child2"))

        self.assertNotIn("slot1", OntologyAPI().get("other1")[0]["other1"])
        self.assertNotIn("slot2", OntologyAPI().get("other1")[0]["other1"])
        self.assertIn("other1", OntologyAPI().get("other1")[0]["other1"]["slot3"]["sem"])
        self.assertIn("other1", OntologyAPI().get("other2")[0]["other2"]["slot1"]["sem"])


class APISearchTestCase(unittest.TestCase):

    def setUp(self):
        client = ont.management.getclient()

        ont.management.DATABASE = "unittest"
        os.environ[ont.management.ONTOLOGY_ACTIVE] = "unittest"

    def tearDown(self):
        client = ont.management.getclient()
        client.drop_database("unittest")

    def test_search_name_like(self):
        c1 = mock_concept("concept1")
        c2 = mock_concept("concept2")
        c3 = mock_concept("concept3")

        self.assertEqual(["concept1"], OntologyAPI().search(name_like="concept1"))
        self.assertEqual(["concept1", "concept2", "concept3"], OntologyAPI().search(name_like="concept"))
        self.assertEqual(["concept1"], OntologyAPI().search(name_like="ept1"))
        self.assertEqual(["concept1", "concept2", "concept3"], OntologyAPI().search(name_like="once"))
        self.assertEqual([], OntologyAPI().search(name_like="xyz"))

        # No name specified returns an empty list
        self.assertEqual([], OntologyAPI().search())

        # Name must be at least 3 characters to search (treats as None otherwise)
        self.assertEqual([], OntologyAPI().search(name_like="co"))