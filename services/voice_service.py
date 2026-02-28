"""
VoiceService - AWS Transcribe/Polly Integration

Handles all voice input/output operations including:
- Audio transcription via AWS Transcribe
- Intent detection and entity extraction
- Multi-language audio generation via AWS Polly
- Voice command processing and routing
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
import logging
import boto3
from botocore.exceptions import ClientError
import json
import time
import uuid
import asyncio

from config.settings import get_settings

logger = logging.getLogger(__name__)


class VoiceLanguageOption(BaseModel):
    """Voice language configuration"""
    code: str  # 'hi-IN', 'ta-IN', 'te-IN', 'en-IN'
    name: str
    native_name: str
    voice_id: str  # AWS Polly voice ID
    transcribe_supported: bool
    transcribe_language_code: str  # Language code for Transcribe


class IntentResult(BaseModel):
    """Result of intent detection"""
    intent: str  # 'check_crop', 'register_plot', 'get_help', 'unknown'
    entities: Dict[str, Any]
    confidence: float


class VoiceProcessingResult(BaseModel):
    """Result of voice processing"""
    transcribed_text: str
    detected_language: str
    confidence: float
    intent: IntentResult
    processing_time_ms: int


class AudioResponse(BaseModel):
    """Audio response data"""
    audio_url: str
    audio_data: Optional[bytes] = None  # For direct playback
    duration_ms: int
    text: str
    language: str
    generated_at: datetime


class VoiceService:
    """Service for AWS Transcribe/Polly voice interaction"""
    
    def __init__(self, region: Optional[str] = None, audio_bucket: Optional[str] = None):
        """
        Initialize VoiceService with AWS clients
        
        Args:
            region: AWS region (defaults to settings)
            audio_bucket: S3 bucket for audio storage (defaults to settings)
        """
        settings = get_settings()
        self.region = region or settings.aws.region
        self.audio_bucket = audio_bucket or f"precision-agriai-audio-{self.region}"
        
        # Fallback mode flag (set to True if AWS services unavailable)
        self.fallback_mode = False
        
        # Initialize AWS clients
        try:
            self.transcribe = boto3.client('transcribe', region_name=self.region)
            self.polly = boto3.client('polly', region_name=self.region)
        except Exception as e:
            logger.warning(f"Failed to initialize AWS voice clients: {e}")
            self.transcribe = None
            self.polly = None
            self.fallback_mode = True
        self.bedrock = boto3.client('bedrock-runtime', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        
        # Bedrock model for intent detection
        self.bedrock_model_id = 'anthropic.claude-3-haiku-20240307-v1:0'  # Fast model for intent
        
        # Audio cache for common phrases
        self.audio_cache: Dict[str, AudioResponse] = {}
        
        # Ensure S3 bucket exists (in production, this should be pre-created)
        if not self.fallback_mode:
            self._ensure_audio_bucket()
        
        if self.fallback_mode:
            logger.warning(f"VoiceService initialized in FALLBACK MODE (AWS Transcribe/Polly unavailable)")
        else:
            logger.info(f"VoiceService initialized with region={self.region}, bucket={self.audio_bucket}")
    
    def _ensure_audio_bucket(self):
        """Ensure S3 bucket exists for audio storage"""
        try:
            self.s3.head_bucket(Bucket=self.audio_bucket)
            logger.info(f"Audio bucket {self.audio_bucket} exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    # Create bucket
                    if self.region == 'us-east-1':
                        self.s3.create_bucket(Bucket=self.audio_bucket)
                    else:
                        self.s3.create_bucket(
                            Bucket=self.audio_bucket,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"Created audio bucket {self.audio_bucket}")
                except ClientError as create_error:
                    logger.warning(f"Could not create audio bucket: {create_error}")
            else:
                logger.warning(f"Error checking audio bucket: {e}")
    
    async def process_audio_input(
        self, 
        audio_data: bytes, 
        language: Optional[str] = None
    ) -> VoiceProcessingResult:
        """
        Process audio input through transcription and intent detection
        
        Args:
            audio_data: Raw audio bytes (WAV, MP3, or other supported format)
            language: Optional language code (auto-detect if None)
            
        Returns:
            VoiceProcessingResult with transcription and intent
            
        Raises:
            ClientError: If AWS services fail
        """
        start_time = time.time()
        
        # Check if in fallback mode
        if self.fallback_mode or self.transcribe is None:
            logger.warning("Voice service in fallback mode - returning mock result")
            return VoiceProcessingResult(
                transcribed_text="[Voice input unavailable - AWS Transcribe not activated]",
                detected_language=language or 'en-IN',
                confidence=0.0,
                intent=IntentResult(
                    intent='unknown',
                    entities={},
                    confidence=0.0
                ),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        try:
            # Step 1: Upload audio to S3
            audio_key = f"input/{uuid.uuid4()}.wav"
            self.s3.put_object(
                Bucket=self.audio_bucket,
                Key=audio_key,
                Body=audio_data,
                ContentType='audio/wav'
            )
            audio_uri = f"s3://{self.audio_bucket}/{audio_key}"
            
            logger.info(f"Uploaded audio to {audio_uri}")
            
            # Step 2: Start transcription job
            job_name = f"transcribe-{uuid.uuid4()}"
            
            # Determine language code for Transcribe
            transcribe_language = self._get_transcribe_language_code(language)
            
            self.transcribe.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': audio_uri},
                MediaFormat='wav',
                LanguageCode=transcribe_language
            )
            
            logger.info(f"Started transcription job {job_name}")
            
            # Step 3: Wait for transcription completion (with timeout)
            max_wait_time = 60  # seconds
            wait_interval = 2  # seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                response = self.transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    
                    # Fetch transcript
                    import requests
                    transcript_response = requests.get(transcript_uri)
                    transcript_data = transcript_response.json()
                    
                    transcribed_text = transcript_data['results']['transcripts'][0]['transcript']
                    confidence = float(transcript_data['results']['items'][0].get('alternatives', [{}])[0].get('confidence', 0.9))
                    
                    logger.info(f"Transcription complete: {transcribed_text}")
                    
                    # Step 4: Detect intent
                    intent = await self.detect_intent(transcribed_text)
                    
                    # Cleanup
                    self.transcribe.delete_transcription_job(TranscriptionJobName=job_name)
                    self.s3.delete_object(Bucket=self.audio_bucket, Key=audio_key)
                    
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    return VoiceProcessingResult(
                        transcribed_text=transcribed_text,
                        detected_language=language or transcribe_language,
                        confidence=confidence,
                        intent=intent,
                        processing_time_ms=processing_time
                    )
                    
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown')
                    raise ValueError(f"Transcription failed: {failure_reason}")
                
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval
            
            raise TimeoutError(f"Transcription timed out after {max_wait_time}s")
            
        except Exception as e:
            logger.error(f"Audio processing failed: {e}", exc_info=True)
            raise
    
    def _get_transcribe_language_code(self, language: Optional[str]) -> str:
        """
        Get AWS Transcribe language code from language option
        
        Args:
            language: Language code (e.g., 'hi-IN', 'en-IN')
            
        Returns:
            Transcribe-compatible language code
        """
        # Map language codes to Transcribe codes
        language_map = {
            'hi-IN': 'hi-IN',
            'ta-IN': 'ta-IN',
            'te-IN': 'te-IN',
            'en-IN': 'en-IN',
            'en': 'en-IN',
            'hi': 'hi-IN',
            'ta': 'ta-IN',
            'te': 'te-IN'
        }
        
        return language_map.get(language, 'en-IN')
    
    async def detect_intent(self, transcribed_text: str) -> IntentResult:
        """
        Detect user intent using AWS Bedrock
        
        Uses Claude Haiku for fast intent classification and entity extraction.
        
        Args:
            transcribed_text: Transcribed text from audio
            
        Returns:
            IntentResult with detected intent and entities
            
        Raises:
            ClientError: If Bedrock API fails
        """
        try:
            # Construct intent detection prompt
            prompt = f"""You are an agricultural assistant analyzing farmer voice commands.

User said: "{transcribed_text}"

Classify the intent and extract entities. Respond in JSON format:

{{
    "intent": "check_crop|register_plot|get_help|unknown",
    "entities": {{
        "location": "coordinates or place name if mentioned",
        "crop_type": "crop type if mentioned",
        "issue": "problem description if mentioned"
    }},
    "confidence": 0.0-1.0
}}

Intents:
- check_crop: User wants to analyze crop health
- register_plot: User wants to register a new plot
- get_help: User needs assistance or has questions
- unknown: Intent unclear

Respond with ONLY the JSON, no other text."""

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.debug(f"Detecting intent for: {transcribed_text}")
            
            response = self.bedrock.invoke_model(
                modelId=self.bedrock_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Parse JSON response
            try:
                intent_data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if response isn't valid JSON
                logger.warning("Bedrock response not valid JSON, using fallback")
                intent_data = {
                    'intent': 'unknown',
                    'entities': {},
                    'confidence': 0.5
                }
            
            logger.info(f"Detected intent: {intent_data['intent']} (confidence: {intent_data['confidence']})")
            
            return IntentResult(
                intent=intent_data.get('intent', 'unknown'),
                entities=intent_data.get('entities', {}),
                confidence=float(intent_data.get('confidence', 0.5))
            )
            
        except ClientError as e:
            logger.error(f"Bedrock intent detection failed: {e}")
            # Fallback to simple keyword matching
            return self._fallback_intent_detection(transcribed_text)
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return self._fallback_intent_detection(transcribed_text)
    
    def _fallback_intent_detection(self, text: str) -> IntentResult:
        """
        Fallback intent detection using keyword matching
        
        Args:
            text: Transcribed text
            
        Returns:
            IntentResult with basic intent classification
        """
        text_lower = text.lower()
        
        # Simple keyword matching
        if any(word in text_lower for word in ['check', 'analyze', 'health', 'crop', 'ndvi', 'status']):
            return IntentResult(intent='check_crop', entities={}, confidence=0.6)
        elif any(word in text_lower for word in ['register', 'add', 'new', 'plot', 'field']):
            return IntentResult(intent='register_plot', entities={}, confidence=0.6)
        elif any(word in text_lower for word in ['help', 'assist', 'support', 'question']):
            return IntentResult(intent='get_help', entities={}, confidence=0.6)
        else:
            return IntentResult(intent='unknown', entities={}, confidence=0.3)
    
    async def generate_audio_response(
        self, 
        text: str, 
        language: str,
        use_cache: bool = True
    ) -> AudioResponse:
        """
        Generate spoken response using AWS Polly
        
        Args:
            text: Text to convert to speech
            language: Language code for voice selection
            use_cache: Whether to use cached audio for common phrases
            
        Returns:
            AudioResponse with audio URL/data and metadata
            
        Raises:
            ClientError: If Polly API fails
        """
        # Check if in fallback mode
        if self.fallback_mode or self.polly is None:
            logger.warning("Voice service in fallback mode - returning mock audio response")
            return AudioResponse(
                audio_url="",
                audio_data=None,
                duration_ms=0,
                text=text,
                language=language,
                generated_at=datetime.now()
            )
        
        try:
            # Check cache first
            cache_key = f"{language}:{text}"
            if use_cache and cache_key in self.audio_cache:
                logger.info(f"Using cached audio for: {text[:50]}...")
                return self.audio_cache[cache_key]
            
            # Select voice for language
            voice_id = self._get_polly_voice_id(language)
            
            logger.info(f"Generating audio in {language} with voice {voice_id}")
            
            # Generate speech using Polly
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                LanguageCode=language,
                Engine='neural'  # Use neural engine for better quality
            )
            
            # Get audio stream
            audio_data = response['AudioStream'].read()
            
            # Upload to S3 for persistent storage
            audio_key = f"output/{uuid.uuid4()}.mp3"
            self.s3.put_object(
                Bucket=self.audio_bucket,
                Key=audio_key,
                Body=audio_data,
                ContentType='audio/mpeg'
            )
            
            # Generate presigned URL (valid for 1 hour)
            audio_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.audio_bucket, 'Key': audio_key},
                ExpiresIn=3600
            )
            
            # Estimate duration (rough estimate: ~150 words per minute)
            word_count = len(text.split())
            duration_ms = int((word_count / 150) * 60 * 1000)
            
            audio_response = AudioResponse(
                audio_url=audio_url,
                audio_data=audio_data,  # Include raw data for immediate playback
                duration_ms=duration_ms,
                text=text,
                language=language,
                generated_at=datetime.now()
            )
            
            # Cache common phrases
            if use_cache and len(text) < 200:  # Only cache short phrases
                self.audio_cache[cache_key] = audio_response
            
            logger.info(f"Generated audio response ({duration_ms}ms)")
            
            return audio_response
            
        except ClientError as e:
            logger.error(f"Polly audio generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            raise
    
    def _get_polly_voice_id(self, language: str) -> str:
        """
        Get AWS Polly voice ID for language
        
        Args:
            language: Language code
            
        Returns:
            Polly voice ID
        """
        # Map language codes to Polly neural voices
        voice_map = {
            'hi-IN': 'Kajal',  # Hindi (India) - Neural
            'ta-IN': 'Kajal',  # Tamil - fallback to Hindi voice (Polly doesn't have Tamil neural)
            'te-IN': 'Kajal',  # Telugu - fallback to Hindi voice
            'en-IN': 'Kajal',  # English (India) - Neural
            'en-US': 'Joanna',  # English (US) - Neural
            'en': 'Kajal'  # Default to Indian English
        }
        
        return voice_map.get(language, 'Kajal')
    
    def get_supported_voice_languages(self) -> List[VoiceLanguageOption]:
        """
        Return supported voice languages
        
        Returns:
            List of VoiceLanguageOption configurations
        """
        return [
            VoiceLanguageOption(
                code='hi-IN',
                name='Hindi (India)',
                native_name='हिन्दी',
                voice_id='Kajal',
                transcribe_supported=True,
                transcribe_language_code='hi-IN'
            ),
            VoiceLanguageOption(
                code='ta-IN',
                name='Tamil (India)',
                native_name='தமிழ்',
                voice_id='Kajal',  # Fallback to Hindi voice
                transcribe_supported=True,
                transcribe_language_code='ta-IN'
            ),
            VoiceLanguageOption(
                code='te-IN',
                name='Telugu (India)',
                native_name='తెలుగు',
                voice_id='Kajal',  # Fallback to Hindi voice
                transcribe_supported=True,
                transcribe_language_code='te-IN'
            ),
            VoiceLanguageOption(
                code='en-IN',
                name='English (India)',
                native_name='English',
                voice_id='Kajal',
                transcribe_supported=True,
                transcribe_language_code='en-IN'
            ),
        ]
    
    async def process_voice_command(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete voice command processing pipeline
        
        Args:
            audio_data: Raw audio bytes
            language: Optional language code
            
        Returns:
            Dictionary with processing results and next actions
        """
        try:
            # Process audio input
            result = await self.process_audio_input(audio_data, language)
            
            # Route based on intent
            if result.intent.intent == 'check_crop':
                return {
                    'action': 'analyze_plot',
                    'transcription': result.transcribed_text,
                    'entities': result.intent.entities,
                    'confidence': result.confidence
                }
            elif result.intent.intent == 'register_plot':
                return {
                    'action': 'register_plot',
                    'transcription': result.transcribed_text,
                    'entities': result.intent.entities,
                    'confidence': result.confidence
                }
            elif result.intent.intent == 'get_help':
                return {
                    'action': 'show_help',
                    'transcription': result.transcribed_text,
                    'entities': result.intent.entities,
                    'confidence': result.confidence
                }
            else:
                return {
                    'action': 'unknown',
                    'transcription': result.transcribed_text,
                    'entities': result.intent.entities,
                    'confidence': result.confidence,
                    'message': 'Could not understand command. Please try again.'
                }
                
        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            return {
                'action': 'error',
                'error': str(e),
                'message': 'Voice processing failed. Please try again or use manual input.'
            }
    
    def clear_audio_cache(self):
        """Clear the audio response cache"""
        self.audio_cache.clear()
        logger.info("Audio cache cleared")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get service information and status
        
        Returns:
            Dictionary with service information
        """
        return {
            'service': 'VoiceService',
            'region': self.region,
            'audio_bucket': self.audio_bucket,
            'bedrock_model': self.bedrock_model_id,
            'supported_languages': [lang.code for lang in self.get_supported_voice_languages()],
            'cache_size': len(self.audio_cache)
        }
