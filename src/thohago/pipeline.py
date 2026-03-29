from __future__ import annotations

from pathlib import Path

from thohago.artifacts import append_chat_log, copy_file, create_session_artifacts, write_json, write_text
from thohago.content import BlogComposer
from thohago.interview_engine import HeuristicMultimodalInterviewEngine, TURN1_QUESTION
from thohago.models import SessionRunResult, ShopConfig, TranscriptArtifact
from thohago.publish import MissingCredentialNaverPublisher, MockNaverPublisher
from thohago.transcription import SidecarTranscriptProvider


class Phase1ReplayPipeline:
    def __init__(self, engine=None, transcriber=None) -> None:
        self.engine = engine or HeuristicMultimodalInterviewEngine()
        self.transcriber = transcriber or SidecarTranscriptProvider()
        self.blog_composer = BlogComposer()

    def run(self, artifact_root: Path, shop: ShopConfig, session_key: str) -> SessionRunResult:
        if session_key not in shop.sample_sessions:
            raise KeyError(f"Shop {shop.shop_id} has no sample session '{session_key}'")

        sample_session = shop.sample_sessions[session_key]
        artifacts = create_session_artifacts(artifact_root, shop, session_key)

        photos = sorted(sample_session.image_dir.glob("*.jpg"))
        videos = self._select_source_videos(sample_session.video_dir)
        for source_path in [*photos, *videos, *sample_session.turn_transcript_files]:
            copy_file(source_path, artifacts.raw_dir / source_path.name)
        for path in photos:
            self.log_chat_event(
                artifacts=artifacts,
                sender="user",
                message_type="photo",
                file_paths=[str(path)],
            )
        for path in videos:
            self.log_chat_event(
                artifacts=artifacts,
                sender="user",
                message_type="video",
                file_paths=[str(path)],
            )

        preflight, photo_assets, video_assets, media_preflight_path = self.prepare_media_artifacts(
            artifacts=artifacts,
            shop=shop,
            photos=photos,
            videos=videos,
        )

        write_text(artifacts.prompts_dir / "turn1_question.txt", TURN1_QUESTION)
        self.log_chat_event(
            artifacts=artifacts,
            sender="bot",
            message_type="text",
            text=TURN1_QUESTION,
            metadata={"turn_index": 1},
        )

        transcript_artifacts: list[TranscriptArtifact] = []
        turn1_transcript = self.transcriber.load_transcript(sample_session.turn_transcript_files[0])
        transcript_artifacts.append(
            self.write_transcript_artifact(
                artifacts=artifacts,
                turn_index=1,
                source_path=sample_session.turn_transcript_files[0],
                transcript_text=turn1_transcript,
            )
        )
        self.log_chat_event(
            artifacts=artifacts,
            sender="user",
            message_type="text",
            text=turn1_transcript,
            metadata={"turn_index": 1},
        )

        turn2_planner, turn2_planner_path = self.build_turn_planner(
            artifacts=artifacts,
            turn_index=2,
            transcripts=[turn1_transcript],
            preflight=preflight,
        )
        self.log_chat_event(
            artifacts=artifacts,
            sender="bot",
            message_type="text",
            text=turn2_planner.next_question,
            metadata={"turn_index": 2, "planner_path": str(turn2_planner_path)},
        )

        turn2_transcript = self.transcriber.load_transcript(sample_session.turn_transcript_files[1])
        transcript_artifacts.append(
            self.write_transcript_artifact(
                artifacts=artifacts,
                turn_index=2,
                source_path=sample_session.turn_transcript_files[1],
                transcript_text=turn2_transcript,
            )
        )
        self.log_chat_event(
            artifacts=artifacts,
            sender="user",
            message_type="text",
            text=turn2_transcript,
            metadata={"turn_index": 2},
        )

        turn3_planner, turn3_planner_path = self.build_turn_planner(
            artifacts=artifacts,
            turn_index=3,
            transcripts=[turn1_transcript, turn2_transcript],
            preflight=preflight,
        )
        self.log_chat_event(
            artifacts=artifacts,
            sender="bot",
            message_type="text",
            text=turn3_planner.next_question,
            metadata={"turn_index": 3, "planner_path": str(turn3_planner_path)},
        )

        turn3_transcript = self.transcriber.load_transcript(sample_session.turn_transcript_files[2])
        transcript_artifacts.append(
            self.write_transcript_artifact(
                artifacts=artifacts,
                turn_index=3,
                source_path=sample_session.turn_transcript_files[2],
                transcript_text=turn3_transcript,
            )
        )
        self.log_chat_event(
            artifacts=artifacts,
            sender="user",
            message_type="text",
            text=turn3_transcript,
            metadata={"turn_index": 3},
        )

        content_bundle_path, blog_article_path, publish_result_path = self.finalize_session(
            artifacts=artifacts,
            shop=shop,
            photo_assets=photo_assets,
            video_assets=video_assets,
            preflight=preflight,
            transcript_artifacts=transcript_artifacts,
            turn2_planner=turn2_planner,
            turn3_planner=turn3_planner,
        )

        session_metadata = {
            "shop_id": shop.shop_id,
            "session_key": session_key,
            "session_id": artifacts.session_id,
            "artifact_dir": str(artifacts.artifact_dir),
            "chat_log_path": str(artifacts.chat_log_path),
            "raw_dir": str(artifacts.raw_dir),
            "generated_dir": str(artifacts.generated_dir),
            "published_dir": str(artifacts.published_dir),
        }
        write_json(artifacts.artifact_dir / "session_metadata.json", session_metadata)

        return SessionRunResult(
            artifacts=artifacts,
            media_preflight_path=media_preflight_path,
            turn2_planner_path=turn2_planner_path,
            turn3_planner_path=turn3_planner_path,
            content_bundle_path=content_bundle_path,
            blog_article_path=blog_article_path,
            publish_result_path=publish_result_path,
        )

    def prepare_media_artifacts(
        self,
        artifacts,
        shop: ShopConfig,
        photos: list[Path],
        videos: list[Path],
    ) -> tuple[dict, list, list, Path]:
        preflight, photo_assets, video_assets = self.engine.build_preflight(shop, photos, videos)
        media_preflight_path = artifacts.generated_dir / "media_preflight.json"
        write_json(media_preflight_path, preflight)
        return preflight, photo_assets, video_assets, media_preflight_path

    def log_chat_event(
        self,
        *,
        artifacts,
        sender: str,
        message_type: str,
        text: str | None = None,
        file_paths: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        append_chat_log(
            artifacts.chat_log_path,
            session_id=artifacts.session_id,
            shop_id=artifacts.shop.shop_id,
            sender=sender,
            message_type=message_type,
            text=text,
            file_paths=file_paths,
            metadata=metadata,
        )

    def write_transcript_artifact(
        self,
        artifacts,
        turn_index: int,
        source_path: Path,
        transcript_text: str,
    ) -> TranscriptArtifact:
        artifact = TranscriptArtifact(turn_index=turn_index, source_path=source_path, transcript_text=transcript_text)
        write_text(artifacts.transcripts_dir / f"turn{turn_index}_transcript.txt", transcript_text)
        write_json(artifacts.transcripts_dir / f"turn{turn_index}_transcript.json", artifact.to_dict())
        return artifact

    def build_turn_planner(
        self,
        artifacts,
        turn_index: int,
        transcripts: list[str],
        preflight: dict,
    ):
        planner = self.engine.plan_turn(turn_index, transcripts, preflight)
        planner_path = artifacts.prompts_dir / f"turn{turn_index}_planner.json"
        write_json(planner_path, self.engine.build_turn_question_artifact(planner))
        write_text(artifacts.prompts_dir / f"turn{turn_index}_question.txt", planner.next_question)
        return planner, planner_path

    def finalize_session(
        self,
        artifacts,
        shop: ShopConfig,
        photo_assets,
        video_assets,
        preflight: dict,
        transcript_artifacts: list[TranscriptArtifact],
        turn2_planner,
        turn3_planner,
    ) -> tuple[Path, Path, Path]:
        content_bundle = {
            "shop": {
                "shop_id": shop.shop_id,
                "display_name": shop.display_name,
                "publish_targets": shop.publish.targets,
            },
            "session": {
                "session_key": artifacts.session_key,
                "session_id": artifacts.session_id,
                "artifact_dir": str(artifacts.artifact_dir),
            },
            "photos": [asset.to_dict() for asset in photo_assets],
            "videos": [asset.to_dict() for asset in video_assets],
            "media_preflight": preflight,
            "interview": {
                "turn1_question": TURN1_QUESTION,
                "turn2_question": turn2_planner.next_question,
                "turn3_question": turn3_planner.next_question,
                "turn1_transcript": transcript_artifacts[0].transcript_text,
                "turn2_transcript": transcript_artifacts[1].transcript_text,
                "turn3_transcript": transcript_artifacts[2].transcript_text,
                "main_angle": turn2_planner.main_angle,
                "covered_elements": turn3_planner.covered_elements,
                "missing_elements": turn3_planner.missing_elements,
            },
            "structure_mode": preflight["structure_mode"],
            "experience_sequence": preflight["experience_sequence"],
        }
        content_bundle_path = artifacts.generated_dir / "content_bundle.json"
        write_json(content_bundle_path, content_bundle)

        blog_article = self.blog_composer.compose(
            shop=shop,
            photos=photo_assets,
            transcripts=transcript_artifacts,
            turn2_planner=turn2_planner,
            turn3_planner=turn3_planner,
            structure_mode=preflight["structure_mode"],
        )
        blog_article_path = artifacts.generated_dir / "naver_blog_article.md"
        write_text(blog_article_path, blog_article)

        publisher = MockNaverPublisher() if shop.publish.provider == "mock_naver" else MissingCredentialNaverPublisher()
        publish_result = publisher.publish(blog_article_path, artifacts.published_dir, shop.shop_id, artifacts.session_id)
        publish_result_path = artifacts.published_dir / "publish_result.json"
        write_json(publish_result_path, publish_result)
        self.log_chat_event(
            artifacts=artifacts,
            sender="bot",
            message_type="text",
            text=(
                "인터뷰와 콘텐츠 생성이 완료됐습니다.\n"
                f"- content_bundle: {content_bundle_path.name}\n"
                f"- blog_article: {blog_article_path.name}\n"
                f"- publish_status: {publish_result['status']}\n"
                f"- publish_url: {publish_result.get('published_url')}"
            ),
            metadata={"stage": "completed"},
        )
        return content_bundle_path, blog_article_path, publish_result_path

    def _select_source_videos(self, video_dir: Path) -> list[Path]:
        candidates = sorted(video_dir.glob("KakaoTalk_*.mp4"))
        filtered = [path for path in candidates if "_reels_edit" not in path.name]
        return filtered
