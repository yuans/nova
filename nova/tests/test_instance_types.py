# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 Ken Pepple
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Unit Tests for instance types code
"""
import time

from nova.compute import flavors
from nova import context
from nova import db
from nova.db.sqlalchemy import models
from nova import exception
from nova.openstack.common.db.sqlalchemy import session as sql_session
from nova import test


class InstanceTypeTestCase(test.TestCase):
    """Test cases for instance type code."""
    def _generate_name(self):
        """return a name not in the DB."""
        nonexistent_flavor = str(int(time.time()))
        all_flavors = flavors.get_all_types()
        while nonexistent_flavor in all_flavors:
            nonexistent_flavor += "z"
        else:
            return nonexistent_flavor

    def _generate_flavorid(self):
        """return a flavorid not in the DB."""
        nonexistent_flavor = 2700
        flavor_ids = [value["id"] for key, value in
                      flavors.get_all_types().iteritems()]
        while nonexistent_flavor in flavor_ids:
            nonexistent_flavor += 1
        else:
            return nonexistent_flavor

    def _existing_flavor(self):
        """return first instance type name."""
        return flavors.get_all_types().keys()[0]

    def test_add_instance_type_access(self):
        user_id = 'fake'
        project_id = 'fake'
        ctxt = context.RequestContext(user_id, project_id, is_admin=True)
        flavor_id = 'flavor1'
        type_ref = flavors.create('some flavor', 256, 1, 120, 100,
                                          flavorid=flavor_id)
        access_ref = flavors.add_instance_type_access(flavor_id,
                                                             project_id,
                                                             ctxt=ctxt)
        self.assertEqual(access_ref["project_id"], project_id)
        self.assertEqual(access_ref["instance_type_id"], type_ref["id"])

    def test_add_instance_type_access_already_exists(self):
        user_id = 'fake'
        project_id = 'fake'
        ctxt = context.RequestContext(user_id, project_id, is_admin=True)
        flavor_id = 'flavor1'
        type_ref = flavors.create('some flavor', 256, 1, 120, 100,
                                          flavorid=flavor_id)
        access_ref = flavors.add_instance_type_access(flavor_id,
                                                             project_id,
                                                             ctxt=ctxt)
        self.assertRaises(exception.FlavorAccessExists,
                          flavors.add_instance_type_access,
                          flavor_id, project_id, ctxt)

    def test_add_instance_type_access_invalid_flavor(self):
        user_id = 'fake'
        project_id = 'fake'
        ctxt = context.RequestContext(user_id, project_id, is_admin=True)
        flavor_id = 'no_such_flavor'
        self.assertRaises(exception.FlavorNotFound,
                          flavors.add_instance_type_access,
                          flavor_id, project_id, ctxt)

    def test_remove_instance_type_access(self):
        user_id = 'fake'
        project_id = 'fake'
        ctxt = context.RequestContext(user_id, project_id, is_admin=True)
        flavor_id = 'flavor1'
        type_ref = flavors.create('some flavor', 256, 1, 120, 100,
                                          flavorid=flavor_id)
        access_ref = flavors.add_instance_type_access(flavor_id, project_id,
                                                      ctxt)
        flavors.remove_instance_type_access(flavor_id, project_id, ctxt)

        projects = flavors.get_instance_type_access_by_flavor_id(flavor_id,
                                                                 ctxt)
        self.assertEqual([], projects)

    def test_remove_instance_type_access_doesnt_exists(self):
        user_id = 'fake'
        project_id = 'fake'
        ctxt = context.RequestContext(user_id, project_id, is_admin=True)
        flavor_id = 'flavor1'
        type_ref = flavors.create('some flavor', 256, 1, 120, 100,
                                          flavorid=flavor_id)
        self.assertRaises(exception.FlavorAccessNotFound,
                          flavors.remove_instance_type_access,
                          flavor_id, project_id, ctxt=ctxt)

    def test_get_all_instance_types(self):
        # Ensures that all instance types can be retrieved.
        session = sql_session.get_session()
        total_instance_types = session.query(models.InstanceTypes).count()
        inst_types = flavors.get_all_types()
        self.assertEqual(total_instance_types, len(inst_types))

    def test_non_existent_inst_type_shouldnt_delete(self):
        # Ensures that instance type creation fails with invalid args.
        self.assertRaises(exception.InstanceTypeNotFoundByName,
                          flavors.destroy,
                          'unknown_flavor')

    def test_will_not_destroy_with_no_name(self):
        # Ensure destroy said path of no name raises error.
        self.assertRaises(exception.InstanceTypeNotFoundByName,
                          flavors.destroy, None)

    def test_will_not_get_bad_default_instance_type(self):
        # ensures error raised on bad default instance type.
        self.flags(default_instance_type='unknown_flavor')
        self.assertRaises(exception.InstanceTypeNotFound,
                          flavors.get_default_instance_type)

    def test_will_get_instance_type_by_id(self):
        default_instance_type = flavors.get_default_instance_type()
        instance_type_id = default_instance_type['id']
        fetched = flavors.get_instance_type(instance_type_id)
        self.assertEqual(default_instance_type, fetched)

    def test_will_not_get_instance_type_by_unknown_id(self):
        # Ensure get by name returns default flavor with no name.
        self.assertRaises(exception.InstanceTypeNotFound,
                         flavors.get_instance_type, 10000)

    def test_will_not_get_instance_type_with_bad_id(self):
        # Ensure get by name returns default flavor with bad name.
        self.assertRaises(exception.InstanceTypeNotFound,
                          flavors.get_instance_type, 'asdf')

    def test_instance_type_get_by_None_name_returns_default(self):
        # Ensure get by name returns default flavor with no name.
        default = flavors.get_default_instance_type()
        actual = flavors.get_instance_type_by_name(None)
        self.assertEqual(default, actual)

    def test_will_not_get_instance_type_with_bad_name(self):
        # Ensure get by name returns default flavor with bad name.
        self.assertRaises(exception.InstanceTypeNotFound,
                          flavors.get_instance_type_by_name, 10000)

    def test_will_not_get_instance_by_unknown_flavor_id(self):
        # Ensure get by flavor raises error with wrong flavorid.
        self.assertRaises(exception.FlavorNotFound,
                          flavors.get_instance_type_by_flavor_id,
                          'unknown_flavor')

    def test_will_get_instance_by_flavor_id(self):
        default_instance_type = flavors.get_default_instance_type()
        flavorid = default_instance_type['flavorid']
        fetched = flavors.get_instance_type_by_flavor_id(flavorid)
        self.assertEqual(default_instance_type, fetched)

    def test_can_read_deleted_types_using_flavor_id(self):
        # Ensure deleted instance types can be read when querying flavor_id.
        inst_type_name = "test"
        inst_type_flavor_id = "test1"

        inst_type = flavors.create(inst_type_name, 256, 1, 120, 100,
                inst_type_flavor_id)
        self.assertEqual(inst_type_name, inst_type["name"])

        # NOTE(jk0): The deleted flavor will show up here because the context
        # in get_instance_type_by_flavor_id() is set to use read_deleted by
        # default.
        flavors.destroy(inst_type["name"])
        deleted_inst_type = flavors.get_instance_type_by_flavor_id(
                inst_type_flavor_id)
        self.assertEqual(inst_type_name, deleted_inst_type["name"])

    def test_read_deleted_false_converting_flavorid(self):
        """
        Ensure deleted instance types are not returned when not needed (for
        example when creating a server and attempting to translate from
        flavorid to instance_type_id.
        """
        flavors.create("instance_type1", 256, 1, 120, 100, "test1")
        flavors.destroy("instance_type1")
        flavors.create("instance_type1_redo", 256, 1, 120, 100, "test1")

        instance_type = flavors.get_instance_type_by_flavor_id(
                "test1", read_deleted="no")
        self.assertEqual("instance_type1_redo", instance_type["name"])


class InstanceTypeToolsTest(test.TestCase):
    def _dict_to_metadata(self, data):
        return [{'key': key, 'value': value} for key, value in data.items()]

    def _test_extract_instance_type(self, prefix):
        instance_type = flavors.get_default_instance_type()

        metadata = {}
        flavors.save_instance_type_info(metadata, instance_type,
                                               prefix)
        instance = {'system_metadata': self._dict_to_metadata(metadata)}
        _instance_type = flavors.extract_instance_type(instance, prefix)

        props = flavors.system_metadata_instance_type_props.keys()
        for key in instance_type.keys():
            if key not in props:
                del instance_type[key]

        self.assertEqual(instance_type, _instance_type)

    def test_extract_instance_type(self):
        self._test_extract_instance_type('')

    def test_extract_instance_type_prefix(self):
        self._test_extract_instance_type('foo_')

    def test_save_instance_type_info(self):
        instance_type = flavors.get_default_instance_type()

        example = {}
        example_prefix = {}

        for key in flavors.system_metadata_instance_type_props.keys():
            example['instance_type_%s' % key] = instance_type[key]
            example_prefix['fooinstance_type_%s' % key] = instance_type[key]

        metadata = {}
        flavors.save_instance_type_info(metadata, instance_type)
        self.assertEqual(example, metadata)

        metadata = {}
        flavors.save_instance_type_info(metadata, instance_type, 'foo')
        self.assertEqual(example_prefix, metadata)

    def test_delete_instance_type_info(self):
        instance_type = flavors.get_default_instance_type()
        metadata = {}
        flavors.save_instance_type_info(metadata, instance_type)
        flavors.save_instance_type_info(metadata, instance_type, '_')
        flavors.delete_instance_type_info(metadata, '', '_')
        self.assertEqual(metadata, {})


class InstanceTypeFilteringTest(test.TestCase):
    """Test cases for the filter option available for instance_type_get_all."""
    def setUp(self):
        super(InstanceTypeFilteringTest, self).setUp()
        self.context = context.get_admin_context()

    def assertFilterResults(self, filters, expected):
        inst_types = db.instance_type_get_all(
                self.context, filters=filters)
        inst_names = [i['name'] for i in inst_types]
        self.assertEqual(inst_names, expected)

    def test_no_filters(self):
        filters = None
        expected = ['m1.large', 'm1.medium', 'm1.small', 'm1.tiny',
                    'm1.xlarge']
        self.assertFilterResults(filters, expected)

    def test_min_memory_mb_filter(self):
        # Exclude tiny instance which is 512 MB.
        filters = dict(min_memory_mb=513)
        expected = ['m1.large', 'm1.medium', 'm1.small', 'm1.xlarge']
        self.assertFilterResults(filters, expected)

    def test_min_root_gb_filter(self):
        # Exclude everything but large and xlarge which have >= 80 GB.
        filters = dict(min_root_gb=80)
        expected = ['m1.large', 'm1.xlarge']
        self.assertFilterResults(filters, expected)

    def test_min_memory_mb_AND_root_gb_filter(self):
        # Exclude everything but large and xlarge which have >= 80 GB.
        filters = dict(min_memory_mb=16384, min_root_gb=80)
        expected = ['m1.xlarge']
        self.assertFilterResults(filters, expected)


class CreateInstanceTypeTest(test.TestCase):

    def assertInvalidInput(self, *create_args, **create_kwargs):
        self.assertRaises(exception.InvalidInput, flavors.create,
                          *create_args, **create_kwargs)

    def test_name_with_special_characters(self):
        # Names can contain [a-zA-Z0-9_.- ]
        flavors.create('_foo.bar-123', 64, 1, 120)

        # Ensure instance types raises InvalidInput for invalid characters.
        self.assertInvalidInput('foobar#', 64, 1, 120)

    def test_name_length_checks(self):
        MAX_LEN = 255

        # Flavor name with 255 characters or less is valid.
        flavors.create('a' * MAX_LEN, 64, 1, 120)

        # Flavor name which is more than 255 characters will cause error.
        self.assertInvalidInput('a' * (MAX_LEN + 1), 64, 1, 120)

        # Flavor name which is empty should cause an error
        self.assertInvalidInput('', 64, 1, 120)

    def test_memory_must_be_positive_integer(self):
        self.assertInvalidInput('flavor1', 'foo', 1, 120)
        self.assertInvalidInput('flavor1', -1, 1, 120)
        self.assertInvalidInput('flavor1', 0, 1, 120)
        flavors.create('flavor1', 1, 1, 120)

    def test_vcpus_must_be_positive_integer(self):
        self.assertInvalidInput('flavor`', 64, 'foo', 120)
        self.assertInvalidInput('flavor1', 64, -1, 120)
        self.assertInvalidInput('flavor1', 64, 0, 120)
        flavors.create('flavor1', 64, 1, 120)

    def test_root_gb_must_be_nonnegative_integer(self):
        self.assertInvalidInput('flavor1', 64, 1, 'foo')
        self.assertInvalidInput('flavor1', 64, 1, -1)
        flavors.create('flavor1', 64, 1, 0)
        flavors.create('flavor2', 64, 1, 120)

    def test_swap_must_be_nonnegative_integer(self):
        self.assertInvalidInput('flavor1', 64, 1, 120, swap='foo')
        self.assertInvalidInput('flavor1', 64, 1, 120, swap=-1)
        flavors.create('flavor1', 64, 1, 120, swap=0)
        flavors.create('flavor2', 64, 1, 120, swap=1)

    def test_rxtx_factor_must_be_positive_float(self):
        self.assertInvalidInput('flavor1', 64, 1, 120, rxtx_factor='foo')
        self.assertInvalidInput('flavor1', 64, 1, 120, rxtx_factor=-1.0)
        self.assertInvalidInput('flavor1', 64, 1, 120, rxtx_factor=0.0)

        flavor = flavors.create('flavor1', 64, 1, 120, rxtx_factor=1.0)
        self.assertEqual(1.0, flavor['rxtx_factor'])

        flavor = flavors.create('flavor2', 64, 1, 120, rxtx_factor=1.1)
        self.assertEqual(1.1, flavor['rxtx_factor'])

    def test_is_public_must_be_valid_bool_string(self):
        self.assertInvalidInput('flavor1', 64, 1, 120, is_public='foo')

        flavors.create('flavor1', 64, 1, 120, is_public='TRUE')
        flavors.create('flavor2', 64, 1, 120, is_public='False')
        flavors.create('flavor3', 64, 1, 120, is_public='Yes')
        flavors.create('flavor4', 64, 1, 120, is_public='No')
        flavors.create('flavor5', 64, 1, 120, is_public='Y')
        flavors.create('flavor6', 64, 1, 120, is_public='N')
        flavors.create('flavor7', 64, 1, 120, is_public='1')
        flavors.create('flavor8', 64, 1, 120, is_public='0')
        flavors.create('flavor9', 64, 1, 120, is_public='true')

    def test_flavorid_populated(self):
        flavor1 = flavors.create('flavor1', 64, 1, 120)
        self.assertIsNot(None, flavor1['flavorid'])

        flavor2 = flavors.create('flavor2', 64, 1, 120, flavorid='')
        self.assertIsNot(None, flavor2['flavorid'])

        flavor3 = flavors.create('flavor3', 64, 1, 120, flavorid='foo')
        self.assertEqual('foo', flavor3['flavorid'])

    def test_default_values(self):
        flavor1 = flavors.create('flavor1', 64, 1, 120)

        self.assertIsNot(None, flavor1['flavorid'])
        self.assertEqual(flavor1['ephemeral_gb'], 0)
        self.assertEqual(flavor1['swap'], 0)
        self.assertEqual(flavor1['rxtx_factor'], 1.0)

    def test_basic_create(self):
        # Ensure instance types can be created.
        original_list = flavors.get_all_types()

        # Create new type and make sure values stick
        flavor = flavors.create('flavor', 64, 1, 120)
        self.assertEqual(flavor['name'], 'flavor')
        self.assertEqual(flavor['memory_mb'], 64)
        self.assertEqual(flavor['vcpus'], 1)
        self.assertEqual(flavor['root_gb'], 120)

        # Ensure new type shows up in list
        new_list = flavors.get_all_types()
        self.assertNotEqual(len(original_list), len(new_list),
                            'flavor was not created')

    def test_create_then_delete(self):
        original_list = flavors.get_all_types()

        flavor = flavors.create('flavor', 64, 1, 120)

        # Ensure new type shows up in list
        new_list = flavors.get_all_types()
        self.assertNotEqual(len(original_list), len(new_list),
                            'instance type was not created')

        flavors.destroy('flavor')
        self.assertRaises(exception.InstanceTypeNotFound,
                          flavors.get_instance_type, flavor['id'])

        # Deleted instance should not be in list anymore
        new_list = flavors.get_all_types()
        self.assertEqual(original_list, new_list)

    def test_duplicate_names_fail(self):
        # Ensures that name duplicates raise InstanceTypeCreateFailed.
        flavors.create('flavor', 256, 1, 120, 200, 'flavor1')
        self.assertRaises(exception.InstanceTypeExists,
                          flavors.create,
                          'flavor', 64, 1, 120)

    def test_duplicate_flavorids_fail(self):
        # Ensures that flavorid duplicates raise InstanceTypeCreateFailed.
        flavors.create('flavor1', 64, 1, 120, flavorid='flavorid')
        self.assertRaises(exception.InstanceTypeIdExists,
                          flavors.create,
                          'flavor2', 64, 1, 120, flavorid='flavorid')
