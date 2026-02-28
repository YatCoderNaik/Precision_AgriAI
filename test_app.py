"""
Quick test script to verify app.py can be imported and services initialize
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all imports work"""
    try:
        logger.info("Testing imports...")
        
        from services.map_service import MapService
        from services.db_service import DbService
        from services.brain_service import BrainService
        from services.voice_service import VoiceService
        from services.integration import ServiceIntegration
        from ui.map_interface import MapInterface
        from config.settings import get_settings
        
        logger.info("✅ All imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False

def test_service_initialization():
    """Test that services can be initialized"""
    try:
        logger.info("Testing service initialization...")
        
        from services.map_service import MapService
        from services.db_service import DbService
        from services.brain_service import BrainService
        from services.integration import ServiceIntegration
        from config.settings import get_settings
        
        settings = get_settings()
        
        map_service = MapService()
        logger.info("✅ MapService initialized")
        
        db_service = DbService()
        logger.info("✅ DbService initialized")
        
        brain_service = BrainService(use_mock_gee=True, region=settings.aws.region)
        logger.info("✅ BrainService initialized")
        
        integration = ServiceIntegration(
            map_service=map_service,
            brain_service=brain_service,
            db_service=db_service
        )
        logger.info("✅ ServiceIntegration initialized")
        
        logger.info("✅ All services initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}", exc_info=True)
        return False

def test_map_service():
    """Test MapService functionality"""
    try:
        logger.info("Testing MapService...")
        
        from services.map_service import MapService
        
        map_service = MapService()
        
        # Test coordinate validation
        validation = map_service.validate_coordinates(12.9716, 77.5946)
        
        if validation.is_valid:
            logger.info(f"✅ Coordinate validation works: {validation.hobli_name}")
            return True
        else:
            logger.error(f"❌ Coordinate validation failed: {validation.error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ MapService test failed: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("Running Precision AgriAI App Tests")
    logger.info("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Service Initialization", test_service_initialization),
        ("MapService", test_map_service),
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n--- Testing: {name} ---")
        result = test_func()
        results.append((name, result))
        logger.info("")
    
    logger.info("="*60)
    logger.info("Test Results Summary")
    logger.info("="*60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        logger.info("\n🎉 All tests passed! App is ready to run.")
        logger.info("\nTo start the app, run:")
        logger.info("  streamlit run app.py")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Please fix errors before running the app.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
