import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from recurring import WorkPackageSchema, WorkPackage


class TestCommon(unittest.TestCase):


    def test_can_get_schema_project_and_type_ids(self):
        """Tests that a schema can accurately provide the information
        used to query  it again.
        """
        with patch('recurring.com.query_work_package_schema', new_callable=AsyncMock) as mock_query:
            mock_schema_data = {
                '_links': {
                    'self': {'href': 'api/v3/schemas/1-1'}
                }
            }
            mock_query.return_value = mock_schema_data
            schema = asyncio.run(WorkPackageSchema.query_work_package_schema(1, 1))
            self.assertEqual(schema.project_id, 1)
            self.assertEqual(schema.type_id, 1)


    def test_can_get_schema_custom_fields(self):
        """Tests that the custom fields mapping is updated when a schema is
        called for the first time.
        """
        with patch('recurring.com.query_work_package_schema', new_callable=AsyncMock) as mock_query:
            mock_schema_data = {
                'customField1': {'name': 'My Custom Field 1'},
                '_links': {
                    'self': {'href': 'api/v3/schemas/1-1'}
                }
            }
            mock_query.return_value = mock_schema_data
            schema = asyncio.run(WorkPackageSchema.query_work_package_schema(1, 1))
            self.assertIsNotNone(schema.get('My Custom Field 1'))


    def test_can_get_work_package_custom_fields(self):
        """Tests that work packages can access data in the WorkPackageSchema class
        in order to correctly return information based on user defined field names.
        """
        with patch('recurring.com.query_work_package_schema', new_callable=AsyncMock) as mock_query:
            mock_schema_data = {
                'customField1': {'name': 'My Custom Field 1'},
                'customField2': {'name': 'My Custom Field 2'},
                '_links': {
                    'self': {'href': 'api/v3/schemas/1-1'}
                }
            }
            mock_query.return_value = mock_schema_data
            asyncio.run(WorkPackageSchema.query_work_package_schema(1, 1))
            with patch('recurring.com.query_work_packages', new_callable=AsyncMock) as mock_query:
                mock_work_packages_data = {
                    '_embedded': {
                        'elements': [
                            {
                                'id': 1,
                                '_type': 'Task',
                                'subject': 'Mocked Task',
                                'customField1': 'foo',
                                '_links': {
                                    'customField2': 'bar',
                                }

                            }
                        ]
                    }
                }
                mock_query.return_value = mock_work_packages_data
                work_packages = asyncio.run(WorkPackage.query_work_packages())
                wp = work_packages[0]
                self.assertEqual(wp['customField1'], 'foo')
                self.assertEqual(wp['customField2'], 'bar')



if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)
