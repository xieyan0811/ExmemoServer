import io
import os
from minio import Minio
from minio.error import S3Error
from typing import Optional

# Retrieve config from environment variables
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "exmemo-data")

class StorageEngine:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(BUCKET_NAME):
                self.client.make_bucket(BUCKET_NAME)
        except S3Error as err:
            print(f"MinIO Engine bucket init error: {err}")

    def put_file(self, object_name: str, file_data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload raw bytes to MinIO"""
        try:
            data_stream = io.BytesIO(file_data)
            self.client.put_object(
                BUCKET_NAME,
                object_name,
                data_stream,
                length=len(file_data),
                content_type=content_type
            )
            return object_name
        except S3Error as err:
            print(f"Error uploading file {object_name}: {err}")
            raise

    def get_file(self, object_name: str) -> Optional[bytes]:
        """Fetch raw bytes from MinIO"""
        try:
            response = self.client.get_object(BUCKET_NAME, object_name)
            return response.read()
        except S3Error as err:
            print(f"Error downloading file {object_name}: {err}")
            return None
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()

    def put_markdown(self, object_name: str, content: str) -> str:
        """Convenience wrapper for saving Markdown strings"""
        return self.put_file(object_name, content.encode('utf-8'), "text/markdown")

    def get_markdown(self, object_name: str) -> Optional[str]:
        """Convenience wrapper for getting Markdown content"""
        data = self.get_file(object_name)
        if data is not None:
            return data.decode('utf-8')
        return None

    def delete_file(self, object_name: str):
        try:
            self.client.remove_object(BUCKET_NAME, object_name)
        except S3Error as err:
            print(f"Error deleting file {object_name}: {err}")

storage_engine = StorageEngine()
