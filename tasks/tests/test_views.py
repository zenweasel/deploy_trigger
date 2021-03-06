from unittest.mock import MagicMock
import sure
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from .. import views
from . import factories


class BaseViewCase(TestCase):
    """Base view case"""

    def setUp(self):
        self.api_client = APIClient()
        self._create_user()

    def _create_user(self):
        """Create user and authenticate"""
        self.user = User.objects.create_user('test', 'test@test.test', 'test')
        self.api_client.login(
            username='test',
            password='test',
        )


class RepositoryViewCase(BaseViewCase):
    """Repository view case"""

    def setUp(self):
        self._mock_github()
        self.url = '/api/v1/repositories/'
        super(RepositoryViewCase, self).setUp()

    def _mock_github(self):
        """Mock github client"""
        self._orig_github = User.github
        User.github = MagicMock()

    def tearDown(self):
        User.github = self._orig_github

    def test_list_repositories(self):
        """Test list repositories"""
        User.github.get_user.return_value.get_repos.return_value =\
            [MagicMock()] * 10
        response = self.api_client.get(self.url)
        len(response.data).should.be.equal(10)


class TaskViewCase(BaseViewCase):
    """Task view case"""

    def setUp(self):
        super(TaskViewCase, self).setUp()
        self.url = '/api/v1/tasks/'

    def test_receive_self_tasks(self):
        """Test receive self tasks"""
        factories.TaskFactory.create_batch(20, user=self.user)
        response = self.api_client.get(self.url)
        len(response.data).should.be.equal(20)

    def test_not_return_other_user_tasks(self):
        """Test not return other user tasks"""
        factories.TaskFactory.create_batch(20)
        response = self.api_client.get(self.url)
        len(response.data).should.be.equal(0)


class JobViewCase(BaseViewCase):
    """Job view case"""

    def setUp(self):
        super(JobViewCase, self).setUp()
        self.url = '/api/v1/jobs/'

    def test_receive_self_jobs(self):
        """Test receive self jobs"""
        factories.JobFactory.create_batch(20, task__user=self.user)
        response = self.api_client.get(self.url)
        len(response.data).should.be.equal(20)

    def test_not_return_other_user_jobs(self):
        """Test not return other user jobs"""
        factories.JobFactory.create_batch(20)
        response = self.api_client.get(self.url)
        len(response.data).should.be.equal(0)


class JobTriggerViewCase(TestCase):
    """Job trigger view case"""

    def setUp(self):
        self.api_client = APIClient()
        self.url = '/api/v1/triggers/'
        self._mock_job()

    def _mock_job(self):
        """Mock rq job"""
        self._orig_perform_job = views.perform_job
        views.perform_job = MagicMock()

    def tearDown(self):
        views.perform_job = self._orig_perform_job

    def test_create_job(self):
        """Test create job"""
        factories.TaskFactory(name='owner/test')
        response = self.api_client.post(self.url, data={
            'repository': {
                'name': 'test',
                'owner': {'name': 'owner'},
            }
        }, format='json')
        response.status_code.should.be.equal(201)
        views.perform_job.delay.call_count.should.be.equal(1)

    def test_not_exists_repo(self):
        """Test trigger for not exists repo"""
        response = self.api_client.post(self.url, data={
            'repository': {
                'name': 'test',
                'owner': {'name': 'owner'},
            }
        }, format='json')
        response.status_code.should.be.equal(404)
