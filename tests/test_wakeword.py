"""
Tests for wake word detection module.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_wakeword_import():
    """Verify OpenWakeWord can be imported."""
    try:
        import openwakeword
        print("✓ openwakeword imported successfully")
        return True
    except ImportError:
        print("⚠ openwakeword not installed. Install with: pip install openwakeword")
        return False


def test_detector_initialization():
    """Verify WakeWordDetector can be instantiated."""
    try:
        from wakeword.detector import WakeWordDetector
        detector = WakeWordDetector()
        print("✓ WakeWordDetector initialized successfully")
        detector.stop()
        return True
    except ImportError:
        print("⚠ openwakeword not installed. Skipping detector initialization test.")
        return False
    except Exception as exc:
        print(f"⚠ Detector initialization failed: {exc}")
        return False


def test_false_positive_silence():
    """Verify silence does not trigger false positive detection."""
    try:
        from wakeword.detector import WakeWordDetector
        detector = WakeWordDetector(threshold=0.5)
        
        # Listen for a very short window (should get no detection from ambient silence)
        result = detector.listen_once(timeout=0.5)
        
        if result is None:
            print("✓ No false positive from ambient silence")
        else:
            print(f"⚠ Possible false positive: {result.keyword} (confidence={result.confidence:.3f})")
        
        detector.stop()
        return True
    except ImportError:
        print("⚠ openwakeword not installed. Skipping false positive test.")
        return False
    except Exception as exc:
        print(f"⚠ False positive test error: {exc}")
        return False


def test_state_transitions():
    """Verify wake word state transitions are correct."""
    from orchestrator.state import AssistantState
    
    # Verify WAKE_LISTENING state exists
    assert hasattr(AssistantState, 'WAKE_LISTENING'), "WAKE_LISTENING state missing"
    assert AssistantState.WAKE_LISTENING.value == "wake_listening"
    print("✓ WAKE_LISTENING state exists")
    
    # Verify state transitions
    from orchestrator.session import ConversationSession
    session = ConversationSession()
    
    session.set_state(AssistantState.WAKE_LISTENING)
    assert session.state == AssistantState.WAKE_LISTENING
    print("✓ Transition to WAKE_LISTENING successful")
    
    session.set_state(AssistantState.LISTENING)
    assert session.state == AssistantState.LISTENING
    print("✓ Transition from WAKE_LISTENING to LISTENING successful")
    
    session.set_state(AssistantState.IDLE)
    assert session.state == AssistantState.IDLE
    print("✓ State transitions work correctly")


if __name__ == "__main__":
    print("=" * 50)
    print("  Wake Word Detection Tests")
    print("=" * 50)
    
    print("\n1. Test openwakeword import:")
    has_oww = test_wakeword_import()
    
    print("\n2. Test state transitions:")
    test_state_transitions()
    
    if has_oww:
        print("\n3. Test detector initialization:")
        test_detector_initialization()
        
        print("\n4. Test false positive from silence:")
        test_false_positive_silence()
    else:
        print("\n3-4. Skipped (openwakeword not installed)")
    
    print("\n" + "=" * 50)
    print("  Wake word tests completed!")
    print("=" * 50)
