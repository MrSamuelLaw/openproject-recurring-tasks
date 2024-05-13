import os
import asyncio
import unittest
import common
import json
from models import APIConfig, SharedContext



class TestCommon(unittest.TestCase):

    def test_can_build_app_configs(self):
        APIConfig(**{
            'api_key':      os.environ['API_KEY'],
            'host':         os.environ['HOST'],
            'verify_ssl':   os.environ['VERIFY_SSL'],
            'https':        os.environ['HTTPS'],
        })

    def test_can_build_url(self):
        config = APIConfig(**{
            'api_key':      '1234',
            'host':         'foo.local',
            'verify_ssl':   False,
            'https':        False,
        })
        url = common.build_url(config, 'api/v3/workpackages')
        self.assertEqual(url, 'http://foo.local/api/v3/workpackages')

    def test_can_query_projects(self):
        config = APIConfig.from_env()
        asyncio.run(common.query_projects(config))

    def test_can_query_work_packages(self):
        config = APIConfig.from_env()
        asyncio.run(common.query_work_packages(config))

    def test_can_query_work_package_schema(self):
        config = APIConfig.from_env()
        work_packages = asyncio.run(common.query_work_packages(config))
        wp = work_packages[0]
        schema = asyncio.run(common.query_work_package_schema(config, wp.schema_id))
        self.assertTrue(schema)

    def test_can_build_work_package_payload(self):
        config = APIConfig.from_env()
        work_packages = asyncio.run(common.query_work_packages(config))
        wp = work_packages[0]
        schema = asyncio.run(common.query_work_package_schema(config, wp.schema_id))
        payload = common.build_work_package_payload(wp, schema)
        self.assertTrue(payload)

    # def test_can_get_custom_fields(self):
    #     config = APIConfig.from_env()
    #     asyncio.run(common.build_shared_context())
    #     projects = asyncio.run(common.query_projects(config))
    #     project = [p for p in projects if p.name == 'Main'][0]
    #     filters=[{'project': {'operator': '=', 'values': [project.id]}}]
    #     work_packages = asyncio.run(common.query_work_packages(config, filters=json.dumps(filters)))
    #     wp = work_packages[0]
    #     wp['Follow Up Date']


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)