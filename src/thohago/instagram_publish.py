"""Instagram Graph API publisher — carousel & single-image posting.

Flow
----
1. Upload each photo to Facebook Page as *unpublished* (gives a public CDN URL).
2. Create Instagram media containers (carousel items) referencing those URLs.
3. Create a carousel container that groups the items.
4. Publish the carousel.

Env vars consumed (via AppConfig):
    GRAPH_META_ACCESS_TOKEN
    INSTAGRAM_BUSINESS_ACCOUNT_ID
    FACEBOOK_PAGE_ID
    INSTAGRAM_GRAPH_VERSION   (default v23.0)
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


class InstagramPublishError(Exception):
    pass


class InstagramGraphPublisher:
    """Publish carousel (or single-image) posts via Instagram Graph API."""

    def __init__(
        self,
        access_token: str,
        ig_user_id: str,
        fb_page_id: str,
        graph_version: str = "v23.0",
    ) -> None:
        self.access_token = access_token
        self.ig_user_id = ig_user_id
        self.fb_page_id = fb_page_id
        self.graph_version = graph_version
        self.base = f"{_GRAPH_BASE}/{graph_version}"
        self._page_access_token: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def publish_carousel(
        self,
        image_paths: list[Path],
        caption: str,
    ) -> dict[str, Any]:
        """Upload local images as an Instagram carousel post.

        Returns a dict with ``ig_media_id``, ``permalink``, and per-image
        details under ``items``.
        """
        if len(image_paths) < 2:
            raise InstagramPublishError("Carousel requires at least 2 images.")
        if len(image_paths) > 10:
            raise InstagramPublishError("Carousel allows at most 10 images.")

        # Step 1 — upload images to Facebook CDN (unpublished page photos)
        image_urls = []
        for path in image_paths:
            url = self._upload_to_facebook_cdn(path)
            image_urls.append(url)

        # Step 2 — create individual carousel-item containers
        item_ids: list[str] = []
        for url in image_urls:
            container_id = self._create_item_container(url)
            item_ids.append(container_id)

        # Step 3 — create the carousel container
        carousel_id = self._create_carousel_container(item_ids, caption)

        # Step 4 — wait for processing then publish
        self._wait_for_container(carousel_id)
        media_id = self._publish_container(carousel_id)

        # Step 5 — fetch permalink
        permalink = self._get_permalink(media_id)

        return {
            "provider": "instagram_graph",
            "status": "published",
            "ig_media_id": media_id,
            "permalink": permalink,
            "caption": caption,
            "image_count": len(image_paths),
        }

    def publish_single_image(
        self,
        image_path: Path,
        caption: str,
    ) -> dict[str, Any]:
        """Upload a single image post to Instagram."""
        image_url = self._upload_to_facebook_cdn(image_path)
        container_id = self._create_single_container(image_url, caption)
        self._wait_for_container(container_id)
        media_id = self._publish_container(container_id)
        permalink = self._get_permalink(media_id)
        return {
            "provider": "instagram_graph",
            "status": "published",
            "ig_media_id": media_id,
            "permalink": permalink,
            "caption": caption,
        }

    def validate_access(self) -> None:
        """Fail fast when the token/account cannot publish Instagram content."""
        page_token = self._resolve_page_access_token()
        self._execute(Request(f"{self.base}/{self.fb_page_id}?fields=id,name&access_token={page_token}"))
        if not self._has_user_permission("pages_manage_posts"):
            raise InstagramPublishError(
                "Instagram publishing is not fully authorized for this implementation. "
                "The current login is missing pages_manage_posts. "
                "This project first uploads local images to the Facebook Page as unpublished photos "
                "to obtain public image URLs, so pages_manage_posts is required in addition to "
                "instagram_content_publish."
            )
        try:
            self._execute(
                Request(
                    f"{self.base}/{self.ig_user_id}/content_publishing_limit"
                    f"?fields=config,quota_usage&access_token={page_token}"
                )
            )
        except InstagramPublishError as exc:
            raise InstagramPublishError(
                "Instagram publishing is not authorized. "
                "Check that the token has instagram_content_publish permission "
                "and that the Instagram business account is correctly linked to the Facebook Page. "
                f"Details: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _upload_to_facebook_cdn(self, image_path: Path) -> str:
        """Upload an image to a Facebook Page as unpublished and return the CDN URL."""
        url = f"{self.base}/{self.fb_page_id}/photos"
        page_token = self._resolve_page_access_token()
        image_data = image_path.read_bytes()

        boundary = "----ThohagoBoundary"
        body = BytesIO()

        # access_token field
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="access_token"\r\n\r\n')
        body.write(f"{page_token}\r\n".encode())

        # published=false
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="published"\r\n\r\n')
        body.write(b"false\r\n")

        # temporary=true (auto-cleanup)
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

        # Fetch the CDN URL from the uploaded photo
        photo_url = f"{self.base}/{photo_id}?fields=images&access_token={page_token}"
        photo_data = self._execute(Request(photo_url))
        images = photo_data.get("images", [])
        if not images:
            raise InstagramPublishError(f"No CDN URL returned for uploaded photo {photo_id}")
        # First image in the list is the largest
        return images[0]["source"]

    def _resolve_page_access_token(self) -> str:
        if self._page_access_token:
            return self._page_access_token
        try:
            data = self._execute(Request(f"{self.base}/me/accounts?access_token={self.access_token}"))
        except Exception:
            self._page_access_token = self.access_token
            return self._page_access_token
        for page in data.get("data", []):
            if page.get("id") == self.fb_page_id and page.get("access_token"):
                self._page_access_token = page["access_token"]
                return self._page_access_token
        self._page_access_token = self.access_token
        return self._page_access_token

    def _has_user_permission(self, permission: str) -> bool:
        try:
            data = self._execute(Request(f"{self.base}/me/permissions?access_token={self.access_token}"))
        except Exception:
            return True
        for item in data.get("data", []):
            if item.get("permission") == permission:
                return item.get("status") == "granted"
        return False

    def _create_item_container(self, image_url: str) -> str:
        """Create an individual carousel-item container."""
        url = f"{self.base}/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _create_carousel_container(self, children_ids: list[str], caption: str) -> str:
        """Create the parent carousel container."""
        url = f"{self.base}/{self.ig_user_id}/media"
        params = {
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(children_ids),
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _create_single_container(self, image_url: str, caption: str) -> str:
        url = f"{self.base}/{self.ig_user_id}/media"
        params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        result = self._post_form(url, params)
        return result["id"]

    def _wait_for_container(self, container_id: str, timeout: int = 60) -> None:
        """Poll until the container is ready for publishing."""
        url = f"{self.base}/{container_id}?fields=status_code&access_token={self.access_token}"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self._execute(Request(url))
            status = result.get("status_code", "")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise InstagramPublishError(f"Container {container_id} processing failed: {result}")
            time.sleep(2)
        raise InstagramPublishError(f"Container {container_id} processing timed out after {timeout}s")

    def _publish_container(self, container_id: str) -> str:
        """Publish a ready container and return the media ID."""
        url = f"{self.base}/{self.ig_user_id}/media_publish"
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
    # HTTP helpers (urllib only — no external deps)
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
            raise InstagramPublishError(
                f"Graph API error {exc.code}: {error_body}"
            ) from exc
