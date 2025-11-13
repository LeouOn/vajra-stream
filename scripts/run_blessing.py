#!/usr/bin/env python3
"""
Simple script to run blessing sessions
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.crystal_broadcaster import Level2CrystalBroadcaster, Level3AmplifiedBroadcaster


def main():
    parser = argparse.ArgumentParser(description='Run Vajra.Stream blessing session')
    
    parser.add_argument(
        '--intention',
        type=str,
        default='May all beings be happy and free from suffering',
        help='Intention/prayer for the session'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=300,
        help='Duration in seconds (default: 300 = 5 minutes)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['blessing', 'healing'],
        default='blessing',
        help='Mode: blessing or healing'
    )
    
    parser.add_argument(
        '--chakra',
        choices=['root', 'sacral', 'solar_plexus', 'heart', 'throat', 'third_eye', 'crown'],
        default='heart',
        help='Chakra to focus on (for healing mode)'
    )
    
    parser.add_argument(
        '--level',
        type=int,
        choices=[2, 3],
        default=2,
        help='Hardware level: 2=passive crystals, 3=amplified'
    )
    
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously until stopped (Ctrl+C)'
    )
    
    args = parser.parse_args()
    
    # Create broadcaster
    if args.level == 3:
        broadcaster = Level3AmplifiedBroadcaster()
        print("\n⚠️  Level 3: Ensure amplifier volume is at safe level (25-40%)\n")
    else:
        broadcaster = Level2CrystalBroadcaster()
    
    # Run session
    try:
        if args.continuous:
            broadcaster.continuous_blessing(args.intention)
        elif args.mode == 'healing':
            broadcaster.generate_chakra_healing(args.chakra, args.duration)
        else:
            if args.level == 3:
                broadcaster.generate_amplified_blessing(args.intention, args.duration)
            else:
                broadcaster.generate_5_channel_blessing(args.intention, args.duration)
    
    except KeyboardInterrupt:
        print("\n\nSession ended by user.")
        print("May all beings benefit. 🙏")


if __name__ == "__main__":
    main()
