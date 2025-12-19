"""
MikesCaptionBuddy - All-in-One Caption Studio
Version 2.2

A desktop application for creating visually engaging video captions
with Whisper transcription, word-level styling, and karaoke effects.
"""

# Suppress known library warnings
import warnings
warnings.filterwarnings("ignore", message="PySoundFile failed")
warnings.filterwarnings("ignore", message="librosa.core.audio.__audioread_load")
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
warnings.filterwarnings("ignore", category=FutureWarning, module="librosa")
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")

__version__ = "2.2.0"
__author__ = "Mike"
__app_name__ = "MikesCaptionBuddy"
