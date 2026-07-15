import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    YOUTUBE_FILE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

def chunk_transcript(transcript, chunk_size=500, overlap=50):
    """
    Split transcript into ~500-word chunks with 50-word overlap.
    """

    chunks = []

    current_segments = []
    current_words = 0

    for segment in transcript:

        words = segment["text"].split()

        current_segments.append(segment)
        current_words += len(words)

        if current_words >= chunk_size:

            chunks.append(
                {
                    "text": " ".join(
                        s["text"] for s in current_segments
                    ),
                    "start": current_segments[0]["start"],
                }
            )

            overlap_segments = []
            overlap_words = 0

            for s in reversed(current_segments):
                overlap_segments.insert(0, s)
                overlap_words += len(s["text"].split())

                if overlap_words >= overlap:
                    break

            current_segments = overlap_segments
            current_words = overlap_words

    if current_segments:

        chunks.append(
            {
                "text": " ".join(
                    s["text"] for s in current_segments
                ),
                "start": current_segments[0]["start"],
            }
        )

    return chunks
with open(YOUTUBE_FILE, encoding="utf-8") as f:
    videos = json.load(f)

print(f"Loaded {len(videos)} videos")

first = videos[0]

chunks = chunk_transcript(first["transcript"])

print()

print(first["title"])

print(f"Chunks: {len(chunks)}")

print(chunks[0]["start"])

print(chunks[0]["text"][:250])