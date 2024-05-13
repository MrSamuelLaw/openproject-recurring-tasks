import asyncio
import unittest
import recurring
from models import APIConfig, WorkPackage



class TestCommon(unittest.TestCase):

    def test_can_query_templates(self):
        config = APIConfig.from_env()
        asyncio.run(recurring.build_shared_context(config))
        templates = asyncio.run(recurring.query_templates(config))
        clones = asyncio.run(recurring.build_clone_info(config, templates))
        new_work_package = asyncio.run(recurring.create_clone(config, clones[0]))
        new_work_package

if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)
