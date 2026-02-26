import random
from typing import Dict, List, Optional, Tuple

Song = Dict[str, object]
PlaylistMap = Dict[str, List[Song]]
Mood = str

PLAYLIST_NAMES = ("Hype", "Chill", "Mixed")
HYPE_KEYWORDS = ("rock", "punk", "party")
CHILL_KEYWORDS = ("lofi", "ambient", "sleep")

DEFAULT_PROFILE = {
    "name": "Default",
    "hype_min_energy": 7,
    "chill_max_energy": 3,
    "favorite_genre": "rock",
    "include_mixed": True,
}


def _as_int(value: object, default: int = 0) -> int:
    """Safely coerce a value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp a numeric value to a range."""
    return max(minimum, min(maximum, value))


def _normalize_tags(raw_tags: object) -> List[str]:
    """Normalize raw tags to a cleaned lowercase list."""
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    if not isinstance(raw_tags, list):
        return []

    normalized: List[str] = []
    for tag in raw_tags:
        cleaned = str(tag).strip().lower()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _contains_any_keyword(text: str, keywords: Tuple[str, ...]) -> bool:
    """Return True if any keyword appears in text."""
    return any(keyword in text for keyword in keywords)


def _song_key(song: Song) -> Tuple[object, ...]:
    """Build a stable key for unique-song calculations."""
    tags = song.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    return (
        normalize_title(str(song.get("title", ""))),
        normalize_artist(str(song.get("artist", ""))),
        normalize_genre(str(song.get("genre", ""))),
        _as_int(song.get("energy", 0), default=0),
        tuple(sorted(str(tag).strip().lower() for tag in tags if str(tag).strip())),
    )


def normalize_title(title: str) -> str:
    """Normalize a song title for comparisons."""
    if not isinstance(title, str):
        return ""
    return title.strip()


def normalize_artist(artist: str) -> str:
    """Normalize an artist name for comparisons."""
    if not artist:
        return ""
    return artist.strip().lower()


def normalize_genre(genre: str) -> str:
    """Normalize a genre name for comparisons."""
    return genre.lower().strip()


def normalize_song(raw: Song) -> Song:
    """Return a normalized song dict with expected keys."""
    title = normalize_title(str(raw.get("title", "")))
    artist = normalize_artist(str(raw.get("artist", "")))
    genre = normalize_genre(str(raw.get("genre", "")))
    energy = _clamp(_as_int(raw.get("energy", 0), default=0), 0, 10)
    normalized_tags = _normalize_tags(raw.get("tags", []))

    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": normalized_tags,
    }


def classify_song(song: Song, profile: Dict[str, object]) -> Mood:
    """Return a mood label given a song and user profile."""
    energy = _as_int(song.get("energy", 0), default=0)
    genre = normalize_genre(str(song.get("genre", "")))
    title = normalize_title(str(song.get("title", "")).lower())

    hype_min_energy = _as_int(profile.get("hype_min_energy", 7), default=7)
    chill_max_energy = _as_int(profile.get("chill_max_energy", 3), default=3)
    favorite_genre = str(profile.get("favorite_genre", "")).lower()

    is_hype_energy = energy >= hype_min_energy
    is_chill_energy = energy <= chill_max_energy
    is_favorite_genre = bool(favorite_genre) and genre == favorite_genre
    is_hype_keyword = _contains_any_keyword(genre, HYPE_KEYWORDS)
    is_chill_keyword = _contains_any_keyword(title, CHILL_KEYWORDS)

    if is_hype_energy or is_favorite_genre or is_hype_keyword:
        return "Hype"
    if is_chill_energy or is_chill_keyword:
        return "Chill"
    return "Mixed"


def build_playlists(songs: List[Song], profile: Dict[str, object]) -> PlaylistMap:
    """Group songs into playlists based on mood and profile."""
    playlists: PlaylistMap = {name: [] for name in PLAYLIST_NAMES}

    for song in songs:
        normalized = normalize_song(song)
        mood = classify_song(normalized, profile)
        normalized["mood"] = mood
        playlists[mood].append(normalized)

    return playlists


def merge_playlists(a: PlaylistMap, b: PlaylistMap) -> PlaylistMap:
    """Merge two playlist maps into a new map."""
    merged: PlaylistMap = {}
    for key in set(list(a.keys()) + list(b.keys())):
        merged[key] = list(a.get(key, []))
        merged[key].extend(b.get(key, []))
    return merged


def compute_playlist_stats(playlists: PlaylistMap) -> Dict[str, object]:
    """Compute statistics across all playlists."""
    all_songs: List[Song] = []
    for songs in playlists.values():
        all_songs.extend(songs)

    unique_map: Dict[Tuple[object, ...], Song] = {}
    for song in all_songs:
        key = _song_key(song)
        if key not in unique_map:
            unique_map[key] = song
    unique_songs = list(unique_map.values())

    hype = playlists.get("Hype", [])
    chill = playlists.get("Chill", [])
    mixed = playlists.get("Mixed", [])

    unique_hype = {_song_key(song) for song in hype}
    unique_chill = {_song_key(song) for song in chill}
    unique_mixed = {_song_key(song) for song in mixed}

    total = len(unique_songs)
    hype_ratio = (len(unique_hype) / total * 100) if total > 0 else 0.0

    avg_energy = 0.0
    if unique_songs:
        total_energy = sum(int(song.get("energy", 0)) for song in unique_songs)
        avg_energy = total_energy / len(unique_songs)

    top_artist, top_count = most_common_artist(unique_songs)

    return {
        "total_songs": total,
        "hype_count": len(unique_hype),
        "chill_count": len(unique_chill),
        "mixed_count": len(unique_mixed),
        "hype_ratio": hype_ratio,
        "avg_energy": avg_energy,
        "top_artist": top_artist,
        "top_artist_count": top_count,
    }


def most_common_artist(songs: List[Song]) -> Tuple[str, int]:
    """Return the most common artist and count."""
    counts: Dict[str, int] = {}
    for song in songs:
        artist = str(song.get("artist", ""))
        if not artist:
            continue
        counts[artist] = counts.get(artist, 0) + 1

    if not counts:
        return "", 0

    return max(counts.items(), key=lambda item: item[1])


def search_songs(
    songs: List[Song],
    query: str,
    field: str = "artist",
) -> List[Song]:
    """Return songs matching the query on a given field."""
    if not query:
        return songs

    q = query.lower().strip()
    return [
        song
        for song in songs
        if (value := str(song.get(field, "")).lower()) and q in value
    ]


def lucky_pick(
    playlists: PlaylistMap,
    mode: str = "any",
) -> Optional[Song]:
    """Pick a song from the playlists according to mode."""
    if mode == "hype":
        songs = playlists.get("Hype", [])
    elif mode == "chill":
        songs = playlists.get("Chill", [])
    else:
        songs = (
            playlists.get("Hype", [])
            + playlists.get("Chill", [])
            + playlists.get("Mixed", [])
        )

    return random_choice_or_none(songs)


def random_choice_or_none(songs: List[Song]) -> Optional[Song]:
    """Return a random song or None."""
    if not songs:
        return None

    return random.choice(songs)


def history_summary(history: List[Song]) -> Dict[str, int]:
    """Return a summary of moods seen in the history."""
    counts = {"Hype": 0, "Chill": 0, "Mixed": 0}
    for song in history:
        mood = song.get("mood", "Mixed")
        if mood not in counts:
            counts["Mixed"] += 1
        else:
            counts[mood] += 1
    return counts
