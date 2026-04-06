"""Threads API publisher — text, single-image, and carousel posting.

Flow (carousel)
---------------
1. Upload each photo to Facebook Page as *unpublished* (reuses Instagram CDN trick).
2. Create Threads item containers for each image.
3. Create a carousel container grouping the items.
4. Publish the carousel.

Env vars consumed (via AppConfig):
    THREADS_ACCESS_TOKEN
    THREADS_USER_ID   (falls back to INSTAGRAM_BUSINESS_ACCOUNT_ID)
    FACEBOOK_PAGE_ID
    INSTAGRAM_GRAPH_VERSION   (shared — Threads uses the same Graph versioning)
"""
from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_GRAPH_BASE = "https://graph.facebook.com"


class ThreadsPublishError(Exception):
    pass


class ThreadsPublisher:
    """Publish text, single-image, or carousel posts to Threads."""

    def __init__(
        self,
        access_token: str,
        threads_user_id: str,
        fb_page_id: str,
        fb_page_upload_token: str | None = None,
        graph_version: str = "v23.0",
    ) -> None:
        self.access_token = access_token
        self.threads_user_id = threads_user_id
        self.fb_page_id = fb_page_id
        self.fb_page_upload_token = fb_page_upload_token or access_token
        self.graph_version = graph_version
        self.base = f"{_GRAPH_BASE}/{graph_version}"
        self._page_access_token: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish_text(self, text: str) -> dict[str, Any]:
        """Publish a text-only thread."""
        container_id = self._create_text_container(text)
        self._wait_for_container(container_id)
        media_id = self._publish_container(container_id)
        permalink = self._get_permalink(media_id)
        return {
            "provider": "threads",
            "status": "published",
            "threads_media_id": media_id,
            "permalink": permalink,
            "text": text,
        }

    def publish_single_image(
        self,
        image_path: Path,
        text: str,
    ) -> dict[str, Any]:
        """Publish a single image thread."""
        image_url = self._upload_to_facebook_cdn(image_path)
        container_id = self._create_image_container(image_url, text)
        self._wait_for_container(container_id)
        media_id = self._publish_container(container_id)
        permalink = self._get_permalink(media_id)
        return {
            "provider": "threads",
            "status": "published",
            "threads_media_id": media_id,
            "permalink": permalink,
            "text": text,
        }

    def publish_carousel(
        self,
        image_paths: list[Path],
        text: str,
    ) -> dict[str, Any]:
        """Upload local images as a Threads carousel post."""
        if len(image_paths) < 2:
            raise ThreadsPublishError("Carousel requires at least 2 images.")
        if len(image_paths) > 10:
            raise ThreadsPublishError("Carousel allows at most 10 images.")

        # Step 1 — upload images to Facebook CDN
        image_urls = [self._upload_to_facebook_cdn(p) for p in image_paths]

        # Step 2 — create individual item containers
        item_ids = [self._create_carousel_item(url) for url in image_urls]

        # Step 3 — create carousel container
        carousel_id = self._create_carousel_container(item_ids, text)

        # Step 4 — wait and publish
        self._wait_for_container(carousel_id)
        media_id = self._publish_container(carousel_id)
        permalink = self._get_permalink(media_id)

        return {
            "provider": "threads",
            "status": "published",
            "threads_media_id": media_id,
            "permalink": permalink,
            "text": text,
            "image_count": len(image_paths),
        }

    def validate_access(self) -> None:
        """Fail fast when the token/account cannot publish Threads content."""
        try:
            self._execute(
                Request(
                    f"{self.base}/{self.threads_user_id}"
                    f"?fields=id,username&access_token={self.access_token}"
                )
            )
        except ThreadsPublishError as exc:
            raise ThreadsPublishError(
                "Threads publishing is not authorized. "
                "Check that THREADS_ACCESS_TOKEN is a valid Threads Graph token "
                "and that THREADS_USER_ID matches the connected Threads account. "
                f"Details: {exc}"
            ) from exc
        page_token = self._resolve_page_access_token()
        self._execute(Request(f"{self.base}/{self.fb_page_id}?fields=id,name&access_token={page_token}"))
        if not self._has_page_upload_permission("pages_manage_posts"):
            raise ThreadsPublishError(
                "Threads publishing is not fully authorized for this implementation. "
                "The current Facebook/Page upload login is missing pages_manage_posts. "
                "This project first uploads local images to the Facebook Page as unpublished photos "
                "to obtain public image URLs before creating Threads media containers."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _upload_to_facebook_cdn(self, image_path: Path) -> str:
        """Upload an image to Facebook Page as unpublished → return CDN URL."""
        url = f"{self.base}/{self.fb_page_id}/photos"
        page_token = self._resolve_page_access_token()
        image_data = image_path.read_bytes()

        boundary = "----ThohagoBoundary"
        body = BytesIO()

        # access_token
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
        body.write(f"{page_token}\r\n".encode())

        # published=false
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="published"\r\n\r\n')
        body.write(b"false\r\n")

        # temporary=true
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="temporary"\r\n\r\n')
        body.write(b"true\r\n")

        # image binary
        body.write(f"--{boundary}\r\n".encode())
        body.write(
            f'Content-Disposition: form-data; name="source"; filename="{image_path.name}"\r\n'.encode()
        )
        body.write(b"Content-Type: image/jpeg\r\n\r\n")
        body.write(image_data)
        body.write(b"\r\n")

        body.write(f"--{boundary}--\r\n".encode())
        raw_body = body.getvalue()

        request = Request(
            url,
            data=raw_body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        result = self._execute(request)
        photo_id = result["id"]

        # Fetch CDN URL
        photo_url = f"{self.base}/{photo_id}?fields=images&access_token={page_token}"
        photo_data = self._execute(Request(photo_url))
        images = photo_data.get("images", [])
        if not images:
            raise ThreadsPublishError(f"No CDN URL returned for photo {photo_id}")
        return images[0]["source"]

    def _resolve_page_access_token(self) -> str:
        if self._page_access_token:
            return self._page_access_token
        try:
            data = self._execute(Request(f"{self.base}/me/accounts?access_token={self.fb_page_upload_token}"))
        except Exception:
            self._page_access_token = self.fb_page_upload_token
            return self._page_access_token
        for page in data.get("data", []):
            if page.get("id") == self.fb_page_id and page.get("access_token"):
                self._page_access_token = page["access_token"]
                return self._page_access_token
        self._page_access_token = self.fb_page_upload_token
        return self._page_access_token

    def _has_page_upload_permission(self, permission: str) -> bool:
        try:
            data = self._execute(Request(f"{self.base}/me/permissions?access_token={self.fb_page_upload_token}"))
        except Exception:
            return True
        for item in data.get("data", []):
            if item.get("permission") == permission:
                return item.get("status") == "granted"
        return False

    def _create_text_container(self, text: str) -> str:
        url = f"{self.base}/{self.threads_user_id}/threads"
        params = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _create_image_container(self, image_url: str, text: str) -> str:
        url = f"{self.base}/{self.threads_user_id}/threads"
        params = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text,
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _create_carousel_item(self, image_url: str) -> str:
        """Create a single carousel item container."""
        url = f"{self.base}/{self.threads_user_id}/threads"
        params = {
            "media_type": "IMAGE",
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _create_carousel_container(self, children_ids: list[str], text: str) -> str:
        url = f"{self.base}/{self.threads_user_id}/threads"
        params = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "text": text,
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _wait_for_container(self, container_id: str, timeout: int = 60) -> None:
        """Poll until the container is ready for publishing."""
        url = f"{self.base}/{container_id}?fields=status&access_token={self.access_token}"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self._execute(Request(url))
            status = result.get("status", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ThreadsPublishError(f"Container {container_id} failed: {result}")
            time.sleep(2)
        raise ThreadsPublishError(f"Container {container_id} timed out after {timeout}s")

    def _publish_container(self, container_id: str) -> str:
        url = f"{self.base}/{self.threads_user_id}/threads_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _get_permalink(self, media_id: str) -> str | None:
        url = f"{self.base}/{media_id}?fields=permalink&access_token={self.access_token}"
        try:
            result = self._execute(Request(url))
            return result.get("permalink")
        except Exception:
            return None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _post_form(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        data = urlencode(params).encode("utf-8")
        request = Request(url, data=data, method="POST")
        return self._execute(request)

    def _execute(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise ThreadsPublishError(
                f"Threads API error {exc.code}: {error_body}"
            ) from exc
