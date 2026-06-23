import threading


class VoiceRegistry:
    """Tracks which system voices are enabled for MCP use and which agents have
    claimed them.

    The user enables/disables voices in the GUI's Voice Settings, and the GUI
    reserves the voice currently selected in its dropdown via
    ``set_user_voice``. Agents then claim a voice via the MCP server: they take
    unused (non-user) voices first, and once those run out they reuse a voice
    another *agent* already claimed (never the user's), requiring an ``agent``
    label so the shared voice can be attributed. The user's reserved voice is
    only handed to an agent when it is the only enabled voice. Thread-safe: the
    MCP server calls this from worker threads while the GUI updates it from the
    main thread.
    """

    def __init__(self, enabled=None):
        self._lock = threading.RLock()
        self._enabled = list(enabled or [])  # list of (id, name)
        self._claims = {}                    # voice_id -> [agent, ...]
        self._agent_voice = {}               # agent -> voice_id
        self._user_voice = None              # voice reserved for the GUI user

    def set_enabled(self, voices):
        """Replace the set of MCP-enabled voices, dropping stale claims."""
        with self._lock:
            self._enabled = list(voices)
            enabled_ids = {vid for vid, _ in self._enabled}
            for vid in list(self._claims):
                if vid not in enabled_ids:
                    for agent in self._claims.pop(vid):
                        self._agent_voice.pop(agent, None)
            if self._user_voice not in enabled_ids:
                self._user_voice = None

    def set_user_voice(self, voice_id):
        """Reserve the voice the GUI user has selected so agents avoid it.

        Agents only get this voice when it is the sole enabled voice.
        """
        with self._lock:
            self._user_voice = voice_id

    def enabled(self):
        with self._lock:
            return list(self._enabled)

    def status(self):
        with self._lock:
            result = []
            for vid, name in self._enabled:
                holders = list(self._claims.get(vid, []))
                if vid == self._user_voice:
                    holders = ["user"] + holders
                result.append({"id": vid, "name": name, "claimed_by": holders})
            return result

    def name_of(self, voice_id):
        with self._lock:
            for vid, name in self._enabled:
                if vid == voice_id:
                    return name
        return voice_id

    def resolve(self, voice):
        """Map a voice id or display name to an enabled voice id, or None."""
        with self._lock:
            for vid, name in self._enabled:
                if voice == vid or voice == name:
                    return vid
        return None

    def voice_for(self, agent):
        with self._lock:
            return self._agent_voice.get(agent)

    def resolve_for_speak(self, agent=None, voice=None):
        """Resolve the voice id to speak with, enforcing the claim handshake.

        - An explicit ``voice`` (name or id) always wins (raises if unknown).
        - Otherwise an ``agent`` must have reserved a voice via ``claim``.
        - If exactly one voice is enabled, it is used without a reservation.
        - If no voices are enabled at all, returns ``None`` (use the engine
          default) so the standalone server still works.
        Raises ``ValueError`` with handshake guidance when a reservation is
        required but missing.
        """
        with self._lock:
            if voice:
                vid = self.resolve(voice)
                if vid is None:
                    raise ValueError(
                        "Unknown voice '%s'. Call list_voices() to see options." % voice)
                return vid
            if not self._enabled:
                return None  # nothing to reserve; use the engine default
            if agent:
                vid = self._agent_voice.get(agent)
                if vid is not None:
                    return vid
                if len(self._enabled) == 1:
                    return self._enabled[0][0]
                raise ValueError(
                    "Agent '%s' has not reserved a voice. Call claim_voice(agent='%s') "
                    "first, then speak with that same agent." % (agent, agent))
            if len(self._enabled) == 1:
                return self._enabled[0][0]
            raise ValueError(
                "No voice reserved. First call claim_voice(agent='<your repo folder or "
                "current task>') to reserve a voice, then call speak with that same agent.")

    def release(self, agent):
        with self._lock:
            vid = self._agent_voice.pop(agent, None)
            holders = self._claims.get(vid)
            if holders and agent in holders:
                holders.remove(agent)
                if not holders:
                    self._claims.pop(vid, None)
            return vid

    def claim(self, agent=None, voice=None):
        """Claim a voice for an agent.

        Returns ``{id, name, agent, shared, reused}``. Raises ``ValueError`` (with
        guidance) when no voices are enabled, a requested voice is unknown or
        taken, or every voice is in use and no ``agent`` label was supplied.
        """
        with self._lock:
            if not self._enabled:
                raise ValueError(
                    "No voices are enabled for MCP use. Open SpeedReader > Voice Settings "
                    "and enable at least one voice.")

            # A named agent that already holds a voice keeps it (idempotent).
            if agent and agent in self._agent_voice:
                vid = self._agent_voice[agent]
                return self._result(vid, agent, shared=len(self._claims.get(vid, [])) > 1, reused=False)

            requested = self.resolve(voice) if voice else None
            if voice and requested is None:
                raise ValueError(
                    "Unknown voice '%s'. Enabled voices: %s"
                    % (voice, [name for _, name in self._enabled]))

            only_voice = len(self._enabled) == 1
            # Unused voices an agent may take: not already claimed, and not the
            # user's reserved voice (unless it is the only enabled voice).
            free = [
                vid for vid, _ in self._enabled
                if not self._claims.get(vid) and (only_voice or vid != self._user_voice)
            ]
            if free:
                if requested is not None and requested not in free:
                    if requested == self._user_voice and not only_voice:
                        raise ValueError(
                            "Voice '%s' is reserved for the application user."
                            % self.name_of(requested))
                    raise ValueError(
                        "Voice '%s' is already in use. Free voices: %s"
                        % (self.name_of(requested), [self.name_of(v) for v in free]))
                vid = requested if requested is not None else free[0]
                self._assign(vid, agent)
                return self._result(vid, agent or "anonymous", shared=False, reused=False)

            # Every assignable voice is taken: reuse requires an agent identifier.
            if not agent:
                raise ValueError(
                    "All %d enabled voices are in use. To share a voice, call claim_voice "
                    "again with an 'agent' identifier (e.g. the repo folder name or your "
                    "current task)." % len(self._enabled))
            # Reuse a voice another agent already claimed; fall back to the
            # user's voice only when no agent voice exists (i.e. one voice total).
            candidates = [vid for vid, _ in self._enabled if self._claims.get(vid)]
            if not candidates:
                candidates = [vid for vid, _ in self._enabled]
            if requested is not None and requested in candidates:
                vid = requested
            else:
                vid = self._least_shared(candidates)
            self._assign(vid, agent)
            return self._result(vid, agent, shared=True, reused=True)

    def _assign(self, voice_id, agent):
        label = agent or "anonymous"
        holders = self._claims.setdefault(voice_id, [])
        if label not in holders:
            holders.append(label)
        self._agent_voice[label] = voice_id

    def _least_shared(self, candidates):
        return min(candidates, key=lambda v: len(self._claims.get(v, [])))

    def _result(self, voice_id, agent, shared, reused):
        return {"id": voice_id, "name": self.name_of(voice_id), "agent": agent,
                "shared": shared, "reused": reused}
