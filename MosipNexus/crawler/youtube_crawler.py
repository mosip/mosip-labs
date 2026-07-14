"""
YouTube crawler for MOSIP videos.
"""
import sys
import json
from pathlib import Path
from googleapiclient.discovery import build
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    YOUTUBE_API_KEY,
    YOUTUBE_CHANNEL_HANDLE,
    YOUTUBE_FILE,
)


def get_youtube_client():
    """Create a YouTube Data API client."""
    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY,
    )


def get_channel_id(youtube):
    """Resolve the channel ID from the handle."""
    response = youtube.channels().list(
        part="id",
        forHandle=YOUTUBE_CHANNEL_HANDLE,
    ).execute()

    items = response.get("items", [])

    if not items:
        raise RuntimeError(
            f"Channel not found: @{YOUTUBE_CHANNEL_HANDLE}"
        )

    return items[0]["id"]
def get_uploads_playlist_id(youtube, channel_id):
    """Return the uploads playlist ID for a channel."""
    response = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()

    items = response.get("items", [])

    if not items:
        raise RuntimeError("Channel not found.")

    return (
        items[0]["contentDetails"]
        ["relatedPlaylists"]
        ["uploads"]
    )
def get_all_videos(youtube, playlist_id):
    """Fetch all public videos from the uploads playlist."""

    videos = []
    next_page_token = None

    while True:
        response = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]

            videos.append(
                {
                    "video_id": snippet["resourceId"]["videoId"],
                    "title": snippet["title"],
                    "published_at": snippet["publishedAt"],
                }
            )

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    return videos
from youtube_transcript_api import YouTubeTranscriptApi

def fetch_transcript(video_id: str):
    """
    Fetch transcript for a video.

    Preference:
      1. Manual English captions
      2. Auto-generated English
      3. Any available language

    Returns:
        list[FetchedTranscriptSnippet] | None
    """
    api = YouTubeTranscriptApi()

    try:
        return api.fetch(
            video_id,
            languages=["en"],
        )
    except Exception:
        pass

    try:
        return api.fetch(video_id)
    except Exception:
        return None
def transcript_to_segments(transcript):
    """Convert transcript snippets into plain dictionaries."""
    segments = []

    for snippet in transcript:
        segments.append(
            {
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            }
        )

    return segments   
def build_video_document(video: dict):
    """
    Build one structured document for a YouTube video.
    """

    transcript = fetch_transcript(video["video_id"])

    if transcript is None:
        print(f"WARN: no transcript for {video['title']} ({video['video_id']})")
        return None

    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "published_at": video["published_at"],
        "channel_name": "MOSIP",
        "transcript": transcript_to_segments(transcript),
    } 
def crawl_youtube():
    """Fetch all YouTube videos and save them."""

    youtube = get_youtube_client()

    channel_id = get_channel_id(youtube)

    playlist_id = get_uploads_playlist_id(
        youtube,
        channel_id,
    )

    videos = get_all_videos(
        youtube,
        playlist_id,
    )

    docs = []

    print(f"Found {len(videos)} videos")

    for i, video in enumerate(videos, start=1):

        print(f"[{i}/{len(videos)}] {video['title']}")

        doc = build_video_document(video)

        if doc:
            docs.append(doc)

    with open(
        YOUTUBE_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            docs,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nSaved {len(docs)} videos")

    return docs



if __name__ == "__main__":
    crawl_youtube()