"""
cloud_sync.py
Uploads mission logs and reports to a remote cloud server (S3 or WebDAV).
"""
import os
import requests

def upload_file(filepath, url, username=None, password=None):
    with open(filepath, 'rb') as f:
        files = {'file': (os.path.basename(filepath), f)}
        auth = (username, password) if username and password else None
        resp = requests.post(url, files=files, auth=auth)
        if resp.status_code == 200:
            print(f"Uploaded {filepath} to {url}")
        else:
            print(f"Failed to upload {filepath}: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python cloud_sync.py <file> <url> [username] [password]")
    else:
        upload_file(sys.argv[1], sys.argv[2], *(sys.argv[3:5]))
