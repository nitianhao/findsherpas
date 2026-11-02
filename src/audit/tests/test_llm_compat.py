import unittest
from types import SimpleNamespace

from pydantic import BaseModel

from src import llm_compat
from src.llm_compat import LLMResponseError, response_text, structured_call, supports_temperature
from tests.helpers import FakeClient, FakeResponse, fake_text_response


class _Verdict(BaseModel):
    severity: str


class TemperatureTests(unittest.TestCase):
    def test_table(self):
        self.assertTrue(supports_temperature("claude-sonnet-4-6"))
        self.assertTrue(supports_temperature("claude-haiku-4-5-20251001"))
        self.assertFalse(supports_temperature("claude-sonnet-5-5"))
        self.assertFalse(supports_temperature("claude-opus-5"))
        self.assertTrue(supports_temperature("some-unknown-model"))


class ResponseTextTests(unittest.TestCase):
    def test_skips_thinking_and_joins_text(self):
        r = FakeResponse(stop_reason="end_turn", content=[
            SimpleNamespace(type="thinking", thinking="..."),
            SimpleNamespace(type="text", text="a"),
            SimpleNamespace(type="text", text="b"),
        ])
        self.assertEqual(response_text(r), "a\nb")

    def test_raises_on_truncation_refusal_and_empty(self):
        with self.assertRaises(LLMResponseError):
            response_text(fake_text_response("{\"partial\":", stop_reason="max_tokens"))
        with self.assertRaises(LLMResponseError):
            response_text(fake_text_response("", stop_reason="refusal"))
        with self.assertRaises(LLMResponseError):
            response_text(FakeResponse(stop_reason="end_turn", content=[]))


class StructuredCallTests(unittest.TestCase):
    def setUp(self):
        llm_compat.reset_usage()

    def _parsed(self, obj, stop="end_turn"):
        r = fake_text_response("{}", stop_reason=stop)
        r.parsed_output = obj
        return r

    def test_returns_parsed_and_records_usage(self):
        client = FakeClient([self._parsed(_Verdict(severity="PASS"))])
        out = structured_call(model="claude-sonnet-4-6", system="rules", user="data", schema=_Verdict,
                              max_tokens=100, phase="judge", temperature=0.2, client=client)
        self.assertEqual(out.severity, "PASS")
        call = client.messages.calls[0]
        self.assertIs(call["output_format"], _Verdict)
        self.assertEqual(call["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(call["temperature"], 0.2)
        self.assertEqual(llm_compat.usage_summary()[0]["calls"], 1)

    def test_no_temperature_on_5_series(self):
        client = FakeClient([self._parsed(_Verdict(severity="PASS"))])
        structured_call(model="claude-sonnet-5-5", system="s", user="u", schema=_Verdict,
                        max_tokens=100, phase="judge", temperature=0.2, client=client)
        self.assertNotIn("temperature", client.messages.calls[0])

    def test_raises_when_unparsed_or_truncated(self):
        with self.assertRaises(LLMResponseError):
            structured_call(model="m", system="s", user="u", schema=_Verdict, max_tokens=1,
                            phase="p", client=FakeClient([self._parsed(None)]))
        with self.assertRaises(LLMResponseError):
            structured_call(model="m", system="s", user="u", schema=_Verdict, max_tokens=1,
                            phase="p", client=FakeClient([self._parsed(_Verdict(severity="x"), stop="max_tokens")]))


if __name__ == "__main__":
    unittest.main()
