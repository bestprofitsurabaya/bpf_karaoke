# AI Services
try:
    from .song_recommender import SongRecommender
except ImportError:
    SongRecommender = None

try:
    from .mood_detector import MoodDetector
except ImportError:
    MoodDetector = None

try:
    from .smart_search import SmartSearch
except ImportError:
    SmartSearch = None

try:
    from .auto_playlist import AutoPlaylistGenerator
except ImportError:
    AutoPlaylistGenerator = None

try:
    from .voice_analyzer import VoiceAnalyzer
except ImportError:
    VoiceAnalyzer = None
