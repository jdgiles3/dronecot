"""SeaweedFS distributed storage service."""

import json
import aiohttp
from typing import Dict, Any, Optional, List, BinaryIO
from datetime import datetime
import uuid
import os

import sys
sys.path.append('..')
from config import settings


class SeaweedFSService:
    """SeaweedFS service for distributed file storage."""
    
    def __init__(self):
        self.master_url = settings.SEAWEEDFS_MASTER
        self.filer_url = settings.SEAWEEDFS_FILER
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()
        
        # Test connection
        try:
            async with self.session.get(f"{self.master_url}/cluster/status") as resp:
                if resp.status == 200:
                    print(f"SeaweedFS connected: {self.master_url}")
                else:
                    print(f"SeaweedFS connection warning: status {resp.status}")
        except Exception as e:
            print(f"SeaweedFS connection error: {e}")
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            print("SeaweedFS disconnected")
    
    # ==================== FILE OPERATIONS ====================
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        path: str = "/",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload a file to SeaweedFS."""
        # Get file ID from master
        async with self.session.get(f"{self.master_url}/dir/assign") as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get file ID: {resp.status}")
            assign_data = await resp.json()
        
        fid = assign_data["fid"]
        volume_url = f"http://{assign_data['url']}"
        
        # Upload to volume server
        form = aiohttp.FormData()
        form.add_field(
            'file',
            file_content,
            filename=filename,
            content_type='application/octet-stream'
        )
        
        async with self.session.post(f"{volume_url}/{fid}", data=form) as resp:
            if resp.status != 201:
                raise Exception(f"Upload failed: {resp.status}")
            upload_result = await resp.json()
        
        # Store metadata in filer
        full_path = os.path.join(path, filename)
        file_metadata = {
            "fid": fid,
            "filename": filename,
            "path": full_path,
            "size": upload_result.get("size", len(file_content)),
            "uploaded_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Create entry in filer
        await self._create_filer_entry(full_path, fid, file_metadata)
        
        return {
            "fid": fid,
            "path": full_path,
            "size": file_metadata["size"],
            "url": f"{volume_url}/{fid}"
        }
    
    async def upload_from_path(
        self,
        local_path: str,
        remote_path: str = "/",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload a file from local path."""
        filename = os.path.basename(local_path)
        
        with open(local_path, 'rb') as f:
            content = f.read()
        
        return await self.upload_file(content, filename, remote_path, metadata)
    
    async def download_file(self, fid: str) -> bytes:
        """Download a file by FID."""
        # Lookup volume location
        async with self.session.get(
            f"{self.master_url}/dir/lookup",
            params={"volumeId": fid.split(",")[0]}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Lookup failed: {resp.status}")
            lookup_data = await resp.json()
        
        volume_url = f"http://{lookup_data['locations'][0]['url']}"
        
        # Download from volume
        async with self.session.get(f"{volume_url}/{fid}") as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")
            return await resp.read()
    
    async def download_by_path(self, path: str) -> bytes:
        """Download a file by path from filer."""
        async with self.session.get(f"{self.filer_url}{path}") as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")
            return await resp.read()
    
    async def delete_file(self, fid: str):
        """Delete a file by FID."""
        # Lookup volume location
        async with self.session.get(
            f"{self.master_url}/dir/lookup",
            params={"volumeId": fid.split(",")[0]}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Lookup failed: {resp.status}")
            lookup_data = await resp.json()
        
        volume_url = f"http://{lookup_data['locations'][0]['url']}"
        
        # Delete from volume
        async with self.session.delete(f"{volume_url}/{fid}") as resp:
            if resp.status not in [200, 202, 204]:
                raise Exception(f"Delete failed: {resp.status}")
    
    async def delete_by_path(self, path: str):
        """Delete a file by path from filer."""
        async with self.session.delete(f"{self.filer_url}{path}") as resp:
            if resp.status not in [200, 202, 204]:
                raise Exception(f"Delete failed: {resp.status}")
    
    # ==================== DIRECTORY OPERATIONS ====================
    
    async def list_directory(
        self,
        path: str = "/",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List files in a directory."""
        async with self.session.get(
            f"{self.filer_url}{path}",
            params={"limit": limit},
            headers={"Accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("Entries", [])
    
    async def create_directory(self, path: str):
        """Create a directory."""
        async with self.session.post(
            f"{self.filer_url}{path}/",
            headers={"Content-Type": "application/json"}
        ) as resp:
            if resp.status not in [200, 201]:
                raise Exception(f"Create directory failed: {resp.status}")
    
    async def _create_filer_entry(
        self,
        path: str,
        fid: str,
        metadata: Dict[str, Any]
    ):
        """Create a filer entry for a file."""
        # The filer automatically creates entries when files are uploaded
        # This is for additional metadata storage
        pass
    
    # ==================== METADATA OPERATIONS ====================
    
    async def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file information from filer."""
        async with self.session.get(
            f"{self.filer_url}{path}",
            params={"metadata": "true"},
            headers={"Accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    
    async def set_file_metadata(
        self,
        path: str,
        metadata: Dict[str, Any]
    ):
        """Set custom metadata for a file."""
        # SeaweedFS stores metadata as extended attributes
        headers = {
            f"Seaweed-{k}": str(v) for k, v in metadata.items()
        }
        
        async with self.session.post(
            f"{self.filer_url}{path}",
            headers=headers
        ) as resp:
            if resp.status not in [200, 201]:
                raise Exception(f"Set metadata failed: {resp.status}")
    
    # ==================== BATCH OPERATIONS ====================
    
    async def upload_batch(
        self,
        files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Upload multiple files.
        
        files: List of dicts with 'content', 'filename', 'path', 'metadata'
        """
        results = []
        for file_info in files:
            try:
                result = await self.upload_file(
                    file_content=file_info["content"],
                    filename=file_info["filename"],
                    path=file_info.get("path", "/"),
                    metadata=file_info.get("metadata")
                )
                results.append({"success": True, **result})
            except Exception as e:
                results.append({
                    "success": False,
                    "filename": file_info["filename"],
                    "error": str(e)
                })
        return results
    
    # ==================== STATS ====================
    
    async def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status."""
        async with self.session.get(f"{self.master_url}/cluster/status") as resp:
            if resp.status != 200:
                return {"error": f"Status {resp.status}"}
            return await resp.json()
    
    async def get_volume_status(self) -> Dict[str, Any]:
        """Get volume server status."""
        async with self.session.get(f"{self.master_url}/vol/status") as resp:
            if resp.status != 200:
                return {"error": f"Status {resp.status}"}
            return await resp.json()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get SeaweedFS statistics."""
        cluster = await self.get_cluster_status()
        volumes = await self.get_volume_status()
        
        return {
            "master_url": self.master_url,
            "filer_url": self.filer_url,
            "cluster": cluster,
            "volumes": volumes
        }
