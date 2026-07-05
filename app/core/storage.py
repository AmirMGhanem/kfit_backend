import logging

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

_BOTO_CONFIG = Config(signature_version="s3v4")
_REGION = "us-east-1"  # MinIO ignores this but boto3 requires it


def _make_client(endpoint_url: str) -> "boto3.client":
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=_BOTO_CONFIG,
        region_name=_REGION,
    )


# Module-level singletons — boto3 clients are thread-safe for concurrent reads.
# Two clients because presigned URLs must embed the public hostname (localhost:9000),
# while bucket operations must reach MinIO over the Docker-internal network (minio:9000).
_internal_client: "boto3.client | None" = None
_public_client: "boto3.client | None" = None


def _get_internal() -> "boto3.client":
    global _internal_client
    if _internal_client is None:
        _internal_client = _make_client(settings.MINIO_INTERNAL_URL)
    return _internal_client


def _get_public() -> "boto3.client":
    global _public_client
    if _public_client is None:
        _public_client = _make_client(settings.MINIO_PUBLIC_URL)
    return _public_client


def ensure_bucket() -> None:
    """Create the media bucket if it does not exist. Called at app startup."""
    cl = _get_internal()
    try:
        cl.head_bucket(Bucket=settings.MINIO_BUCKET)
        logger.info("bucket %r already exists", settings.MINIO_BUCKET)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            cl.create_bucket(Bucket=settings.MINIO_BUCKET)
            logger.info("bucket %r created", settings.MINIO_BUCKET)
        else:
            raise


def presigned_put_url(key: str, content_type: str, expires: int = 3600) -> str:
    """
    Return a presigned PUT URL pointing at the public MinIO endpoint.

    The client (browser/app) uses this URL to upload directly to MinIO —
    the backend is never in the upload path.

    URL generation is pure HMAC — no network call is made.
    """
    return _get_public().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.MINIO_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
    )
