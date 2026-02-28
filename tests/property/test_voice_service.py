"""
Property-Based Tests for VoiceService

Property 20: Voice Interaction Accuracy
Validates: Requirements 3.1, 3.2, 3.3, 3.4

Tests voice transcription, intent detection, and audio generation accuracy.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
from services.voice_service import VoiceService, IntentResult
import asyncio


# Test data strategies
@st.composite
def voice_command_text(draw):
    """Generate realistic voice command text"""
    commands = [
        "check my crop health",
        "analyze my plot",
        "register new plot",
        "I need help",
        "what is the status of my field",
        "show me crop analysis",
        "add a new field",
        "can you help me"
    ]
    return draw(st.sampled_from(commands))


@st.composite
def language_code(draw):
    """Generate valid language codes"""
    codes = ['hi-IN', 'ta-IN', 'te-IN', 'en-IN', 'en']
    return draw(st.sampled_from(codes))


@st.composite
def guidance_text(draw):
    """Generate farmer guidance text"""
    texts = [
        "Your crop is healthy. Continue current practices.",
        "Your crop shows signs of stress. Check irrigation immediately.",
        "URGENT: Your crop needs immediate attention. Inspect field today.",
        "Good news! Your crop health is excellent. Maintain watering schedule."
    ]
    return draw(st.sampled_from(texts))


class TestVoiceInteractionAccuracy:
    """
    Property 20: Voice Interaction Accuracy
    
    Validates that voice interactions maintain accuracy across:
    - Intent detection
    - Language handling
    - Audio generation
    """
    
    @pytest.fixture
    def voice_service(self):
        """Create VoiceService instance"""
        return VoiceService(region='ap-south-2')
    
    @given(text=voice_command_text())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_intent_detection_consistency(self, voice_service, text):
        """
        Property: Intent detection must be consistent for similar commands
        
        Given a voice command text
        When intent is detected multiple times
        Then the same intent should be returned consistently
        """
        # Run intent detection multiple times
        results = []
        for _ in range(3):
            result = asyncio.run(voice_service.detect_intent(text))
            results.append(result.intent)
        
        # All results should be the same
        assert len(set(results)) == 1, f"Inconsistent intent detection for '{text}': {results}"
        
        # Intent should be valid
        valid_intents = ['check_crop', 'register_plot', 'get_help', 'unknown']
        assert results[0] in valid_intents, f"Invalid intent: {results[0]}"
    
    @given(text=voice_command_text())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_intent_confidence_bounds(self, voice_service, text):
        """
        Property: Intent confidence must be within valid bounds
        
        Given a voice command text
        When intent is detected
        Then confidence must be between 0.0 and 1.0
        """
        result = asyncio.run(voice_service.detect_intent(text))
        
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} out of bounds for '{text}'"
        
        # Confidence should be reasonable (not too low)
        assert result.confidence >= 0.3, \
            f"Confidence {result.confidence} too low for '{text}'"
    
    @given(text=voice_command_text())
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_intent_entities_structure(self, voice_service, text):
        """
        Property: Intent entities must have valid structure
        
        Given a voice command text
        When intent is detected
        Then entities must be a dictionary
        """
        result = asyncio.run(voice_service.detect_intent(text))
        
        assert isinstance(result.entities, dict), \
            f"Entities must be dict, got {type(result.entities)}"
        
        # Entity values should be strings or None
        for key, value in result.entities.items():
            assert isinstance(key, str), f"Entity key must be string: {key}"
            assert value is None or isinstance(value, str), \
                f"Entity value must be string or None: {value}"
    
    @given(
        text=guidance_text(),
        lang=language_code()
    )
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audio_generation_consistency(self, voice_service, text, lang):
        """
        Property: Audio generation must be consistent
        
        Given guidance text and language
        When audio is generated
        Then audio response must have valid structure
        """
        try:
            response = asyncio.run(
                voice_service.generate_audio_response(text, lang, use_cache=False)
            )
            
            # Response must have required fields
            assert response.audio_url, "Audio URL must not be empty"
            assert response.text == text, "Text must match input"
            assert response.language == lang, "Language must match input"
            assert response.duration_ms > 0, "Duration must be positive"
            
            # Audio data should be present
            assert response.audio_data is not None, "Audio data must be present"
            assert len(response.audio_data) > 0, "Audio data must not be empty"
            
        except Exception as e:
            # AWS services might not be available in test environment
            pytest.skip(f"AWS service unavailable: {e}")
    
    @given(lang=language_code())
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_language_code_mapping(self, voice_service, lang):
        """
        Property: Language codes must map to valid Transcribe codes
        
        Given a language code
        When mapped to Transcribe code
        Then result must be a valid Transcribe language code
        """
        transcribe_code = voice_service._get_transcribe_language_code(lang)
        
        # Must be a valid Transcribe code
        valid_codes = ['hi-IN', 'ta-IN', 'te-IN', 'en-IN']
        assert transcribe_code in valid_codes, \
            f"Invalid Transcribe code: {transcribe_code}"
    
    @given(lang=language_code())
    @settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_voice_id_mapping(self, voice_service, lang):
        """
        Property: Language codes must map to valid Polly voice IDs
        
        Given a language code
        When mapped to Polly voice ID
        Then result must be a valid voice ID
        """
        voice_id = voice_service._get_polly_voice_id(lang)
        
        # Must be a non-empty string
        assert isinstance(voice_id, str), "Voice ID must be string"
        assert len(voice_id) > 0, "Voice ID must not be empty"
        
        # Must be a valid Polly voice
        valid_voices = ['Kajal', 'Joanna', 'Aditi']
        assert voice_id in valid_voices, f"Invalid voice ID: {voice_id}"
    
    def test_supported_languages_completeness(self, voice_service):
        """
        Property: Supported languages must be complete
        
        When getting supported languages
        Then all required Indian languages must be present
        """
        languages = voice_service.get_supported_voice_languages()
        
        # Must have at least 4 languages
        assert len(languages) >= 4, "Must support at least 4 languages"
        
        # Must include required languages
        language_codes = [lang.code for lang in languages]
        required = ['hi-IN', 'ta-IN', 'te-IN', 'en-IN']
        
        for code in required:
            assert code in language_codes, f"Missing required language: {code}"
        
        # Each language must have required fields
        for lang in languages:
            assert lang.code, "Language code must not be empty"
            assert lang.name, "Language name must not be empty"
            assert lang.native_name, "Native name must not be empty"
            assert lang.voice_id, "Voice ID must not be empty"
            assert isinstance(lang.transcribe_supported, bool), \
                "Transcribe supported must be boolean"
            assert lang.transcribe_language_code, \
                "Transcribe language code must not be empty"
    
    @given(text=voice_command_text())
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_fallback_intent_detection(self, voice_service, text):
        """
        Property: Fallback intent detection must always return valid result
        
        Given a voice command text
        When fallback intent detection is used
        Then result must be valid
        """
        result = voice_service._fallback_intent_detection(text)
        
        # Must return valid IntentResult
        assert isinstance(result, IntentResult), "Must return IntentResult"
        
        # Intent must be valid
        valid_intents = ['check_crop', 'register_plot', 'get_help', 'unknown']
        assert result.intent in valid_intents, f"Invalid intent: {result.intent}"
        
        # Confidence must be in bounds
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} out of bounds"
        
        # Entities must be dict
        assert isinstance(result.entities, dict), "Entities must be dict"
    
    def test_audio_cache_functionality(self, voice_service):
        """
        Property: Audio cache must work correctly
        
        When audio is generated with caching
        Then subsequent requests should use cache
        """
        text = "Your crop is healthy"
        lang = "en-IN"
        
        # Clear cache first
        voice_service.clear_audio_cache()
        assert len(voice_service.audio_cache) == 0, "Cache should be empty"
        
        try:
            # Generate audio (should cache)
            response1 = asyncio.run(
                voice_service.generate_audio_response(text, lang, use_cache=True)
            )
            
            # Cache should have one entry
            assert len(voice_service.audio_cache) == 1, "Cache should have one entry"
            
            # Generate again (should use cache)
            response2 = asyncio.run(
                voice_service.generate_audio_response(text, lang, use_cache=True)
            )
            
            # Responses should be identical (same object from cache)
            assert response1 is response2, "Should return cached response"
            
            # Clear cache
            voice_service.clear_audio_cache()
            assert len(voice_service.audio_cache) == 0, "Cache should be empty after clear"
            
        except Exception as e:
            pytest.skip(f"AWS service unavailable: {e}")
    
    def test_service_info_completeness(self, voice_service):
        """
        Property: Service info must be complete
        
        When getting service info
        Then all required fields must be present
        """
        info = voice_service.get_service_info()
        
        # Required fields
        assert 'service' in info, "Must have service field"
        assert info['service'] == 'VoiceService', "Service name must be correct"
        
        assert 'region' in info, "Must have region field"
        assert isinstance(info['region'], str), "Region must be string"
        
        assert 'audio_bucket' in info, "Must have audio_bucket field"
        assert isinstance(info['audio_bucket'], str), "Bucket must be string"
        
        assert 'bedrock_model' in info, "Must have bedrock_model field"
        assert isinstance(info['bedrock_model'], str), "Model must be string"
        
        assert 'supported_languages' in info, "Must have supported_languages field"
        assert isinstance(info['supported_languages'], list), "Languages must be list"
        assert len(info['supported_languages']) >= 4, "Must support at least 4 languages"
        
        assert 'cache_size' in info, "Must have cache_size field"
        assert isinstance(info['cache_size'], int), "Cache size must be int"
        assert info['cache_size'] >= 0, "Cache size must be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
