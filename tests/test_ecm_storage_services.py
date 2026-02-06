from unittest.mock import MagicMock, patch

from app.services.ecm_storage import StorageService


class TestStorageService:
    def test_generate_storage_key_format(self):
        key = StorageService.generate_storage_key("doc-123", "report.pdf")
        assert key.startswith("documents/doc-123/")
        assert key.endswith("/report.pdf")

    def test_is_configured_false_by_default(self):
        assert StorageService.is_configured() is False

    @patch("app.services.ecm_storage.settings")
    def test_is_configured_true(self, mock_settings):
        mock_settings.s3_endpoint_url = "http://localhost:9000"
        mock_settings.s3_access_key = "test-key"
        mock_settings.s3_secret_key = "test-secret"
        assert StorageService.is_configured() is True

    @patch("app.services.ecm_storage.boto3")
    @patch("app.services.ecm_storage.settings")
    def test_generate_upload_url(self, mock_settings, mock_boto3):
        mock_settings.s3_endpoint_url = "http://localhost:9000"
        mock_settings.s3_access_key = "test-key"
        mock_settings.s3_secret_key = "test-secret"
        mock_settings.s3_region = "us-east-1"
        mock_settings.s3_bucket_name = "ecm-documents"
        mock_settings.s3_presigned_url_expiry = 3600

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://example.com/upload"
        mock_boto3.client.return_value = mock_client

        url = StorageService.generate_upload_url("key/file.pdf", "application/pdf")
        assert url == "https://example.com/upload"
        mock_client.generate_presigned_url.assert_called_once()

    @patch("app.services.ecm_storage.boto3")
    @patch("app.services.ecm_storage.settings")
    def test_generate_download_url(self, mock_settings, mock_boto3):
        mock_settings.s3_endpoint_url = "http://localhost:9000"
        mock_settings.s3_access_key = "test-key"
        mock_settings.s3_secret_key = "test-secret"
        mock_settings.s3_region = "us-east-1"
        mock_settings.s3_bucket_name = "ecm-documents"
        mock_settings.s3_presigned_url_expiry = 3600

        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://example.com/download"
        mock_boto3.client.return_value = mock_client

        url = StorageService.generate_download_url("key/file.pdf")
        assert url == "https://example.com/download"
        mock_client.generate_presigned_url.assert_called_once()
