import os
import re
import urllib.parse
import urllib.request
from config import MODS_BUCKET, logger
from gcp_client import storage_service

ALLOWED_FOLDERS = ["mods", "plugins"]

def _validate_path(filename, folder):
    if folder not in ALLOWED_FOLDERS:
        raise ValueError(f"Invalid folder: {folder}. Must be one of {ALLOWED_FOLDERS}")
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError(f"Invalid filename: {filename}")
    clean_name = os.path.basename(filename).strip()
    if not (clean_name.endswith(".jar") or clean_name.endswith(".jar.disabled") or clean_name.endswith(".zip")):
        raise ValueError(f"File must be a .jar or .zip: {clean_name}")
    return clean_name

def list_mods(folder="mods"):
    """Lists installed mods or plugins from the GCS mods bucket."""
    if folder not in ALLOWED_FOLDERS:
        raise ValueError(f"Invalid folder: {folder}")
        
    prefix = f"{folder}/"
    logger.info(f"Listing mods from gs://{MODS_BUCKET}/{prefix}...")
    try:
        res = storage_service.objects().list(
            bucket=MODS_BUCKET,
            prefix=prefix
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to list mods in bucket {MODS_BUCKET}: {e}")
        return []

    items = []
    for obj in res.get("items", []):
        raw_name = obj.get("name", "")
        if raw_name == prefix or raw_name.endswith("/"):
            continue
        filename = raw_name[len(prefix):]
        enabled = not filename.endswith(".disabled")
        items.append({
            "filename": filename,
            "size": int(obj.get("size", 0)),
            "enabled": enabled,
            "updated": obj.get("updated", "")
        })
    return items

def create_upload_session(filename, folder="mods"):
    """Initiates a GCS resumable upload session and returns the session URI for direct browser PUT."""
    clean_name = _validate_path(filename, folder)
    full_path = f"{folder}/{clean_name}"
    
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    token = credentials.token

    url = f"https://storage.googleapis.com/upload/storage/v1/b/{MODS_BUCKET}/o?uploadType=resumable&name={urllib.parse.quote(full_path, safe='')}"
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "application/java-archive"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        session_uri = resp.headers.get("Location")
        if not session_uri:
            raise RuntimeError("GCS did not return an upload session Location header")
        logger.info(f"Minted GCS resumable upload URI for {full_path}")
        return {
            "upload_url": session_uri,
            "filename": clean_name,
            "folder": folder
        }

def toggle_mod(filename, folder="mods"):
    """Toggles a mod between active (.jar) and inactive (.jar.disabled) via GCS copy + delete."""
    clean_name = _validate_path(filename, folder)
    if clean_name.endswith(".disabled"):
        new_name = clean_name[:-9] # strip .disabled
    else:
        new_name = f"{clean_name}.disabled"

    src_path = f"{folder}/{clean_name}"
    dst_path = f"{folder}/{new_name}"

    logger.info(f"Toggling mod: {src_path} -> {dst_path}")
    storage_service.objects().copy(
        sourceBucket=MODS_BUCKET,
        sourceObject=src_path,
        destinationBucket=MODS_BUCKET,
        destinationObject=dst_path,
        body={}
    ).execute()

    storage_service.objects().delete(
        bucket=MODS_BUCKET,
        object=src_path
    ).execute()

    return {
        "filename": new_name,
        "enabled": not new_name.endswith(".disabled"),
        "folder": folder
    }

def delete_mod(filename, folder="mods"):
    """Deletes a mod file from the GCS mods bucket."""
    clean_name = _validate_path(filename, folder)
    path = f"{folder}/{clean_name}"
    logger.info(f"Deleting mod gs://{MODS_BUCKET}/{path}...")
    storage_service.objects().delete(
        bucket=MODS_BUCKET,
        object=path
    ).execute()
    return {"deleted": True, "filename": clean_name, "folder": folder}
