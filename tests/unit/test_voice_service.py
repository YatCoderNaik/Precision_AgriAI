"""
Unit Tests for VoiceService

Tests AWS Transcribe, Polly, and Bedrock integration for voice interactions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.voice_service import VoiceService, IntentResult, AudioResponse
import asyncio
from datetime import datetime
import json


@pytest.fixture
def voice_service():
    """Create VoiceService instance with mocked AWS clients"""
    with patch('services.voice_service.boto3.client'):
        service = VoiceService(region='ap-south-2')
        return service


@pytest.fixture
def mock_transcribe_response():
    """Mock Transcribe API response"""
    return {
        'TranscriptionJob': {
            'TranscriptionJobStatus': 'COMPLETED',
            'Transcript': {
                'TranscriptFileUri': 'https://example.com/transcript.json'
            }
        }
    }


@pytest.fixture
def mock_transcript_data():
    """Mock transcript JSON data"""
    return {
        'results': {
            'transcripts': [
                {'transcript': 'check my crop health'}
            ],
            'items': [
                {
                    'alternatives': [
                        {'confidence': '0.95'}
                    ]
                }
            ]
        }
    }


@pytest.fixture
def mock_polly_response():
    """Mock Polly API response"""
    mock_stream = Mock()
    mock_stream.read.return_value = b'mock_audio_data'
    return {'AudioStream': mock_stream}


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response for intent detection"""
    return {
        'body': Mock(read=lambda: json.dumps({
            'content': [{
                'text': json.dumps({
                    'intent': 'check_crop',
                    'entities': {'location': 'field 1'},
                    'confidence': 0.9
                })
            }]
        }).encode())
    }


class TestVoiceServiceInitialization:
    """Test VoiceService initialization"""
    
    def test_initialization_with_defaults(self):
        """Test service initializes with default settings"""
        with patch('services.voice_service.boto3.client'):
            service = VoiceService()
            
            assert service.region is not None
            assert service.audio_bucket is not None
            assert service.bedrock_model_id is not None
            assert isinstance(service.audio_cache, dict)
    
    def test_initialization_with_custom_region(self):
        """Test service initializes with custom region"""
        with patch('services.voice_service.boto3.client'):
            service = VoiceService(region='us-east-1')
            
            assert service.region == 'us-east-1'
    
    def test_initialization_with_custom_bucket(self):
        """Test service initializes with custom bucket"""
        with patch('services.voice_service.boto3.client'):
            service = VoiceService(audio_bucket='my-audio-bucket')
            
            assert service.audio_bucket == 'my-audio-bucket'


class TestIntentDetection:
    """Test intent detection functionality"""
    
    @pytest.mark.asyncio
    async def test_detect_intent_check_crop(self, voice_service, mock_bedrock_response):
        """Test intent detection for crop check command"""
        with patch.object(voice_service.bedrock, 'invoke_model', return_value=mock_bedrock_response):
            result = await voice_service.detect_intent("check my crop health")
            
            assert isinstance(result, IntentResult)
            assert result.intent == 'check_crop'
            assert result.confidence > 0.0
            assert isinstance(result.entities, dict)
    
    @pytest.mark.asyncio
    async def test_detect_intent_register_plot(self, voice_service):
        """Test intent detection for plot registration"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{
                    'text': json.dumps({
                        'intent': 'register_plot',
                        'entities': {},
                        'confidence': 0.85
                    })
                }]
            }).encode())
        }
        
        with patch.object(voice_service.bedrock, 'invoke_model', return_value=mock_response):
            result = await voice_service.detect_intent("register new plot")
            
            assert result.intent == 'register_plot'
            assert result.confidence > 0.0
    
    @pytest.mark.asyncio
    async def test_detect_intent_get_help(self, voice_service):
        """Test intent detection for help request"""
        mock_response = {
            'body': Mock(read=lambda: json.dumps({
                'content': [{
                    'text': json.dumps({
                        'intent': 'get_help',
                        'entities': {},
                        'confidence': 0.9
                    })
                }]
            }).encode())
        }
        
        with patch.object(voice_service.bedrock, 'invoke_model', return_value=mock_response):
            result = await voice_service.detect_intent("I need help")
            
            assert result.intent == 'get_help'
    
    @pytest.mark.asyncio
    async def test_detect_intent_fallback_on_error(self, voice_service):
        """Test fallback intent detection when Bedrock fails"""
        with patch.object(voice_service.bedrock, 'invoke_model', side_effect=Exception('API Error')):
            result = await voice_service.detect_intent("check my crop")
            
            # Should use fallback
            assert isinstance(result, IntentResult)
            assert result.intent in ['check_crop', 'register_plot', 'get_help', 'unknown']
    
    def test_fallback_intent_detection_check_crop(self, voice_service):
        """Test fallback intent detection for crop check"""
        result = voice_service._fallback_intent_detection("check my crop health")
        
        assert result.intent == 'check_crop'
        assert result.confidence > 0.0
    
    def test_fallback_intent_detection_register_plot(self, voice_service):
        """Test fallback intent detection for plot registration"""
        result = voice_service._fallback_intent_detection("register new plot")
        
        assert result.intent == 'register_plot'
    
    def test_fallback_intent_detection_get_help(self, voice_service):
        """Test fallback intent detection for help"""
        result = voice_service._fallback_intent_detection("I need help")
        
        assert result.intent == 'get_help'
    
    def test_fallback_intent_detection_unknown(self, voice_service):
        """Test fallback intent detection for unknown command"""
        result = voice_service._fallback_intent_detection("random gibberish")
        
        assert result.intent == 'unknown'


class TestAudioGeneration:
    """Test audio generation functionality"""
    
    @pytest.mark.asyncio
    async def test_generate_audio_response(self, voice_service, mock_polly_response):
        """Test audio response generation"""
        with patch.object(voice_service.polly, 'synthesize_speech', return_value=mock_polly_response):
            with patch.object(voice_service.s3, 'put_object'):
                with patch.object(voice_service.s3, 'generate_presigned_url', return_value='https://example.com/audio.mp3'):
                    response = await voice_service.generate_audio_response(
                        text="Your crop is healthy",
                        language="en-IN"
                    )
                    
                    assert isinstance(response, AudioResponse)
                    assert response.audio_url
                    assert response.audio_data == b'mock_audio_data'
                    assert response.text == "Your crop is healthy"
                    assert response.language == "en-IN"
                    assert response.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_generate_audio_with_caching(self, voice_service, mock_polly_response):
        """Test audio caching functionality"""
        with patch.object(voice_service.polly, 'synthesize_speech', return_value=mock_polly_response):
            with patch.object(voice_service.s3, 'put_object'):
                with patch.object(voice_service.s3, 'generate_presigned_url', return_value='https://example.com/audio.mp3'):
                    # First call - should generate
                    response1 = await voice_service.generate_audio_response(
                        text="Short text",
                        language="en-IN",
                        use_cache=True
                    )
                    
                    # Second call - should use cache
                    response2 = await voice_service.generate_audio_response(
                        text="Short text",
                        language="en-IN",
                        use_cache=True
                    )
                    
                    # Should be same object from cache
                    assert response1 is response2
    
    @pytest.mark.asyncio
    async def test_generate_audio_without_caching(self, voice_service, mock_polly_response):
        """Test audio generation without caching"""
        with patch.object(voice_service.polly, 'synthesize_speech', return_value=mock_polly_response):
            with patch.object(voice_service.s3, 'put_object'):
                with patch.object(voice_service.s3, 'generate_presigned_url', return_value='https://example.com/audio.mp3'):
                    response = await voice_service.generate_audio_response(
                        text="Your crop is healthy",
                        language="en-IN",
                        use_cache=False
                    )
                    
                    # Should not be in cache
                    assert len(voice_service.audio_cache) == 0


class TestLanguageMapping:
    """Test language code mapping"""
    
    def test_get_transcribe_language_code(self, voice_service):
        """Test Transcribe language code mapping"""
        assert voice_service._get_transcribe_language_code('hi-IN') == 'hi-IN'
        assert voice_service._get_transcribe_language_code('ta-IN') == 'ta-IN'
        assert voice_service._get_transcribe_language_code('te-IN') == 'te-IN'
        assert voice_service._get_transcribe_language_code('en-IN') == 'en-IN'
        assert voice_service._get_transcribe_language_code('en') == 'en-IN'
        assert voice_service._get_transcribe_language_code('unknown') == 'en-IN'  # Default
    
    def test_get_polly_voice_id(self, voice_service):
        """Test Polly voice ID mapping"""
        assert voice_service._get_polly_voice_id('hi-IN') == 'Kajal'
        assert voice_service._get_polly_voice_id('en-IN') == 'Kajal'
        assert voice_service._get_polly_voice_id('en-US') == 'Joanna'
        assert voice_service._get_polly_voice_id('unknown') == 'Kajal'  # Default


class TestSupportedLanguages:
    """Test supported languages functionality"""
    
    def test_get_supported_voice_languages(self, voice_service):
        """Test getting supported languages"""
        languages = voice_service.get_supported_voice_languages()
        
        assert len(languages) >= 4
        assert all(lang.code for lang in languages)
        assert all(lang.name for lang in languages)
        assert all(lang.native_name for lang in languages)
        assert all(lang.voice_id for lang in languages)
        assert all(hasattr(lang, 'transcribe_supported') for lang in languages)
        assert all(lang.transcribe_language_code for lang in languages)
    
    def test_supported_languages_include_required(self, voice_service):
        """Test that required languages are supported"""
        languages = voice_service.get_supported_voice_languages()
        language_codes = [lang.code for lang in languages]
        
        assert 'hi-IN' in language_codes
        assert 'ta-IN' in language_codes
        assert 'te-IN' in language_codes
        assert 'en-IN' in language_codes


class TestVoiceCommandProcessing:
    """Test complete voice command processing"""
    
    @pytest.mark.asyncio
    async def test_process_voice_command_check_crop(self, voice_service):
        """Test processing voice command for crop check"""
        mock_result = {
            'transcription': 'check my crop health',
            'confidence': 0.95,
            'intent': IntentResult(intent='check_crop', entities={}, confidence=0.9)
        }
        
        with patch.object(voice_service, 'process_audio_input', return_value=Mock(**mock_result)):
            result = await voice_service.process_voice_command(
                audio_data=b'mock_audio',
                language='en-IN'
            )
            
            assert result['action'] == 'analyze_plot'
            assert 'transcription' in result
            assert 'confidence' in result
    
    @pytest.mark.asyncio
    async def test_process_voice_command_error_handling(self, voice_service):
        """Test error handling in voice command processing"""
        with patch.object(voice_service, 'process_audio_input', side_effect=Exception('Processing failed')):
            result = await voice_service.process_voice_command(
                audio_data=b'mock_audio',
                language='en-IN'
            )
            
            assert result['action'] == 'error'
            assert 'error' in result
            assert 'message' in result


class TestCacheManagement:
    """Test audio cache management"""
    
    def test_clear_audio_cache(self, voice_service):
        """Test clearing audio cache"""
        # Add something to cache
        voice_service.audio_cache['test'] = Mock()
        assert len(voice_service.audio_cache) > 0
        
        # Clear cache
        voice_service.clear_audio_cache()
        assert len(voice_service.audio_cache) == 0


class TestServiceInfo:
    """Test service information"""
    
    def test_get_service_info(self, voice_service):
        """Test getting service information"""
        info = voice_service.get_service_info()
        
        assert info['service'] == 'VoiceService'
        assert 'region' in info
        assert 'audio_bucket' in info
        assert 'bedrock_model' in info
        assert 'supported_languages' in info
        assert 'cache_size' in info
        assert isinstance(info['supported_languages'], list)
        assert len(info['supported_languages']) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
