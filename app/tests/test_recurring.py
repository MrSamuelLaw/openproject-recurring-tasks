import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from recurring import Project


class TestCommon(unittest.TestCase):

    @patch('recurring.com', new_callable=AsyncMock)
    def test_can_query_templates(self, mock_com):
        mock_com.query_projects.return_value = {
            '_embedded': {'elements': [
                {
                    'id': -1,
                    'active': True,
                    'name': 'Mocked'
                }
            ]}
        }
        result = asyncio.run(Project.query_projects())
        project = result[0]
        self.assertEqual(project.id, -1)

if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=False)
