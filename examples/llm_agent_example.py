"""
Example: LLM Agent Using Vajra Stream Tools

Demonstrates how an LLM agent can autonomously guide a user through their
"radionics journey" using tool calling.

This simulates an LLM agent responding to user requests by calling appropriate
tools and providing guidance.
"""

import time
from backend.core.llm_agent import (
    create_rng_session,
    get_rng_reading,
    create_blessing_slideshow,
    create_population,
    list_populations,
    start_automation,
    get_automation_status,
    get_tool_schemas
)


class VajraStreamAgent:
    """
    Simulated LLM Agent for Vajra Stream

    In practice, this would be an actual LLM (Claude, GPT-4, etc.) with access
    to the tool schemas and tool-calling capability.
    """

    def __init__(self):
        self.context = {
            "active_sessions": {},
            "user_preferences": {}
        }

    def handle_request(self, user_message: str) -> str:
        """
        Process user request and call appropriate tools.

        In a real system, this would:
        1. Pass user message + tool schemas to LLM
        2. LLM decides which tools to call
        3. Execute tools and return results to LLM
        4. LLM formats final response to user
        """
        user_message_lower = user_message.lower()

        # Example 1: User wants to monitor RNG
        if "rng" in user_message_lower or "floating needle" in user_message_lower:
            return self._handle_rng_request()

        # Example 2: User wants to bless photos
        elif "bless" in user_message_lower and "photo" in user_message_lower:
            return self._handle_blessing_request()

        # Example 3: User wants automation
        elif "automat" in user_message_lower or "24/7" in user_message_lower:
            return self._handle_automation_request()

        # Example 4: User wants status
        elif "status" in user_message_lower or "how" in user_message_lower:
            return self._handle_status_request()

        else:
            return self._explain_capabilities()

    def _handle_rng_request(self) -> str:
        """Handle RNG monitoring request"""
        try:
            # Tool call: create_rng_session
            result = create_rng_session(baseline_tone_arm=5.0, sensitivity=1.0)
            session_id = result['session_id']
            self.context['active_sessions']['rng'] = session_id

            # Tool call: get_rng_reading (simulate monitoring)
            reading = get_rng_reading(session_id)

            response = f"""I've started RNG monitoring for you.

Current Reading:
- Tone Arm: {reading['tone_arm']:.1f}
- Needle Position: {reading['needle_position']:.1f}
- Needle State: {reading['needle_state']}
- Floating Needle Score: {reading['floating_needle_score']:.2f}

"""
            if reading['floating_needle_score'] > 0.6:
                response += "🎯 **Floating Needle detected!** This indicates a release or completion.\n"
            else:
                response += "Continue monitoring. I'll watch for a Floating Needle (score > 0.6).\n"

            response += f"\nSession ID: {session_id}"
            return response

        except Exception as e:
            return f"Error starting RNG session: {str(e)}"

    def _handle_blessing_request(self) -> str:
        """Handle blessing slideshow request"""
        # In real system, would ask for directory path
        # For demo, we'll return guidance
        return """To bless photos, I need:

1. **Directory Path**: Where are your photos located?
   Example: /home/user/photos/refugees

2. **Mantra**: Which mantra would you like?
   Options: chenrezig (compassion), tara (swift compassion),
   medicine_buddha (healing), etc.

3. **Intentions**: What intentions to transmit?
   Examples: love, healing, peace, protection, reunion

4. **RNG Monitoring**: Should I monitor RNG during blessing? (recommended)

Please provide the directory path and I'll create the slideshow for you.

*Example*: "Bless photos in /home/user/photos using Chenrezig mantra with love and healing intentions"
"""

    def _handle_automation_request(self) -> str:
        """Handle automation request"""
        try:
            # Tool call: list_populations
            populations = list_populations(active_only=True)

            if not populations:
                return """You don't have any populations set up yet!

To start automation, first create populations:

**Example populations you could create**:
1. Missing Persons - for people who are lost
2. Refugees - for displaced populations
3. Disaster Victims - for those affected by natural disasters
4. Hospital Patients - for healing (with permission)

Would you like me to help you create a population first?
"""

            # Tool call: start_automation
            result = start_automation(
                duration_per_population=1800,  # 30 minutes each
                continuous_mode=True,
                link_rng=True
            )

            session_id = result['session_id']
            self.context['active_sessions']['automation'] = session_id

            return f"""Automated blessing rotation started! 🙏

**Configuration**:
- Mode: Round Robin (fair time distribution)
- Duration per population: 30 minutes
- Populations in queue: {result['populations_in_queue']}
- RNG monitoring: Enabled
- Continuous mode: Yes (runs indefinitely)

The system will now:
1. Bless each population for 30 minutes
2. Monitor RNG for psychoenergetic feedback
3. Track all statistics
4. Automatically transition between populations
5. Loop back to start after completing all

Session ID: {session_id}

You can check status anytime by asking "How's the automation going?"
"""

        except Exception as e:
            return f"Error starting automation: {str(e)}"

    def _handle_status_request(self) -> str:
        """Handle status inquiry"""
        automation_id = self.context['active_sessions'].get('automation')

        if not automation_id:
            return "No automation is currently running. Would you like to start automated blessing rotation?"

        try:
            # Tool call: get_automation_status
            status = get_automation_status(automation_id)

            current_pop = status.get('current_population')
            if current_pop:
                pop_name = current_pop['name']
                category = current_pop['category']
                progress = status['progress_percentage']
                elapsed = status['elapsed_seconds']

                return f"""Automation Status: {status['status'].title()} ✨

**Currently Blessing**: {pop_name}
- Category: {category}
- Progress: {progress:.1f}% complete
- Time elapsed: {int(elapsed // 60)} minutes

The system is working beautifully. Mantras and intentions are being
transmitted with precision. Continue letting it run, or I can provide
more detailed statistics if you'd like.
"""
            else:
                return "Automation is running but not currently on a population (possibly in transition)."

        except Exception as e:
            return f"Error getting status: {str(e)}"

    def _explain_capabilities(self) -> str:
        """Explain what the agent can do"""
        return """I can help you with your radionics journey! Here's what I can do:

**RNG Monitoring** 🎲
- Start RNG attunement session
- Monitor for floating needles (release indicators)
- Provide real-time psychoenergetic feedback

**Blessing Photos** 🙏
- Create blessing slideshows for photos
- Overlay mantras and intentions
- Use 10Hz alpha-wave pulsing for maximum effect
- Link RNG monitoring for feedback

**Population Management** 👥
- Create target populations (refugees, missing persons, etc.)
- Organize and prioritize blessing targets
- Track statistics per population

**Automated Rotation** ⚙️
- 24/7 automated blessing through all populations
- Fair time distribution (Round Robin)
- Integrated RNG monitoring
- Complete statistics tracking

**What would you like to do?**
- "Monitor RNG for floating needle"
- "Bless photos in [directory]"
- "Start automated rotation"
- "Show me the status"
- "Create a population for [group]"
"""


def main():
    """
    Example conversation demonstrating LLM agent using tools
    """
    print("=" * 70)
    print("Vajra Stream LLM Agent Example")
    print("Demonstrating autonomous tool calling for radionics practice")
    print("=" * 70)
    print()

    agent = VajraStreamAgent()

    # Example conversation
    conversations = [
        "What can you do?",
        "Start monitoring RNG for floating needle",
        "How's everything going?",
        "Start automated rotation"
    ]

    for user_msg in conversations:
        print(f"USER: {user_msg}")
        print()
        response = agent.handle_request(user_msg)
        print(f"AGENT: {response}")
        print()
        print("-" * 70)
        print()
        time.sleep(1)  # Simulate thinking time

    print("\n" + "=" * 70)
    print("Example complete!")
    print("=" * 70)

    # Show available tool schemas
    print("\nAvailable Tool Schemas for LLMs:")
    print("=" * 70)
    schemas = get_tool_schemas()
    for schema in schemas[:3]:  # Show first 3 as example
        print(f"\n{schema['name']}:")
        print(f"  Description: {schema['description']}")
        print(f"  Parameters: {list(schema['parameters']['properties'].keys())}")

    print(f"\n... and {len(schemas) - 3} more tools available!")


if __name__ == "__main__":
    print("\n" + "🔷" * 35)
    print("\n  This example requires the Vajra Stream backend to be running:")
    print("  uvicorn backend.app.main:app --reload")
    print("\n" + "🔷" * 35 + "\n")

    # Uncomment to run (requires backend running):
    # main()

    print("\nTool schemas can be used with any LLM that supports function calling:")
    print("- Claude (Anthropic) via Messages API with tools")
    print("- GPT-4 (OpenAI) via Chat Completions with functions")
    print("- Other compatible LLMs")
    print("\nThe tools.py module provides the complete interface.")
