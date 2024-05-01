import boto3
from asnake.aspace import ASpace
from aws_assume_role_lib import assume_role
from requests import Session


class ArchivesSpaceClient(ASpace):
    """Client to interact with ArchivesSpace API."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.repository = kwargs['repository']

    def has_structured_dates(self, dates_array):
        """Parses date array to determine if structured dates are available.

        Args:
            dates_array (dict): Dates data from ArchivesSpace

        Returns:
            Boolean
        """
        start_dates = []
        end_dates = []
        for date in dates_array:
            start_dates.append(date.get('begin'))
            if date['date_type'] == 'single':
                end_dates.append(date.get('begin'))
            else:
                end_dates.append(date.get('end'))
        return bool(all([len(list(filter(None, start_dates))), len(list(filter(None, end_dates)))]))

    def get_package_data(self, refid):
        """Fetch data about an object in ArchivesSpace.

        Args:
            refid (string): RefID for an ArchivesSpace archival object.

        Returns:
            object_title, av_number, object_uri, resource_title, resource_uri (tuple of strings): data about the object.
        """
        results = self.client.get(f"/repositories/{self.repository}/find_by_id/archival_objects?ref_id[]={refid}&resolve[]=archival_objects&resolve[]=archival_objects::resource").json()
        try:
            if len(results['archival_objects']) != 1:
                raise Exception(f'Expecting to get one result for ref id {refid} but got {len(results["archival_objects"])} instead.')
            object = results['archival_objects'][0]['_resolved']
            object_uri = object['uri']
            resource = object['resource']['_resolved']
            resource_title = resource['title']
            resource_uri = resource['uri']
            undated_object = self.has_structured_dates(object['dates'])
            return object['display_string'], object_uri, resource_title, resource_uri, undated_object
        except KeyError:
            raise Exception(f'Unable to fetch results for {refid}. Got results {results}')


class AquilaClient(object):

    def __init__(self, baseurl):
        self.baseurl = baseurl.rstrip("/")
        self.client = Session()

    def available_rights_statements(self):
        """Fetches available rights statements from Aquila.

        Returns:
            rights_statements (list of tuples): IDs and display strings of rights statements
        """
        return self.client.get(f'{self.baseurl}/api/rights/').json()


class AWSClient(object):

    def __init__(self, resource, role_arn):
        """Gets Boto3 client which authenticates with a specific IAM role."""
        self.client = self.get_client_with_role(resource, role_arn)

    def get_client_with_role(self, resource, role_arn):
        """Gets Boto3 client which authenticates with a specific IAM role."""
        session = boto3.Session()
        assumed_role_session = assume_role(session, role_arn)
        return assumed_role_session.client(resource)

    def deliver_message(self, sns_topic, package, message, outcome, traceback=None, rights_ids=None):
        """Delivers message to SNS Topic."""
        attributes = {
            'service': {
                'DataType': 'String',
                'StringValue': 'digitized_image_qc',
            },
            'outcome': {
                'DataType': 'String',
                'StringValue': outcome,
            }
        }
        if package:
            attributes['refid'] = {
                'DataType': 'String',
                'StringValue': package.refid,
            }
        if traceback:
            attributes['traceback'] = {
                'DataType': 'String',
                'StringValue': traceback,
            }
        if rights_ids:
            attributes['rights_ids'] = {
                'DataType': 'String',
                'StringValue': rights_ids,
            }
        self.client.publish(
            TopicArn=sns_topic,
            Message=message,
            MessageAttributes=attributes)
