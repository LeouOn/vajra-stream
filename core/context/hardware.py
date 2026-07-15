# core/context/hardware.py
"""Hardware / session context module."""

from __future__ import annotations

import logging

from core.context.models import ContextData, ContextRequest

logger = logging.getLogger(__name__)


class HardwareContextModule:
    """Gathers and renders hardware-status / session context."""

    name = "hardware"

    async def gather(self, request: ContextRequest) -> ContextData:
        """Collect system-status and session data, never raising."""
        if not request.include_hardware:
            return ContextData(module_name=self.name)

        try:
            from backend.core.services.vajra_service import vajra_service

            sys_status = vajra_service.get_system_status()
            sessions = vajra_service.get_all_sessions()
        except Exception as exc:  # noqa: BLE001
            logger.debug("vajra_service import failed: %s", exc)
            return ContextData(
                module_name=self.name,
                error="vajra_service unavailable",
            )

        try:
            # Normalize session list — extract name/type/status defensively.
            session_list: list[dict] = []
            if isinstance(sessions, dict):
                iterable = sessions.values()
            elif isinstance(sessions, list):
                iterable = sessions
            else:
                iterable = []
            for s in iterable:
                if not isinstance(s, dict):
                    continue
                config = s.get("config")
                name = None
                if config is not None:
                    name = getattr(config, "name", None) or (config.get("name") if isinstance(config, dict) else None)
                session_list.append(
                    {
                        "name": name or s.get("name", "unnamed"),
                        "type": s.get("type", "session"),
                        "status": s.get("status", "unknown"),
                    }
                )

            return ContextData(
                module_name=self.name,
                data={
                    "system_status": sys_status,
                    "sessions": session_list,
                    "session_count": len(session_list),
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("hardware gather failed: %s", exc)
            return ContextData(module_name=self.name, error=str(exc))

    def render(self, data: ContextData) -> str:
        """Render hardware / session Markdown."""
        d = data.data
        if not d:
            return ""
        lines: list[str] = ["### Hardware & Session Context", ""]

        try:
            self._render_system_status(d, lines)
            self._render_sessions(d, lines)
        except Exception as exc:  # noqa: BLE001
            logger.warning("hardware render failed: %s", exc)
            return ""

        if len(lines) <= 2:
            return ""
        return "\n".join(lines) + "\n"

    # -- render helpers -----------------------------------------------------

    @staticmethod
    def _render_system_status(d: dict, lines: list[str]) -> None:
        status = d.get("system_status")
        if not status:
            return
        lines.append("**System Status:**")
        enhanced = status.get("enhanced_mode", False)
        lines.append(f"  - Enhanced mode: {'ON' if enhanced else 'OFF'}")
        active = status.get("active_sessions", 0)
        lines.append(f"  - Active sessions: {active}")
        audio = status.get("current_audio", False)
        lines.append(f"  - Audio streaming: {'ON' if audio else 'OFF'}")
        spectrum = status.get("spectrum_available", False)
        lines.append(f"  - Spectrum available: {'yes' if spectrum else 'no'}")
        modules = status.get("modules_loaded", {})
        if modules:
            loaded = [k for k, v in modules.items() if v]
            if loaded:
                lines.append(f"  - Modules loaded: {', '.join(loaded)}")
        lines.append("")

    @staticmethod
    def _render_sessions(d: dict, lines: list[str]) -> None:
        sessions = d.get("sessions")
        if not sessions:
            return
        lines.append("**Sessions:**")
        for s in sessions:
            name = s.get("name", "unnamed")
            stype = s.get("type", "session")
            status = s.get("status", "unknown")
            lines.append(f"  - {name} ({stype}): {status}")
        lines.append("")
