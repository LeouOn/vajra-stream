"""
Vajra.Stream Crystal Broadcaster
Level 2: Passive crystal grid
Level 3: Amplified with bass shaker
Enhanced with prayer bowl synthesis as default
"""

import numpy as np
import sounddevice as sd
import time
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.audio_generator import ScalarWaveGenerator, INTENTION_TO_FREQUENCY


class Level2CrystalBroadcaster:
    """
    Software for crystal grid broadcasting
    No external electronics needed - just crystals + computer audio
    Enhanced with prayer bowl synthesis as default
    """
    
    def __init__(self, pure_sine=False):
        self.sample_rate = 44100
        self.channels = 2  # Stereo for left/right speakers
        self.audio_gen = ScalarWaveGenerator(self.sample_rate)
        self.pure_sine = pure_sine  # Flag for original sine wave mode
        
    def generate_5_channel_blessing(self, intention, duration=300):
        """
        Generate 5 simultaneous frequencies with prayer bowl synthesis
        Optimized for crystal grid resonance
        Default: prayer bowl style, set pure_sine=True for original
        """
        print(f"\n{'='*60}")
        print(f"VAJRA.STREAM - Crystal Grid Blessing")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Duration: {duration/60:.1f} minutes")
        print(f"Audio Mode: {'Pure Sine Waves' if self.pure_sine else 'Prayer Bowl Synthesis'}")
        print(f"Time: {datetime.now().strftime('%I:%M %p')}")
        print(f"\nPlace your written intention in the center well now.")
        print(f"{'='*60}\n")
        
        # 5 frequencies - each chosen for specific purpose
        frequencies = {
            'schumann': 7.83,      # Earth resonance
            'om': 136.1,           # Year of Earth frequency
            'love': 528,           # DNA healing/love
            'connection': 639,     # Relationships/connection
            'awakening': 741       # Intuition/awakening
        }
        
        print("Broadcasting frequencies:")
        for name, freq in frequencies.items():
            print(f"  {name.title()}: {freq} Hz")
        
        # Generate time array
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        # Create combined wave using prayer bowl synthesis
        wave = np.zeros_like(t)
        
        for freq in frequencies.values():
            if self.pure_sine:
                # Original simple sine wave
                wave += np.sin(2 * np.pi * freq * t)
            else:
                # Prayer bowl synthesis for each frequency
                bowl_tone = self.audio_gen.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
                wave += bowl_tone
        
        # Normalize
        wave = wave / len(frequencies)
        
        if self.pure_sine:
            # Original breathing effect
            breath_freq = 0.1  # 6 breaths per minute
            modulation = 0.85 + 0.15 * np.sin(2 * np.pi * breath_freq * t)
            wave = wave * modulation
        
        # Convert to stereo (same signal both channels)
        stereo_wave = np.column_stack([wave, wave])
        
        # Play
        print("\nBroadcasting now... (Ctrl+C to stop)\n")
        
        try:
            sd.play(stereo_wave, samplerate=self.sample_rate)
            sd.wait()
            
        except KeyboardInterrupt:
            sd.stop()
            print("\n\nBroadcast completed.")
            print("Dedication: May all beings benefit from this practice.")
            print(f"{'='*60}\n")
    
    def generate_chakra_healing(self, chakra='heart', duration=300):
        """
        Focused healing for specific chakra with prayer bowl synthesis
        """
        chakra_frequencies = {
            'root': 396,
            'sacral': 417,
            'solar_plexus': 528,
            'heart': 639,
            'throat': 741,
            'third_eye': 852,
            'crown': 963
        }
        
        base_freq = chakra_frequencies.get(chakra, 528)
        
        print(f"\n{'='*60}")
        print(f"CHAKRA HEALING - {chakra.upper()}")
        print(f"{'='*60}")
        print(f"Primary Frequency: {base_freq} Hz")
        print(f"Supporting: {7.83} Hz (Schumann)")
        print(f"Audio Mode: {'Pure Sine Waves' if self.pure_sine else 'Prayer Bowl Synthesis'}")
        
        if self.pure_sine:
            # Original approach
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            wave = np.sin(2 * np.pi * base_freq * t)
            wave += 0.3 * np.sin(2 * np.pi * 7.83 * t)
            wave = wave / 1.3
        else:
            # Prayer bowl synthesis
            wave = self.audio_gen.generate_prayer_bowl_tone(base_freq, duration, pure_sine=False)
            schumann = self.audio_gen.generate_prayer_bowl_tone(7.83, duration, pure_sine=False)
            wave = wave + 0.3 * schumann
            wave = wave / np.max(np.abs(wave))
        
        # Stereo
        stereo_wave = np.column_stack([wave, wave])
        
        print("\nHealing broadcast active...\n")
        
        sd.play(stereo_wave, samplerate=self.sample_rate)
        sd.wait()
    
    def continuous_blessing(self, intention):
        """
        Run blessing continuously (background mode)
        Loops indefinitely until stopped
        """
        print(f"\n{'='*60}")
        print(f"CONTINUOUS BLESSING MODE")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Audio Mode: {'Pure Sine Waves' if self.pure_sine else 'Prayer Bowl Synthesis'}")
        print(f"Mode: Infinite loop")
        print(f"Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        # Generate 5 minute segment
        segment_duration = 300
        
        while True:
            try:
                self.generate_5_channel_blessing(intention, segment_duration)
                
            except KeyboardInterrupt:
                print("\n\nContinuous blessing ended.")
                print("Total merit dedicated to all beings.")
                break


class Level3AmplifiedBroadcaster(Level2CrystalBroadcaster):
    """
    Enhanced version for amplified setup with bass shaker
    Optimized for prayer bowl synthesis
    """
    
    def __init__(self, pure_sine=False):
        super().__init__(pure_sine)
        self.bass_shaker_optimized = True
        
    def generate_amplified_blessing(self, intention, duration=300):
        """
        Optimized waveform for bass shaker with prayer bowl synthesis
        Lower frequencies emphasized for better tactile response
        """
        print(f"\n{'='*60}")
        print(f"VAJRA.STREAM - Amplified Crystal Broadcasting")
        print(f"Hardware: Amplifier + Bass Shaker + Crystal Grid")
        print(f"{'='*60}")
        print(f"Intention: {intention}")
        print(f"Audio Mode: {'Pure Sine Waves' if self.pure_sine else 'Prayer Bowl Synthesis'}")
        print(f"\n⚠️  Ensure amplifier volume is at safe level (25-40%)")
        print(f"{'='*60}\n")
        
        # Lower frequencies work better with bass shaker
        frequencies = {
            'schumann': 7.83,
            'theta': 6.0,         # Deep meditation
            'om': 136.1,
            'love': 528,
            'earth_day': 194.18   # Earth's daily rotation
        }
        
        print("Broadcasting frequencies:")
        for name, freq in frequencies.items():
            print(f"  {name.title()}: {freq} Hz")
        
        if self.pure_sine:
            # Original approach
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            wave = np.zeros_like(t)
            
            # Weight lower frequencies more for shaker
            for name, freq in frequencies.items():
                weight = 2.0 if freq < 100 else 1.0
                wave += weight * np.sin(2 * np.pi * freq * t)
            
            # Normalize
            wave = wave / np.max(np.abs(wave)) * 0.7
            
            # Add gentle pulse (earth heartbeat)
            pulse_freq = 1.2  # 72 bpm
            pulse = 0.9 + 0.1 * np.sin(2 * np.pi * pulse_freq * t)
            wave = wave * pulse
        else:
            # Prayer bowl synthesis optimized for bass shaker
            wave = np.zeros_like(t)
            
            for name, freq in frequencies.items():
                # Generate prayer bowl tone for each frequency
                bowl_tone = self.audio_gen.generate_prayer_bowl_tone(freq, duration, pure_sine=False)
                
                # Weight lower frequencies more for shaker
                weight = 2.0 if freq < 100 else 1.0
                wave += weight * bowl_tone
            
            # Normalize with headroom for amplifier
            wave = wave / np.max(np.abs(wave)) * 0.7
            
            # Add gentle pulse (earth heartbeat) - more subtle for prayer bowls
            t = np.linspace(0, duration, int(self.sample_rate * duration))
            pulse_freq = 0.8  # Slower pulse for prayer bowls
            pulse = 0.95 + 0.05 * np.sin(2 * np.pi * pulse_freq * t)
            wave = wave * pulse
        
        # Stereo (same both channels)
        stereo_wave = np.column_stack([wave, wave])
        
        print("\nBroadcasting through amplified crystal grid...")
        print("You may feel subtle vibrations in the platform.\n")
        
        try:
            sd.play(stereo_wave, samplerate=self.sample_rate)
            sd.wait()
        except KeyboardInterrupt:
            sd.stop()
            print("\n\nBroadcast completed.")
            print("Dedication: May all beings benefit from this practice.")
    
    def test_bass_shaker(self):
        """
        Test bass shaker function with prayer bowl frequency sweep
        """
        print(f"\n{'='*60}")
        print("BASS SHAKER TEST")
        print(f"{'='*60}")
        print("You should feel vibrations in the platform")
        if self.pure_sine:
            print("Frequency sweep: 5 Hz → 200 Hz over 30 seconds (sine waves)")
        else:
            print("Prayer bowl sweep: 5 Hz → 200 Hz over 30 seconds")
        print(f"{'='*60}\n")
        
        duration = 30
        start_freq = 5
        end_freq = 200
        
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        
        if self.pure_sine:
            # Original frequency sweep (chirp)
            freq_sweep = np.linspace(start_freq, end_freq, len(t))
            phase = 2 * np.pi * np.cumsum(freq_sweep) / self.sample_rate
            wave = np.sin(phase) * 0.5  # Medium volume
        else:
            # Prayer bowl frequency sweep
            wave = np.zeros_like(t)
            # Create multiple prayer bowl tones sweeping through frequency range
            for i in range(0, len(t), len(t)//10):  # 10 frequency steps
                step_duration = duration / 10
                step_start = i
                step_end = min(i + len(t)//10, len(t))
                if step_end > step_start:
                    freq = start_freq + (end_freq - start_freq) * (i / len(t))
                    step_t = np.linspace(0, step_duration, step_end - step_start)
                    step_wave = self.audio_gen.generate_prayer_bowl_tone(freq, step_duration, pure_sine=False)
                    wave[step_start:step_end] = step_wave[:step_end-step_start]
            
            wave = wave * 0.5  # Medium volume
        
        stereo_wave = np.column_stack([wave, wave])
        
        sd.play(stereo_wave, samplerate=self.sample_rate)
        sd.wait()
        
        print("\nTest complete!")
        print("Did you feel the vibrations change frequency?\n")


if __name__ == "__main__":
    # Determine hardware level
    print("\nVajra.Stream Crystal Broadcaster")
    print("="*60)
    print("\nSelect hardware level:")
    print("  2 - Passive crystal grid (speakers only)")
    print("  3 - Amplified (bass shaker + crystals)")
    
    try:
        level = int(input("\nHardware level (2 or 3): "))
    except (ValueError, KeyboardInterrupt):
        print("\nExiting...")
        sys.exit(0)
    
    # Ask for audio mode
    print("\nSelect audio mode:")
    print("  1 - Prayer Bowl Synthesis (default - rich harmonics)")
    print("  2 - Pure Sine Waves (original)")
    
    try:
        audio_mode = int(input("\nAudio mode (1 or 2, default 1): ") or "1")
        pure_sine = (audio_mode == 2)
    except (ValueError, KeyboardInterrupt):
        pure_sine = False
    
    if level == 3:
        broadcaster = Level3AmplifiedBroadcaster(pure_sine=pure_sine)
        
        print("\nWould you like to test the bass shaker first? (y/n)")
        test = input().lower()
        
        if test == 'y':
            broadcaster.test_bass_shaker()
    else:
        broadcaster = Level2CrystalBroadcaster(pure_sine=pure_sine)
    
    # Run blessing
    print("\nEnter intention (or press Enter for default):")
    intention = input().strip()
    
    if not intention:
        intention = "May all beings be happy and free from suffering"
    
    print("\nDuration in minutes (default 5):")
    try:
        minutes = float(input())
    except (ValueError, KeyboardInterrupt):
        minutes = 5
    
    duration = int(minutes * 60)
    
    # Run the broadcast
    if level == 3:
        broadcaster.generate_amplified_blessing(intention, duration)
    else:
        broadcaster.generate_5_channel_blessing(intention, duration)
