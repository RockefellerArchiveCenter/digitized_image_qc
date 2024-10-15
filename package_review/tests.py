import json
import random
import shutil
from pathlib import Path
from unittest.mock import patch

import boto3
from django.conf import settings
from django.shortcuts import reverse
from django.test import TestCase
from moto import mock_sns, mock_sqs, mock_ssm, mock_sts
from moto.core import DEFAULT_ACCOUNT_ID

from .clients import ArchivesSpaceClient, AWSClient
from .helpers import get_config
from .management.commands import (check_qc_status, discover_packages,
                                  fetch_rights_statements,
                                  send_startup_message)
from .models import Package, RightsStatement

FIXTURE_DIR = "fixtures"
RIGHTS_DATA = [("1", "foo"), ("2", "bar")]
PACKAGE_DATA = [("foo", "9ba10e5461d401517b0e1a53d514ec87", "9ba10e5461d401517b0e1a53d514ec87/\n----- 9ba10e5461d401517b0e1a53d514ec87_0001.pdf"),
                ("bar", "f7d3dd6dc9c4732fa17dbd88fbe652b6", "f7d3dd6dc9c4732fa17dbd88fbe652b6/\n----- f7d3dd6dc9c4732fa17dbd88fbe652b6_0001.pdf")]


def create_rights_statements():
    for aquila_id, title in RIGHTS_DATA:
        RightsStatement.objects.create(
            aquila_id=aquila_id,
            title=title)


def create_packages():
    for title, refid, tree in PACKAGE_DATA:
        Package.objects.create(
            title=title,
            refid=refid,
            tree=tree,
            process_status=Package.PENDING)


def copy_binaries():
    """Moves binary files into place."""
    for refid in ['9ba10e5461d401517b0e1a53d514ec87', 'f7d3dd6dc9c4732fa17dbd88fbe652b6']:
        shutil.copytree(
            Path("package_review", FIXTURE_DIR, "packages", refid),
            Path(settings.BASE_STORAGE_DIR, refid),
            dirs_exist_ok=True)


class HelpersTests(TestCase):

    @mock_ssm
    @patch('package_review.clients.AWSClient.get_client_with_role')
    def test_get_config(self, mock_client):
        """Asserts configs are properly fetched from SSM"""
        ssm = boto3.client('ssm', region_name='us-east-1')
        mock_client.return_value = ssm
        path = "/dev/digitized-av-qc"
        for name, value in [("foo", "bar"), ("baz", "buzz")]:
            ssm.put_parameter(
                Name=f"{path}/{name}",
                Value=value,
                Type="SecureString",
            )
        config = get_config(path)
        self.assertIsInstance(config, dict)
        self.assertEqual(config, {'foo': 'bar', 'baz': 'buzz'})


class ArchivesSpaceClientTests(TestCase):

    @patch('asnake.aspace.ASpace.__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None
        self.as_client = ArchivesSpaceClient(
            username='admin',
            password='admin',
            baseurl='https://archivesspace.org/api',
            repository='2')

    def test_init(self):
        """Asserts repository identifier is correctly set."""
        self.assertEqual(
            self.as_client.repository,
            '2')

    def test_has_structured_dates(self):
        """Asserts presence of structured dates are parsed correctly."""
        for dates, expected in [
            ([], False),
            ([{
                "expression": "1950",
                "date_type": "single"
            }], False),
            ([{
                "begin": "1950",
                "end": "1969",
                "date_type": "inclusive",
            }], True),
            ([{
                "begin": "1950",
                "date_type": "single"
            }], True)
        ]:
            output = self.as_client.has_structured_dates(dates)
            self.assertEqual(output, expected)


class AWSClientTests(TestCase):

    def setUp(self):
        create_packages()

    @mock_sns
    @mock_sqs
    @mock_sts
    @patch('package_review.clients.AWSClient.get_client_with_role')
    def test_deliver_message(self, mock_client):
        sns = boto3.client('sns', region_name='us-east-1')
        mock_client.return_value = sns
        topic_arn = sns.create_topic(Name='my-topic')['TopicArn']
        sqs_conn = boto3.resource("sqs", region_name="us-east-1")
        sqs_conn.create_queue(QueueName="test-queue")
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol="sqs",
            Endpoint=f"arn:aws:sqs:us-east-1:{DEFAULT_ACCOUNT_ID}:test-queue")

        client = AWSClient('sns', settings.AWS['role_arn'])

        package = random.choice(Package.objects.all())

        client.deliver_message(
            topic_arn,
            package,
            "This is a message",
            "SUCCESS",
            rights_ids="1,2")

        queue = sqs_conn.get_queue_by_name(QueueName="test-queue")
        messages = queue.receive_messages(MaxNumberOfMessages=1)
        message_body = json.loads(messages[0].body)
        self.assertEqual(message_body['MessageAttributes']['outcome']['Value'], 'SUCCESS')
        self.assertEqual(message_body['MessageAttributes']['refid']['Value'], package.refid)
        self.assertEqual(message_body['MessageAttributes']['rights_ids']['Value'], "1,2")


class DiscoverPackagesCommandTests(TestCase):

    def setUp(self):
        copy_binaries()

    def test_get_tree(self):
        for refid in ["9ba10e5461d401517b0e1a53d514ec87", "f7d3dd6dc9c4732fa17dbd88fbe652b6"]:
            tree = discover_packages.Command()._get_dir_tree(Path("package_review", FIXTURE_DIR, "packages", refid))
            self.assertIsInstance(tree, str)
            self.assertIn(refid, tree)
            self.assertIn('master', tree)
            self.assertIn('master_edited', tree)
            self.assertIn('service_edited', tree)

    @mock_sts
    @patch('package_review.clients.ArchivesSpaceClient.__init__')
    @patch('package_review.clients.ArchivesSpaceClient.get_package_data')
    @patch('package_review.clients.AWSClient.deliver_message')
    @patch('package_review.clients.AWSClient.get_client_with_role')
    @patch('package_review.management.commands.discover_packages.get_config')
    def test_handle(self, mock_config, mock_client, mock_message, mock_package_data, mock_init):
        """Asserts cron produces expected results."""
        expected_len = len(list(Path(settings.BASE_STORAGE_DIR).iterdir()))
        mock_init.return_value = None
        mock_package_data.return_value = 'object_title', 'object_uri', 'resource_title', 'resource_uri', False, False

        discover_packages.Command().handle()
        mock_config.assert_called_once()
        mock_init.assert_called_once()
        mock_client.assert_not_called()
        mock_message.assert_not_called()
        self.assertEqual(mock_package_data.call_count, expected_len)
        self.assertEqual(Package.objects.all().count(), expected_len)
        discover_packages.Command().handle()
        mock_message.assert_not_called()

    @mock_sns
    @mock_sts
    @patch('package_review.clients.ArchivesSpaceClient.__init__')
    @patch('package_review.clients.ArchivesSpaceClient.get_package_data')
    @patch('package_review.clients.AWSClient.deliver_message')
    @patch('package_review.clients.AWSClient.get_client_with_role')
    @patch('package_review.helpers.get_config')
    def test_handle_exception(self, mock_config, mock_client, mock_message, mock_package_data, mock_init):
        """Asserts exceptions while processing packages are handled as expected."""
        expected_len = len(list(Path(settings.BASE_STORAGE_DIR).iterdir()))
        mock_package_data.side_effect = Exception("foo")
        mock_init.return_value = None
        discover_packages.Command().handle()
        self.assertEqual(mock_message.call_count, expected_len)

    def tearDown(self):
        for dir in Path(settings.BASE_STORAGE_DIR).iterdir():
            shutil.rmtree(dir)


class CheckQCStatusCommandTests(TestCase):

    @mock_sns
    @mock_sts
    @patch('package_review.clients.AWSClient.deliver_message')
    @patch('package_review.clients.AWSClient.get_client_with_role')
    def test_qc_done(self, mock_client, mock_message):
        for dir in Path(settings.BASE_STORAGE_DIR).iterdir():
            shutil.rmtree(dir)
        check_qc_status.Command().handle()
        mock_message.assert_called_once_with(
            settings.AWS['sns_topic'],
            None,
            'No packages left to QC',
            'COMPLETE')

    @mock_sns
    @mock_sts
    @patch('package_review.clients.AWSClient.deliver_message')
    @patch('package_review.clients.AWSClient.get_client_with_role')
    def test_no_message(self, mock_client, mock_message):
        copy_binaries()
        check_qc_status.Command().handle()
        mock_message.assert_not_called()

    def tearDown(self):
        for dir in Path(settings.BASE_STORAGE_DIR).iterdir():
            shutil.rmtree(dir)


class CheckStartupMessageCommandTests(TestCase):

    @mock_sns
    @mock_sts
    @patch('package_review.clients.AWSClient.deliver_message')
    @patch('package_review.clients.AWSClient.get_client_with_role')
    def test_qc_done(self, mock_client, mock_message):
        send_startup_message.Command().handle()
        mock_message.assert_called_once_with(
            settings.AWS['sns_topic'],
            None,
            'Packages are waiting to be QCed',
            'STARTED')


class FetchRightsStatementsCommandTests(TestCase):

    @patch('package_review.clients.AquilaClient.available_rights_statements')
    def test_handle(self, mock_rights):
        """Asserts FetchRights cron only adds new rights statements."""
        rights_statements = [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}]
        mock_rights.return_value = rights_statements
        fetch_rights_statements.Command().handle()
        mock_rights.assert_called_once_with()
        self.assertEqual(RightsStatement.objects.all().count(), len(rights_statements))

        fetch_rights_statements.Command().handle()
        self.assertEqual(RightsStatement.objects.all().count(), len(rights_statements))


class ViewMixinTests(TestCase):

    def setUp(self):
        create_rights_statements()
        create_packages()

    def test_rights_statement_mixin(self):
        """Asserts rights statements are inserted in views."""
        package_pk = random.choice(Package.objects.all()).pk
        response = self.client.get(reverse('package-detail', args=[package_pk]))
        self.assertEqual(RightsStatement.objects.all().count(), len(response.context['rights_statements']))

        response = self.client.get(reverse('package-bulk-approve'))
        self.assertEqual(len(RIGHTS_DATA), len(response.context['rights_statements']))

    def test_bulk_action_list_mixin(self):
        """Asserts objects are fetched from URL params."""
        form_data = "&".join([f'{str(obj.pk)}=on' for obj in Package.objects.all()])
        for view_str in ['package-bulk-approve', 'package-bulk-reject']:
            response = self.client.get(f'{reverse(view_str)}?{form_data}')
            self.assertEqual(Package.objects.all().count(), len(response.context['object_list']))


class PackageActionViewTests(TestCase):

    def setUp(self):
        create_rights_statements()
        create_packages()
        copy_binaries()

    @patch('package_review.clients.AWSClient.__init__')
    @patch('package_review.clients.AWSClient.deliver_message')
    def test_approve_view(self, mock_deliver, mock_init):
        mock_init.return_value = None
        pkg_list = ",".join([str(obj.id) for obj in Package.objects.all()])
        rights_list = ",".join([str(obj.id) for obj in RightsStatement.objects.all()])
        response = self.client.post(f'{reverse("package-approve")}?object_list={pkg_list}&rights_ids={rights_list}')
        self.assertEqual(mock_deliver.call_count, Package.objects.all().count())
        for package in Package.objects.all():
            self.assertEqual(package.process_status, Package.APPROVED)
            self.assertEqual(package.rights_ids, rights_list)
        self.assertEqual(len(list(Path(settings.BASE_STORAGE_DIR).iterdir())), Package.objects.all().count())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('package-list'))

    @patch('package_review.clients.AWSClient.__init__')
    @patch('package_review.clients.AWSClient.deliver_message')
    def test_reject_view(self, mock_delete, mock_init):
        mock_init.return_value = None
        pkg_list = ",".join([str(obj.id) for obj in Package.objects.all()])
        response = self.client.post(f'{reverse("package-reject")}?object_list={pkg_list}')
        self.assertEqual(mock_delete.call_count, Package.objects.all().count())
        for package in Package.objects.all():
            self.assertEqual(package.process_status, Package.REJECTED)
        self.assertTrue(len(list(Path(settings.BASE_STORAGE_DIR).iterdir())) == 0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('package-list'))

    @patch('package_review.clients.ArchivesSpaceClient.__init__')
    @patch('package_review.clients.ArchivesSpaceClient.get_package_data')
    @patch('package_review.views.get_config')
    def test_refresh_view(self, mock_config, mock_data, mock_init):
        mock_init.return_value = None
        title = "title"
        object_uri = "/repositories/2/archival_objects/1"
        resource_title = "resource title"
        resource_uri = "/repositories/2/resources/1"
        undated_object = True
        already_digitized = False
        mock_data.return_value = title, object_uri, resource_title, resource_uri, undated_object, already_digitized
        package = random.choice(Package.objects.all())
        response = self.client.get(f'{reverse("refresh-data")}?object_list={package.id}')
        package.refresh_from_db()
        self.assertEqual(package.title, title)
        self.assertEqual(package.uri, object_uri)
        self.assertEqual(package.resource_title, resource_title)
        self.assertEqual(package.resource_uri, resource_uri)
        self.assertEqual(package.undated_object, undated_object)
        self.assertEqual(package.already_digitized, already_digitized)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('package-detail', kwargs={'pk': package.pk}))


class HealthCheckEndpointTests(TestCase):

    def test_endpoint_response(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
