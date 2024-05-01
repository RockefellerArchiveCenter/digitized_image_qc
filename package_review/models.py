from django.db import models


class Package(models.Model):
    """Package of digitized AV files."""
    PENDING = 0
    APPROVED = 9
    REJECTED = 5
    PROCESS_STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'))

    title = models.CharField(max_length=255)
    uri = models.CharField(max_length=255)
    resource_title = models.CharField(max_length=255)
    resource_uri = models.CharField(max_length=255)
    undated_object = models.BooleanField(default=False)
    possible_duplicate = models.BooleanField(default=False)
    refid = models.CharField(max_length=32)
    tree = models.JSONField(null=True, blank=True)
    process_status = models.IntegerField(choices=PROCESS_STATUS_CHOICES)
    rights_ids = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def archivesspace_link(self):
        """Returns a link to an archival object in ArchivesSpace."""
        resource_id = self.resource_uri.split("/")[-1]
        object_id = self.uri.split("/")[-1]
        return f'https://as.rockarch.org/resources/{resource_id}#tree::archival_object_{object_id}'


class RightsStatement(models.Model):
    """Rights statement stored in Aquila."""

    title = models.CharField(max_length=255)
    aquila_id = models.IntegerField()
    last_modified = models.DateTimeField(auto_now=True)
