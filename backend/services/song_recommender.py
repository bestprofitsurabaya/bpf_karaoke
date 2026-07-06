"""
AI Song Recommender - Content-Based Filtering
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import json
import os
from datetime import datetime
from typing import Dict, List

class SongRecommender:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.song_matrix = None
        self.song_ids = []
        self.song_features = []
        self.is_trained = False
        self.play_history = defaultdict(list)
        self.user_preferences = defaultdict(lambda: defaultdict(int))
        
    def train(self, songs_data: List[Dict]):
        """Train recommender dengan data lagu"""
        if not songs_data:
            return False
            
        self.song_ids = [s['id'] for s in songs_data]
        
        self.song_features = []
        for song in songs_data:
            features = f"{song.get('genre', '')} {song.get('artist', '')} {song.get('language', '')} {song.get('title', '')}"
            self.song_features.append(features)
        
        try:
            self.song_matrix = self.vectorizer.fit_transform(self.song_features)
            self.is_trained = True
            return True
        except:
            return False
    
    def get_recommendations(self, song_id: int, n_recommendations: int = 10) -> List[Dict]:
        """Dapatkan rekomendasi lagu"""
        if not self.is_trained or song_id not in self.song_ids:
            return []
        
        idx = self.song_ids.index(song_id)
        song_vector = self.song_matrix[idx]
        
        similarities = cosine_similarity(song_vector, self.song_matrix).flatten()
        similar_indices = similarities.argsort()[::-1][1:n_recommendations+1]
        
        recommendations = []
        for i in similar_indices:
            recommendations.append({
                'song_id': self.song_ids[i],
                'similarity_score': float(similarities[i]),
                'reason': 'Genre dan artis serupa'
            })
        
        return recommendations
    
    def get_recommendations_for_room(self, room_id: str, n_recommendations: int = 10) -> List[Dict]:
        """Rekomendasi berdasarkan preferensi room"""
        if not self.is_trained:
            return []
        
        preferences = self.user_preferences.get(room_id, {})
        if not preferences:
            return self._get_popular_recommendations(n_recommendations)
        
        favorite_genre = max(preferences, key=preferences.get)
        query_features = f"{favorite_genre}"
        query_vector = self.vectorizer.transform([query_features])
        
        similarities = cosine_similarity(query_vector, self.song_matrix).flatten()
        similar_indices = similarities.argsort()[::-1][:n_recommendations]
        
        recommendations = []
        for i in similar_indices:
            recommendations.append({
                'song_id': self.song_ids[i],
                'similarity_score': float(similarities[i]),
                'reason': f"Karena Anda suka genre {favorite_genre}"
            })
        
        return recommendations
    
    def get_mood_based_recommendations(self, mood: str, n_recommendations: int = 10) -> List[Dict]:
        """Rekomendasi berdasarkan mood"""
        if not self.is_trained:
            return []
        
        mood_genre_map = {
            'happy': 'Pop Indonesia Dangdut',
            'energetic': 'Rock K-Pop Dangdut',
            'sad': 'Ballad',
            'relaxed': 'Jazz',
            'romantic': 'Pop Indonesia Barat'
        }
        
        query_features = mood_genre_map.get(mood, 'Pop Indonesia')
        query_vector = self.vectorizer.transform([query_features])
        
        similarities = cosine_similarity(query_vector, self.song_matrix).flatten()
        similar_indices = similarities.argsort()[::-1][:n_recommendations]
        
        recommendations = []
        for i in similar_indices:
            recommendations.append({
                'song_id': self.song_ids[i],
                'similarity_score': float(similarities[i]),
                'reason': f"Lagu {mood} untuk menemani suasana"
            })
        
        return recommendations
    
    def record_play(self, room_id: str, song_id: int, genre: str = None):
        """Catat lagu yang diputar"""
        self.play_history[room_id].append({
            'song_id': song_id,
            'timestamp': datetime.now().isoformat()
        })
        
        if genre:
            self.user_preferences[room_id][genre] += 1
    
    def _get_popular_recommendations(self, n: int = 10) -> List[Dict]:
        """Rekomendasi populer"""
        return self.get_mood_based_recommendations('happy', n)

# Singleton instance
song_recommender = SongRecommender()
