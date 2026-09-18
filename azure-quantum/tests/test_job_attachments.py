##
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
##

from unittest.mock import Mock, patch
from azure.quantum import Job, JobDetails


UNSIGNED_CONTAINER_URI = "https://acct.blob.core.windows.net/job-id"
SIGNED_CONTAINER_URI = f"{UNSIGNED_CONTAINER_URI}?sas"


def _job_with_container(container_uri=UNSIGNED_CONTAINER_URI, workspace=None) -> Job:
    job_details = JobDetails(
        id="job-id",
        name="",
        provider_id="",
        target="",
        container_uri=container_uri,
        input_data_format="",
        output_data_format="",
    )
    return Job(workspace=workspace, job_details=job_details)


@patch("azure.quantum.job.base_job.ContainerClient")
def test_list_attachments_returns_container_blobs(mock_container_client):
    workspace = Mock()
    workspace.get_container_uri.return_value = SIGNED_CONTAINER_URI
    job = _job_with_container(workspace=workspace)

    blob_a = Mock()
    blob_b = Mock()
    container = mock_container_client.from_container_url.return_value
    container.list_blobs.return_value = [blob_a, blob_b]

    result = job.list_attachments()

    workspace.get_container_uri.assert_called_once_with(job_id="job-id")
    mock_container_client.from_container_url.assert_called_once_with(SIGNED_CONTAINER_URI)
    assert result == [blob_a, blob_b]


@patch("azure.quantum.job.base_job.ContainerClient")
def test_list_attachments_uses_workspace_container_when_unset(mock_container_client):
    workspace = Mock()
    workspace.get_container_uri.return_value = SIGNED_CONTAINER_URI
    job = _job_with_container(container_uri=None, workspace=workspace)

    container = mock_container_client.from_container_url.return_value
    container.list_blobs.return_value = []

    result = job.list_attachments()

    workspace.get_container_uri.assert_called_once_with(job_id="job-id")
    mock_container_client.from_container_url.assert_called_once_with(SIGNED_CONTAINER_URI)
    assert result == []


def test_upload_attachment_uses_fresh_workspace_container_uri():
    workspace = Mock()
    workspace.get_container_uri.return_value = SIGNED_CONTAINER_URI
    job = _job_with_container(workspace=workspace)
    job.upload_input_data = Mock(return_value="uploaded-uri")

    result = job.upload_attachment("attachment", b"data")

    workspace.get_container_uri.assert_called_once_with(job_id="job-id")
    job.upload_input_data.assert_called_once_with(
        container_uri=SIGNED_CONTAINER_URI,
        blob_name="attachment",
        input_data=b"data",
    )
    assert result == "uploaded-uri"


@patch("azure.quantum.job.base_job.ContainerClient")
def test_download_attachment_uses_fresh_workspace_container_uri(mock_container_client):
    workspace = Mock()
    workspace.get_container_uri.return_value = SIGNED_CONTAINER_URI
    job = _job_with_container(workspace=workspace)
    blob_client = mock_container_client.from_container_url.return_value.get_blob_client.return_value
    blob_client.download_blob.return_value.readall.return_value = b"data"

    result = job.download_attachment("attachment")

    workspace.get_container_uri.assert_called_once_with(job_id="job-id")
    mock_container_client.from_container_url.assert_called_once_with(SIGNED_CONTAINER_URI)
    assert result == b"data"


@patch("azure.quantum.job.base_job.ContainerClient")
def test_attachment_methods_honor_explicit_container_uri(mock_container_client):
    workspace = Mock()
    job = _job_with_container(workspace=workspace)
    job.upload_input_data = Mock(return_value="uploaded-uri")
    blob_client = mock_container_client.from_container_url.return_value.get_blob_client.return_value
    blob_client.download_blob.return_value.readall.return_value = b"data"
    explicit_uri = "https://custom.blob.core.windows.net/container?sas"

    job.upload_attachment("upload", b"data", container_uri=explicit_uri)
    job.download_attachment("download", container_uri=explicit_uri)

    workspace.get_container_uri.assert_not_called()
    job.upload_input_data.assert_called_once_with(
        container_uri=explicit_uri,
        blob_name="upload",
        input_data=b"data",
    )
    mock_container_client.from_container_url.assert_called_once_with(explicit_uri)
