#!/usr/bin/env python3
"""
Vajra.Stream Integrated Blessing
Combines prayer bowl audio with visual system
Complete blessing experience
"""

import sys
import os
import time
import threading

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.audio_generator import ScalarWaveGenerator
from core.visual_renderer_simple import SimpleVisualRenderer


class IntegratedBlessing:
    """
    Combines audio and visual systems
    """
    
    def __init__(self):
        self.audio = ScalarWaveGenerator()
        self.visual = SimpleVisualRenderer()
        self.running = False
        
    def start_blessing_session(self, intention="peace", duration=60):
        """
        Start blessing with both audio and visuals
        """
        print(f"\n{'='*60}")
        print("VAJRA.STREAM INTEGRATED BLESSING")
        print("="*60)
        print(f"Intention: {intention}")
        print(f"Duration: {duration} seconds")
        print(f"{'='*60}\n")
        
        self.running = True
        
        # Start audio in separate thread
        audio_thread = threading.Thread(
            target=self._run_audio,
            args=(intention, duration)
            daemon=True
        )
        
        # Start visuals in separate thread
        visual_thread = threading.Thread(
            target=self._run_visual,
            args=(intention, duration),
            daemon=True
        )
        
        # Start both threads
        audio_thread.start()
        visual_thread.start()
        
        print("Audio and visual systems started...")
        print("Press Ctrl+C to stop\n")
        
        try:
            # Wait for completion or interruption
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping blessing session...")
            self.running = False
            
            # Wait for threads to finish
            audio_thread.join(timeout=2)
            visual_thread.join(timeout=2)
            
            print("\nBlessing session completed.")
            print("Dedication: May all beings benefit from this practice.")
            print("="*60)
    
    def _run_audio(self, intention, duration):
        """
        Run audio blessing
        """
        # Generate prayer bowl frequencies
        frequencies = [7.83, 136.1, 528, 639, 741]
        
        # Generate combined wave
        wave = self.audio.layer_frequencies(
            [(f, 0.2) for f in frequencies],
            duration=duration
        )
        
        # Play audio
        self.audio.play(wave, loop=True)
        
        # Wait for duration
        time.sleep(duration)
        
        # Stop audio
        self.audio.stop()
    
    def _run_visual(self, intention, duration):
        """
        Run visual blessing
        """
        # Run simple mandala visualization
        self.visual.animate_mandala(duration_seconds=duration, intention=intention)


def main():
    """
    Main interface
    """
    print("\n" + "="*60)
    print("VAJRA.STREAM INTEGRATED BLESSING")
    print("="*60)
    
    blessing = IntegratedBlessing()
    
    print("\nSelect blessing type:")
    print("1. Peace (528Hz focus)")
    print("2. Healing (multiple frequencies)")
    print("3. Meditation (theta waves)")
    
    try:
        choice = int(input("\nEnter choice (1-3): "))
    except (ValueError, KeyboardInterrupt):
        print("\nExiting...")
        return
    
    print(f"\nStarting {choice} blessing...")
    
    if choice == 1:
        blessing.start_blessing_session(
            intention="May all beings be peaceful",
            duration=60
        )
    elif choice == 2:
        blessing.start_blessing_session(
            intention="May healing energy flow to all who need it",
            duration=90
        )
    else:
        blessing.start_blessing_session(
            intention="May all beings find deep peace and stillness",
            duration=120
        )
    
    print("\nBlessing complete!")
    print("May this practice benefit all beings. 🙏")


if __name__ == "__main__":
    main()