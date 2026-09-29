import unittest
from pathlib import Path


class ContinuousVoiceSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[2] / "web" / "assets" / "app.js").read_text(encoding="utf-8")

    def test_state_machine_contains_required_transitions(self):
        for state in ("IDLE", "LISTENING", "SPEAKING", "PROCESSING", "AI_RESPONDING"):
            self.assertIn(f"{state}:'{state}'", self.source)
        for transition in ("LISTENING", "SPEAKING", "PROCESSING", "AI_RESPONDING"):
            self.assertIn(f"setVoiceState(VOICE_STATE.{transition})", self.source)

    def test_silence_detection_is_configured_and_bounds_utterances(self):
        for setting in ("rmsThreshold", "silenceMs", "minUtteranceMs", "speechStartDebounceMs", "ttsCooldownMs", "maxUtteranceMs"):
            self.assertIn(setting, self.source)
        self.assertIn("silenceMs:2000", self.source)
        self.assertIn("minUtteranceMs:1000", self.source)
        self.assertIn("speechStartDebounceMs:250", self.source)
        self.assertIn("ttsCooldownMs:700", self.source)
        self.assertIn("getByteTimeDomainData", self.source)
        self.assertIn("now-voice.lastVoiceAt>=VOICE_CONFIG.silenceMs", self.source)

    def test_speech_start_requires_debounce_and_short_pause_does_not_stop(self):
        monitor = self._function("function monitorVoice", "function startUtterance")
        self.assertIn("voice.speechStartedAt??=now", monitor)
        self.assertIn("now-voice.speechStartedAt>=VOICE_CONFIG.speechStartDebounceMs", monitor)
        self.assertIn("elapsed>=VOICE_CONFIG.minUtteranceMs&&now-voice.lastVoiceAt>=VOICE_CONFIG.silenceMs", monitor)

    def test_each_utterance_has_an_id_and_can_submit_once(self):
        start = self._function("function startUtterance", "function stopUtterance")
        stopped = self._function("async function handleUtteranceStopped", "function resumeListening")
        self.assertIn("id:++voice.utteranceCounter", start)
        self.assertIn("submitted:false", start)
        self.assertIn("utterance.stopped", stopped)
        self.assertIn("utterance.submitted=true", stopped)
        self.assertIn("duplicate stop ignored", stopped)
        self.assertIn("SUBMIT", stopped)

    def test_monitor_is_singleton_and_processing_states_pause_it(self):
        monitor = self._function("function startVoiceMonitor", "function startUtterance")
        self.assertIn("voice.monitorRunning", monitor)
        self.assertIn("voice.monitorGeneration", monitor)
        self.assertIn("VOICE_STATE.LISTENING&&voice.state!==VOICE_STATE.SPEAKING", monitor)
        self.assertIn("monitor already running", self.source)

    def test_processing_and_ai_responding_cannot_start_a_recorder(self):
        start = self._function("function startUtterance", "function stopUtterance")
        submit = self._function("async function submitUtterance", "function wait")
        self.assertIn("voice.state!==VOICE_STATE.LISTENING", start)
        self.assertIn("setVoiceState(VOICE_STATE.PROCESSING)", submit)
        self.assertIn("setVoiceState(VOICE_STATE.AI_RESPONDING)", submit)

    def test_tts_stops_any_recorder_and_uses_cooldown_before_listening(self):
        cooldown = self._function("function startTtsCooldown", "function stopRecorderForTts")
        submit = self._function("async function submitUtterance", "function wait")
        self.assertIn("stopRecorderForTts();await playTurnAudio", submit)
        self.assertIn("voice.cooldownUntil=performance.now()+VOICE_CONFIG.ttsCooldownMs", cooldown)
        self.assertIn("setTimeout", cooldown)
        self.assertIn("resumeListening()", cooldown)

    def test_audio_submission_uses_existing_audio_endpoint_not_turn_endpoint(self):
        start = self.source.index("async function submitUtterance")
        end = self.source.index("function wait", start)
        submit = self.source[start:end]
        self.assertIn("/audio", submit)
        self.assertIn("messages.push(data.turn)", submit)
        self.assertNotIn("/turn", submit)
        self.assertNotIn("session.speak", submit)

    def test_failure_and_system_error_resume_listening(self):
        start = self.source.index("async function submitUtterance")
        end = self.source.index("function wait", start)
        submit = self.source[start:end]
        self.assertIn("data.turn.system_error", submit)
        self.assertIn("startTtsCooldown()", submit)
        self.assertIn("resumeListening(message)", submit)

    def test_stop_releases_recorder_tracks_and_audio_context(self):
        start = self.source.index("function releaseVoiceResources")
        end = self.source.index("function stopContinuousVoice", start)
        cleanup = self.source[start:end]
        for cleanup_call in ("cancelAnimationFrame", "voice.recorder.stop()", "getTracks().forEach(track=>track.stop())", "voice.context?.close?.()", "clearTimeout", "voice.monitorGeneration=++voiceGeneration"):
            self.assertIn(cleanup_call, cleanup)

    def test_repeated_utterances_keep_one_audio_submission_per_utterance(self):
        stopped = self._function("async function handleUtteranceStopped", "function resumeListening")
        submit = self._function("async function submitUtterance", "function wait")
        self.assertEqual(stopped.count("await submitUtterance(blob,utterance)"), 1)
        self.assertEqual(submit.count("/audio"), 1)

    def test_observation_captures_the_browser_visible_voice_lifecycle(self):
        for field in (
            "startedAt",
            "stoppedAt",
            "audioRequestStartedAt",
            "audioResponseAt",
            "ttsStartedAt",
            "ttsResponseAt",
            "playbackStartedAt",
            "playbackEndedAt",
        ):
            self.assertIn(field, self.source)
        self.assertIn("observation:createVoiceObservation(voice.utteranceCounter,now)", self.source)
        self.assertIn("performance.now()", self.source)

    def test_observation_calculates_response_and_full_turn_durations(self):
        complete = self._function("function completeVoiceObservation", "function startUtterance")
        for metric in (
            "speech",
            "audioResponseLatency",
            "responseLatency",
            "ttsLatency",
            "playbackDuration",
            "totalTurnDuration",
        ):
            self.assertIn(metric, complete)
        self.assertIn("difference(observation.playbackStartedAt,observation.stoppedAt)", complete)
        self.assertIn("difference(observation.playbackEndedAt,observation.startedAt)", complete)

    def test_tts_playback_records_start_end_and_keeps_null_response_without_start(self):
        playback = self._function("async function playTurnAudio", "function releasePlayback")
        self.assertIn("observation.playbackStartedAt=performance.now()", playback)
        self.assertIn("observation.playbackEndedAt=performance.now()", playback)
        self.assertIn("end!==null&&start!==null?Math.round(end-start):null", self.source)
        self.assertIn("observation.ttsFailed=true", playback)

    def test_observations_are_isolated_and_limited_to_recent_twenty(self):
        complete = self._function("function completeVoiceObservation", "function startUtterance")
        self.assertIn("VOICE_PERF_HISTORY_LIMIT=20", self.source)
        self.assertIn("voice.performanceHistory.push(observation)", complete)
        self.assertIn("voice.performanceHistory.splice(0,voice.performanceHistory.length-VOICE_PERF_HISTORY_LIMIT)", complete)
        self.assertIn("[VoicePerf]", complete)

    def _function(self, start_marker, end_marker):
        start = self.source.index(start_marker)
        end = self.source.index(end_marker, start)
        return self.source[start:end]


if __name__ == "__main__":
    unittest.main()
