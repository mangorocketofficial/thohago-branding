from __future__ import annotations

from pathlib import Path

from thohago.artifacts import copy_file


class MockNaverPublisher:
    def publish(self, blog_article_path: Path, published_dir: Path, shop_id: str, session_id: str) -> dict:
        destination = published_dir / "naver_blog_post.md"
        copy_file(blog_article_path, destination)
        return {
            "provider": "mock_naver",
            "status": "mock_published",
            "published_url": f"mock://naver/{shop_id}/{session_id}",
            "published_path": str(destination),
        }


class MissingCredentialNaverPublisher:
    def publish(self, blog_article_path: Path, published_dir: Path, shop_id: str, session_id: str) -> dict:
        return {
            "provider": "naver_live",
            "status": "missing_credentials",
            "published_url": None,
            "published_path": None,
            "error": "Live Naver credentials/cookies are not configured.",
            "source_article_path": str(blog_article_path),
        }

