"""
Protocol Selector — intelligent condition-to-protocol mapping.

Selects the best healing protocol for a given condition by cross-referencing
the chakra, meridian, and Tibetan channel data in :mod:`core.healing_systems`.
Produces structured protocol dicts containing frequencies, mantras, colours,
practices, dietary suggestions, and timing recommendations.

Dependencies:
    :mod:`core.healing_systems` — ChakraSystem, MeridianSystem, TibetanChannelSystem.

Exports:
    ProtocolSelector — main selector class.
    ConditionProtocol — dataclass for structured protocol results.
"""

from dataclasses import dataclass, field

try:
    from core.healing_systems import ChakraSystem, MeridianSystem, TibetanChannelSystem

    HAS_HEALING = True
except ImportError:
    HAS_HEALING = False


@dataclass
class ConditionProtocol:
    """Structured protocol for a specific condition.

    Attributes:
        condition: Human-readable condition name.
        chakras: List of chakra Sanskrit names involved.
        meridians: List of meridian keys involved.
        frequencies: Recommended audio frequencies (Hz).
        mantras: Recommended seed mantras or full mantras.
        colours: Recommended colour therapy colours.
        practices: List of healing practice descriptions.
        dietary: List of dietary suggestions.
        timing: Optional timing recommendation (e.g. best meridian hour).
        severity: Estimated severity of the condition mapping (0.0–1.0).
    """

    condition: str
    chakras: list[str] = field(default_factory=list)
    meridians: list[str] = field(default_factory=list)
    frequencies: list[float] = field(default_factory=list)
    mantras: list[str] = field(default_factory=list)
    colours: list[str] = field(default_factory=list)
    practices: list[str] = field(default_factory=list)
    dietary: list[str] = field(default_factory=list)
    timing: str | None = None
    severity: float = 0.5


class ProtocolSelector:
    """Select and generate healing protocols based on conditions.

    Uses the data models from :mod:`core.healing_systems` to cross-reference
    conditions across chakra, meridian, and Tibetan systems, producing
    unified :class:`ConditionProtocol` objects.

    Attributes:
        chakra_system: :class:`ChakraSystem` instance.
        meridian_system: :class:`MeridianSystem` instance.
        tibetan_system: :class:`TibetanChannelSystem` instance.
    """

    def __init__(self):
        if HAS_HEALING:
            self.chakra_system = ChakraSystem()
            self.meridian_system = MeridianSystem()
            self.tibetan_system = TibetanChannelSystem()
        else:
            self.chakra_system = None
            self.meridian_system = None
            self.tibetan_system = None

    def select_protocol(self, condition: str) -> ConditionProtocol:
        """Select the best protocol for a given condition.

        Queries each healing system for relevant chakras/meridians, then
        aggregates frequencies, mantras, colours, and practices into a
        single :class:`ConditionProtocol`.

        Args:
            condition: Condition name (e.g. ``"anxiety"``, ``"lower_back_pain"``).

        Returns:
            ConditionProtocol with aggregated recommendations.
        """
        protocol = ConditionProtocol(condition=condition)

        if not self.chakra_system:
            return protocol

        # --- Chakra mapping ---
        chakra_names = self.chakra_system.get_chakra_for_condition(condition)
        protocol.chakras = chakra_names

        for name in chakra_names:
            chakra = self.chakra_system.chakras.get(name, {})
            if chakra.get("frequency"):
                protocol.frequencies.append(float(chakra["frequency"]))
            if chakra.get("seed_mantra"):
                protocol.mantras.append(chakra["seed_mantra"])
            if chakra.get("color"):
                protocol.colours.append(chakra["color"])
            if chakra.get("healing_practices"):
                protocol.practices.extend(chakra["healing_practices"])

        # --- Meridian mapping ---
        meridian_names = self.meridian_system.get_meridian_for_condition(condition) if self.meridian_system else []
        protocol.meridians = meridian_names

        # --- Timing recommendation ---
        if meridian_names:
            # Suggest the active hour of the first meridian
            first_m = meridian_names[0]
            meridian_data = self.meridian_system.primary_meridians.get(first_m, {})
            if meridian_data.get("time_active"):
                protocol.timing = meridian_data["time_active"]

        # --- Deduplicate and clean ---
        protocol.frequencies = list(dict.fromkeys(protocol.frequencies))
        protocol.mantras = list(dict.fromkeys(protocol.mantras))
        protocol.colours = list(dict.fromkeys(protocol.colours))
        protocol.practices = list(dict.fromkeys(protocol.practices))

        return protocol

    def select_multi_condition(self, conditions: list[str]) -> ConditionProtocol:
        """Select a combined protocol for multiple conditions.

        Merges protocols from all conditions, deduplicating frequencies,
        mantras, and practices. The condition name is set to the joined list.

        Args:
            conditions: List of condition names.

        Returns:
            ConditionProtocol merging all individual protocols.
        """
        if not conditions:
            return ConditionProtocol(condition="none")

        merged = ConditionProtocol(condition=", ".join(conditions))

        for cond in conditions:
            proto = self.select_protocol(cond)
            merged.chakras.extend(proto.chakras)
            merged.meridians.extend(proto.meridians)
            merged.frequencies.extend(proto.frequencies)
            merged.mantras.extend(proto.mantras)
            merged.colours.extend(proto.colours)
            merged.practices.extend(proto.practices)
            merged.dietary.extend(proto.dietary)

        # Deduplicate
        merged.chakras = list(dict.fromkeys(merged.chakras))
        merged.meridians = list(dict.fromkeys(merged.meridians))
        merged.frequencies = list(dict.fromkeys(merged.frequencies))
        merged.mantras = list(dict.fromkeys(merged.mantras))
        merged.colours = list(dict.fromkeys(merged.colours))
        merged.practices = list(dict.fromkeys(merged.practices))

        return merged

    def get_available_conditions(self) -> list[str]:
        """Return all conditions that have at least one chakra or meridian mapping.

        Returns:
            Sorted list of condition names.
        """
        # Known conditions from ChakraSystem.get_chakra_for_condition
        known = [
            "anxiety",
            "depression",
            "anger",
            "grief",
            "fear",
            "lower_back_pain",
            "digestive_issues",
            "heart_disease",
            "thyroid",
            "headache",
        ]
        return sorted(known)


if __name__ == "__main__":
    print("Testing Protocol Selector")
    print("=" * 60)

    selector = ProtocolSelector()

    print("\nAvailable conditions:", ", ".join(selector.get_available_conditions()))

    for cond in ["anxiety", "headache", "grief"]:
        print(f"\n--- Protocol for {cond} ---")
        proto = selector.select_protocol(cond)
        print(f"  Chakras: {proto.chakras}")
        print(f"  Meridians: {proto.meridians}")
        print(f"  Frequencies: {proto.frequencies} Hz")
        print(f"  Mantras: {proto.mantras}")
        print(f"  Colours: {proto.colours}")
        print(f"  Practices: {proto.practices[:3]}...")
        if proto.timing:
            print(f"  Best time: {proto.timing}")

    print("\n--- Multi-condition (anxiety + headache) ---")
    multi = selector.select_multi_condition(["anxiety", "headache"])
    print(f"  Combined frequencies: {multi.frequencies}")
    print(f"  Combined chakras: {multi.chakras}")
