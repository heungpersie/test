"""배포 전 환경 혼선을 실제로 차단하는지 확인합니다. AWS·Docker 접속은 하지 않습니다."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / 'infra/deploy/validate_environment.py'
spec = importlib.util.spec_from_file_location('deployment_environment', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config(target):
    policy = module.POLICIES[target]
    return {'name': policy['project'], 'services': {'api': {
        'environment': {'APP_ENV': target, 'DB_HOST': 'db.internal.example',
                        'DB_NAME': policy['db'], 'DB_USER': policy['user'],
                        'DB_PASSWORD': 'test-secret-do-not-print'},
        'ports': [{'host_ip': '127.0.0.1', 'published': policy['port'], 'target': 8000}],
    }}}


class EnvironmentSeparationTests(unittest.TestCase):
    def test_correct_environments(self):
        for target in ['dev', 'demo']:
            self.assertEqual(module.validate(config(target), target), [])

    def test_dev_cannot_deploy_as_demo(self):
        self.assertTrue(module.validate(config('dev'), 'demo'))

    def test_wrong_database_or_account_is_rejected(self):
        for key, value in [('DB_NAME', 'coach_demo'), ('DB_USER', 'coach_demo_app'),
                           ('DB_HOST', 'localhost'), ('DB_PASSWORD', '')]:
            bad = config('dev')
            bad['services']['api']['environment'][key] = value
            self.assertTrue(module.validate(bad, 'dev'), key)

    def test_public_or_wrong_port_is_rejected(self):
        for key, value in [('host_ip', '0.0.0.0'), ('published', '18001')]:
            bad = config('dev')
            bad['services']['api']['ports'][0][key] = value
            self.assertTrue(module.validate(bad, 'dev'))

    def test_error_messages_do_not_contain_secret(self):
        bad = copy.deepcopy(config('dev'))
        bad['name'] = 'wrong-project'
        messages = module.validate(bad, 'dev')
        self.assertNotIn('test-secret-do-not-print', '\n'.join(messages))

    def test_unknown_environment_is_rejected(self):
        self.assertTrue(module.validate(config('dev'), 'production'))


if __name__ == '__main__':
    unittest.main()
