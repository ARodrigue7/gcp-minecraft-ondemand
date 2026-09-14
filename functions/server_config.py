import json
from datetime import datetime, timezone
from googleapiclient.http import MediaInMemoryUpload
from googleapiclient.errors import HttpError
from config import PROJECT_ID, ZONE, INSTANCE_NAME, BACKUPS_BUCKET, logger
from gcp_client import compute, storage_service, get_cached_instance, invalidate_instance_cache

CONFIG_OBJECT_NAME = "server-config.json"
ALLOWED_TYPES = ["vanilla", "paper", "fabric", "modrinth", "curseforge"]
ALLOWED_MACHINE_TYPES = ["e2-medium", "e2-standard-2", "e2-standard-4"]

DEFAULT_CONFIG = {
    "type": "paper",
    "minecraft_version": "LATEST",
    "modpack_id": "",
    "machine_type": "e2-medium",
    "idle_timeout_seconds": 600,
    "world_stamp": "paper",
    "updated_at": ""
}

def get_server_config():
    """Retrieves server-config.json from GCS or returns defaults."""
    config = dict(DEFAULT_CONFIG)
    
    # Enrich with live instance machine type if available
    try:
        instance = get_cached_instance()
        mt = instance.get("machineType", "").split("/")[-1]
        if mt in ALLOWED_MACHINE_TYPES:
            config["machine_type"] = mt
    except Exception as e:
        logger.warning(f"Could not read live VM machine type: {e}")

    try:
        raw_bytes = storage_service.objects().get_media(
            bucket=BACKUPS_BUCKET,
            object=CONFIG_OBJECT_NAME
        ).execute()
        stored = json.loads(raw_bytes.decode("utf-8"))
        if isinstance(stored, dict):
            config.update(stored)
    except HttpError as e:
        if e.resp.status != 404:
            logger.error(f"Failed to read {CONFIG_OBJECT_NAME} from GCS: {e}")
    except Exception as e:
        logger.warning(f"Error reading server config from GCS, using defaults: {e}")

    return config

def save_server_config(new_data):
    """Validates and saves server configuration to GCS, applying machine resize if applicable."""
    current = get_server_config()
    
    server_type = str(new_data.get("type", current.get("type", "paper"))).lower().strip()
    if server_type not in ALLOWED_TYPES:
        raise ValueError(f"Invalid server type: {server_type}. Must be one of: {ALLOWED_TYPES}")
        
    machine_type = str(new_data.get("machine_type", current.get("machine_type", "e2-medium"))).lower().strip()
    if machine_type not in ALLOWED_MACHINE_TYPES:
        raise ValueError(f"Invalid machine type: {machine_type}. Must be one of: {ALLOWED_MACHINE_TYPES}")

    idle_timeout = int(new_data.get("idle_timeout_seconds", current.get("idle_timeout_seconds", 600)))
    if idle_timeout < 300 or idle_timeout > 7200:
        raise ValueError("idle_timeout_seconds must be between 300 and 7200")

    minecraft_version = str(new_data.get("minecraft_version", current.get("minecraft_version", "LATEST"))).strip()
    modpack_id = str(new_data.get("modpack_id", current.get("modpack_id", ""))).strip()
    world_stamp = str(new_data.get("world_stamp", current.get("world_stamp", server_type))).strip()

    # Apply machine resize if changed and VM is stopped
    try:
        instance = get_cached_instance()
        vm_status = instance.get("status", "UNKNOWN")
        curr_mt = instance.get("machineType", "").split("/")[-1]
        
        if machine_type != curr_mt:
            if vm_status == "TERMINATED":
                logger.info(f"Resizing VM from {curr_mt} to {machine_type}...")
                compute.instances().setMachineType(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=INSTANCE_NAME,
                    body={"machineType": f"zones/{ZONE}/machineTypes/{machine_type}"}
                ).execute()
                invalidate_instance_cache()
            else:
                logger.info(f"VM is currently {vm_status}. Machine type change to {machine_type} will apply on next stopped cycle.")
    except Exception as e:
        logger.error(f"Error updating instance machine type: {e}")

    updated_config = {
        "type": server_type,
        "minecraft_version": minecraft_version,
        "modpack_id": modpack_id,
        "machine_type": machine_type,
        "idle_timeout_seconds": idle_timeout,
        "world_stamp": world_stamp,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Write to GCS
    media = MediaInMemoryUpload(
        json.dumps(updated_config, indent=2).encode("utf-8"),
        mimetype="application/json"
    )
    storage_service.objects().insert(
        bucket=BACKUPS_BUCKET,
        name=CONFIG_OBJECT_NAME,
        media_body=media
    ).execute()
    
    logger.info(f"Successfully saved {CONFIG_OBJECT_NAME} to gs://{BACKUPS_BUCKET}/")
    return updated_config
