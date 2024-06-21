import os
import unittest
import common as com



class TestCommon(unittest.TestCase):

    def test_can_build_app_configs(self):
        com.APIConfig(**{
            'api_key':      os.environ['API_KEY'],
            'host':         os.environ['HOST'],
            'verify_ssl':   os.environ['VERIFY_SSL'],
            'https':        os.environ['HTTPS'],
        })

    def test_can_build_url(self):
        config = com.APIConfig(**{
            'api_key':      '1234',
            'host':         'foo.local',
            'verify_ssl':   False,
            'https':        False,
        })
        url = com.build_url(config, 'api/v3/workpackages')
        self.assertEqual(url, 'http://foo.local/api/v3/workpackages')


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)