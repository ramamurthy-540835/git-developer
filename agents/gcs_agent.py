import os
from google.cloud import storage

def upload_to_gcs(file_path: str) -> str:
    """
    Uploads a file to Google Cloud Storage.

    Args:
        file_path (str): The local path to the file to upload.

    Returns:
        str: The gs:// URI of the uploaded file.
    """
    bucket_name = os.environ.get("GCS_BUCKET")
    if not bucket_name:
        raise ValueError("GCS_BUCKET environment variable not set.")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Determine the destination blob name within the 'agents/media/' prefix
    base_filename = os.path.basename(file_path)
    destination_blob_name = f"agents/media/{base_filename}"

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)

    return f"gs://{bucket_name}/{destination_blob_name}"
