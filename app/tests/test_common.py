import os
import asyncio
import unittest
import common
from models import APIConfig

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
        url = common.build_url(config, 'workpackages')


    def test_can_query_workpackages(self):
        config = APIConfig.from_environment_variables()
        asyncio.run(common.query_work_packages(config))


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)