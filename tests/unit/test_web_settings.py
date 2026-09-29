import unittest
from pathlib import Path


class WebSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[2] / "web" / "assets" / "app.js").read_text(encoding="utf-8")

    def test_defaults_and_local_storage_recovery_are_defined(self):
        for value in (
            "SETTINGS_STORAGE_KEY='ai-speaking-coach-settings'",
            "voice_name:'en-US-AriaNeural'",
            "speaking_rate:1",
            "auto_tts:true",
            "volume:1",
            "difficulty:'B2'",
            "session_duration:45",
            "english_only:false",
            "feedback_intensity:'light'",
            "theme:'dark'",
            "SPEAKING_RATES=[.7,.8,.9,1,1.1,1.2]",
            "function normalizeUserSettings",
            "function loadUserSettings",
            "JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY)||'{}')",
        ):
            self.assertIn(value, self.source)

    def test_settings_are_persisted_and_used_for_new_sessions(self):
        self.assertIn("localStorage.setItem(SETTINGS_STORAGE_KEY,JSON.stringify(userSettings))", self.source)
        create = self._function("async function createSession", "function settingsPage")
        for field in (
            "difficulty:settings.difficulty",
            "english_only:userSettings.coach.english_only",
            "feedback_intensity:userSettings.coach.feedback_intensity",
            "mode:settings.mode",
            "duration:settings.duration",
            "topic:settings.topic",
            "voice_name:userSettings.voice.voice_name",
            "speaking_rate:userSettings.voice.speaking_rate",
            "auto_tts:userSettings.voice.auto_tts",
            "volume:userSettings.voice.volume",
        ):
            self.assertIn(field, create)

    def test_call_setup_supports_modes_free_duration_and_optional_topic(self):
        for value in (
            "foreign_friend:{title:'自然聊天'",
            "teacher:{title:'教练模式'",
            "business_coach:{title:'专业模式'",
            "B1:'简单'",
            "B2:'中等'",
            "'B2+':'较难'",
            "C1:'难'",
            "{value:null,title:'自由聊天'",
            "settings.topic=document.querySelector('#topic')?.value.trim()||null",
        ):
            self.assertIn(value, self.source)

    def test_voice_settings_control_playback(self):
        submit = self._function("async function submitUtterance", "function wait")
        playback = self._function("async function playTurnAudio", "function releasePlayback")
        self.assertIn("else if(userSettings.voice.auto_tts)", submit)
        self.assertIn("playbackAudio.volume=userSettings.voice.volume", playback)
        self.assertIn("playTurnAudio(data.reply).catch(()=>{})", self.source)

    def _function(self, start_marker, end_marker):
        start = self.source.index(start_marker)
        end = self.source.index(end_marker, start)
        return self.source[start:end]


if __name__ == "__main__":
    unittest.main()
