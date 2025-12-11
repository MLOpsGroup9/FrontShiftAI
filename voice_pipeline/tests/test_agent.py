import asyncio
from collections import defaultdict
import json

import httpx
import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from livekit.agents import AgentSession, llm, beta, stt, tts
from livekit.plugins import openai
from scripts.main import (
    _env_flag, 
    _build_stt_provider, 
    _build_llm_provider, 
    _build_tts_provider, 
    _build_vad,
    _build_chain,
    _build_stt_chain,
    _build_llm_chain,
    _build_tts_chain,
    handle_asyncio_exception,
    entrypoint,
    )
from scripts.main import VoiceAgent, BackendClient
from voice_pipeline.utils.config import ProviderConfig, ProviderChainConfig

def _llm_model() -> llm.LLM:
    return openai.LLM(model="gpt-4o", parallel_tool_calls=False, temperature=0.45)


# Tier 1: Testing the helper functions 
def test_env_flag(monkeypatch):
    monkeypatch.setenv("VOICE_PIPELINE_LOG_TO_FILE", "1")
    assert _env_flag("VOICE_PIPELINE_LOG_TO_FILE") is True

    monkeypatch.setenv("VOICE_PIPELINE_LOG_TO_FILE", "off")
    assert _env_flag("VOICE_PIPELINE_LOG_TO_FILE") is False

    monkeypatch.delenv("VOICE_PIPELINE_LOG_TO_FILE", raising=False)
    assert _env_flag("VOICE_PIPELINE_LOG_TO_FILE", default="yes") is True


def test_build_stt_provider(monkeypatch) -> None:
    captured = {}

    class DummySTT:
        def __init__(self, model=None, **kwargs):
            captured["model"] = model
            captured["kwargs"] = kwargs

    monkeypatch.setattr("scripts.main.deepgram", SimpleNamespace(STT=DummySTT))

    cfg = ProviderConfig(
        provider="deepgram",
        model="nova-2-general",
        kwargs={"language": "en"},   
    )

    result = _build_stt_provider(cfg)

    assert isinstance(result, DummySTT)
    assert captured["model"] == "nova-2-general"
    assert captured["kwargs"] == {"language": "en"}


def test_build_llm_provider(monkeypatch) -> None:
    captured = {}

    class DummyLLM:
        def __init__(self, model=None, **kwargs):
            captured["model"] = model
            captured["kwargs"] = kwargs

    monkeypatch.setattr("scripts.main.openai", SimpleNamespace(LLM=DummyLLM))


    cfg = ProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        kwargs={"temperature": 0.1},
    )

    result = _build_llm_provider(cfg)

    assert isinstance(result, DummyLLM)
    assert captured["model"] == "gpt-4o-mini"
    assert captured["kwargs"] == {"temperature": 0.1}


def test_build_tts_provider(monkeypatch) -> None:
    captured = {}

    class DummyTTS:
        def __init__(self, model=None, **kwargs):
            captured["model"] = model
            captured["kwargs"] = kwargs


    monkeypatch.setattr("scripts.main.cartesia", SimpleNamespace(TTS=DummyTTS))


    cfg = ProviderConfig(
        provider="cartesia",
        model="sonic-2",
        kwargs={"voice": "stream"},
    )

    result = _build_tts_provider(cfg)

    assert isinstance(result, DummyTTS)
    assert captured["model"] == "sonic-2"
    assert captured["kwargs"] == {"voice": "stream"}


def test_build_vad(monkeypatch) -> None:
    captured = {}

    class DummyVAD:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        "scripts.main.silero",
        SimpleNamespace(VAD=SimpleNamespace(load=lambda **kwargs: DummyVAD(**kwargs))),
    )
    cfg = ProviderConfig(
        provider="silero",
        kwargs={"sensitivity": 0.5},
    )

    result = _build_vad(cfg)

    assert isinstance(result, DummyVAD)
    assert captured["kwargs"] == {"sensitivity": 0.5}



def test_build_chain_single_provider() -> None:
    cfg = ProviderChainConfig(primary=ProviderConfig(provider="primary"), fallbacks=[])

    def builder(provider_cfg):
        return provider_cfg.provider

    result = _build_chain(cfg, builder, object)
    assert result == "primary"


def test_build_chain_multiple_providers() -> None:
    captured = {}

    class DummyAdapter:
        def __init__(self, providers):
            captured["providers"] = providers

    cfg = ProviderChainConfig(
        primary=ProviderConfig(provider="primary"),
        fallbacks=[ProviderConfig(provider="fallback1"), ProviderConfig(provider="fallback2")],
    )

    def builder(provider_cfg):
        return provider_cfg.provider

    adapter = _build_chain(cfg, builder, DummyAdapter)
    assert isinstance(adapter, DummyAdapter)
    assert captured["providers"] == ["primary", "fallback1", "fallback2"]


def test_build_llm_chain(monkeypatch) -> None:
    sentinel = object()
    args = {}

    def fake_build_chain(cfg, builder, adapter):
        args["cfg"] = cfg
        args["builder"] = builder
        args["adapter"] = adapter
        return sentinel

    monkeypatch.setattr("scripts.main._build_chain", fake_build_chain)

    cfg = ProviderChainConfig(primary=ProviderConfig(provider="primary"), fallbacks=[])
    result = _build_llm_chain(cfg)

    assert result is sentinel
    assert args["cfg"] is cfg
    assert args["builder"] is _build_llm_provider
    assert args["adapter"] is llm.FallbackAdapter


def test_build_stt_chain(monkeypatch) -> None:
    sentinel = object()
    args = {}

    def fake_build_chain(cfg, builder, adapter):
        args["builder"] = builder
        args["adapter"] = adapter
        return sentinel

    monkeypatch.setattr("scripts.main._build_chain", fake_build_chain)

    cfg = ProviderChainConfig(primary=ProviderConfig(provider="primary"), fallbacks=[])
    result = _build_stt_chain(cfg)

    assert result is sentinel
    assert args["builder"] is _build_stt_provider
    assert args["adapter"] is stt.FallbackAdapter


def test_build_tts_chain(monkeypatch) -> None:
    sentinel = object()
    args = {}

    def fake_build_chain(cfg, builder, adapter):
        args["builder"] = builder
        args["adapter"] = adapter
        return sentinel

    monkeypatch.setattr("scripts.main._build_chain", fake_build_chain)

    cfg = ProviderChainConfig(primary=ProviderConfig(provider="primary"), fallbacks=[])
    result = _build_tts_chain(cfg)

    assert result is sentinel
    assert args["builder"] is _build_tts_provider
    assert args["adapter"] is tts.FallbackAdapter


def test_handle_asyncio_exception(monkeypatch) -> None:
    calls = {}

    class DummyLogger:
        def exception(self, message, context):
            calls["message"] = message
            calls["context"] = context

    monkeypatch.setattr("scripts.main.logger", DummyLogger())

    context = {"error": "boom"}
    handle_asyncio_exception(loop=Mock(), context=context)

    assert "Unhandled asyncio error" in calls["message"]
    assert calls["context"] is context


@pytest.fixture
def voice_agent_builder(monkeypatch):
    backend_calls = []
    backend_responses = defaultdict(list)
    backend_instances = []

    class DummyBackend:
        def __init__(self, base_url: str, token: str) -> None:
            self.base_url = base_url
            self.token = token
            backend_instances.append(self)

        async def post(self, path: str, payload: dict) -> dict:
            backend_calls.append({"path": path, "payload": payload})
            queue = backend_responses[path]
            if not queue:
                raise AssertionError(f"No mock response configured for path {path}")
            response = queue.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr("scripts.main.BackendClient", DummyBackend)
    monkeypatch.setattr(
        "scripts.main.CONFIG",
        SimpleNamespace(
            backend=SimpleNamespace(url="http://backend.test", token="testing-token"),
        ),
    )

    def fake_function_tool(fn):
        fn._is_function_tool = True
        return fn

    monkeypatch.setattr("scripts.main.function_tool", fake_function_tool)

    class DummyEmitter:
        def __init__(self) -> None:
            self.handlers = defaultdict(list)

        def on(self, event_name: str, handler):
            self.handlers[event_name].append(handler)
            return handler

        def emit(self, event_name: str, payload) -> None:
            for handler in self.handlers.get(event_name, []):
                handler(payload)

    class DummyLLM(DummyEmitter):
        def __init__(self) -> None:
            super().__init__()
            self.registered_tools = []

        def register_tools(self, tools):
            self.registered_tools.extend(tools)

    def fake_agent_init(self, instructions=None):
        self.instructions = instructions
        self.stt = DummyEmitter()
        self.llm = DummyLLM()
        self.tts = DummyEmitter()
        self.vad = DummyEmitter()

    monkeypatch.setattr("scripts.main.Agent.__init__", fake_agent_init, raising=False)

    stt_reporters = []

    class DummySTTMetricsReporter:
        def __init__(self):
            self.stt_metrics = []
            self.eou_metrics = []
            stt_reporters.append(self)

        async def on_stt_metrics_collected(self, metrics):
            self.stt_metrics.append(metrics)

        async def on_eou_metrics_collected(self, metrics):
            self.eou_metrics.append(metrics)

    llm_reporters = []

    class DummyLLMMetricsReporter:
        def __init__(self):
            self.metrics = []
            llm_reporters.append(self)

        async def on_metrics_collected(self, metrics):
            self.metrics.append(metrics)

    tts_reporters = []

    class DummyTTSMetricsReporter:
        def __init__(self):
            self.metrics = []
            tts_reporters.append(self)

        async def on_metrics_collected(self, metrics):
            self.metrics.append(metrics)

    vad_reporters = []

    class DummyVADMetricsReporter:
        def __init__(self):
            self.events = []
            vad_reporters.append(self)

        async def on_vad_event(self, event):
            self.events.append(event)

    monkeypatch.setattr("scripts.main.STTMetricsReporter", DummySTTMetricsReporter)
    monkeypatch.setattr("scripts.main.LLMMetricsReporter", DummyLLMMetricsReporter)
    monkeypatch.setattr("scripts.main.TTSMetricsReporter", DummyTTSMetricsReporter)
    monkeypatch.setattr("scripts.main.VADMetricsReporter", DummyVADMetricsReporter)

    def build_agent(session_id: str = "test-session") -> VoiceAgent:
        agent = VoiceAgent(session_id=session_id)
        agent.attach_metric_sources(agent.stt, agent.llm, agent.tts, agent.vad)
        return agent

    return SimpleNamespace(
        build_agent=build_agent,
        backend_calls=backend_calls,
        backend_responses=backend_responses,
        backend_instances=backend_instances,
        stt_reporters=stt_reporters,
        llm_reporters=llm_reporters,
        tts_reporters=tts_reporters,
        vad_reporters=vad_reporters,
    )


@pytest.fixture
def entrypoint_setup(monkeypatch):
    fake_stt_cls = type("FakeSTT", (), {})
    fake_tts_cls = type("FakeTTS", (), {})
    fake_llm_cls = type("FakeLLM", (), {})

    monkeypatch.setattr("scripts.main.stt", SimpleNamespace(STT=fake_stt_cls))
    monkeypatch.setattr("scripts.main.tts", SimpleNamespace(TTS=fake_tts_cls))
    monkeypatch.setattr("scripts.main.llm", SimpleNamespace(LLM=fake_llm_cls))

    config = SimpleNamespace(
        backend=SimpleNamespace(url="http://backend.test", token="testing-token"),
        livekit=SimpleNamespace(
            stt="stt-config",
            llm="llm-config",
            tts="tts-config",
            vad="vad-config",
        ),
    )
    monkeypatch.setattr("scripts.main.CONFIG", config)

    build_calls = {"stt": [], "llm": [], "tts": [], "vad": []}

    def builder_factory(name):
        def _builder(cfg):
            build_calls[name].append(cfg)
            return f"{name}-chain"

        return _builder

    monkeypatch.setattr("scripts.main._build_stt_chain", builder_factory("stt"))
    monkeypatch.setattr("scripts.main._build_llm_chain", builder_factory("llm"))
    monkeypatch.setattr("scripts.main._build_tts_chain", builder_factory("tts"))
    monkeypatch.setattr("scripts.main._build_vad", builder_factory("vad"))

    session_config = {}
    created_sessions = []

    class DummySession:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.events = defaultdict(list)
            self.say_calls = []
            self.update_agent_calls = []
            self.current_agent = SimpleNamespace()
            self.start_error = session_config.get("start_error")
            self.reply_error = session_config.get("reply_error")
            created_sessions.append(self)

        def on(self, event_name: str):
            def decorator(fn):
                self.events[event_name].append(fn)
                return fn

            return decorator

        async def start(self, agent, room):
            self.started = (agent, room)
            if self.start_error:
                raise self.start_error

        async def generate_reply(self, **kwargs):
            self.generated = kwargs
            if self.reply_error:
                raise self.reply_error

        def say(self, message: str, **kwargs):
            self.say_calls.append({"message": message, **kwargs})

        def update_agent(self, agent):
            self.update_agent_calls.append(agent)

    monkeypatch.setattr("scripts.main.AgentSession", DummySession)

    created_agents = []

    class DummyVoiceAgent:
        def __init__(self, session_id=None):
            self.session_id = session_id
            created_agents.append(self)
            self.metric_sources = None

        def attach_metric_sources(self, stt_chain, llm_chain, tts_chain, vad_chain):
            self.metric_sources = {
                "stt": stt_chain,
                "llm": llm_chain,
                "tts": tts_chain,
                "vad": vad_chain,
            }

    monkeypatch.setattr("scripts.main.VoiceAgent", DummyVoiceAgent)
    monkeypatch.setattr("scripts.main.Path.exists", lambda self: False)

    return SimpleNamespace(
        build_calls=build_calls,
        created_sessions=created_sessions,
        created_agents=created_agents,
        session_config=session_config,
        fake_classes=SimpleNamespace(stt=fake_stt_cls, tts=fake_tts_cls, llm=fake_llm_cls),
    )



# Tier 2: BackendClient Test (no LLM, just HTTP)
@pytest.mark.asyncio
async def test_backend_client_hits_mock_server(monkeypatch) -> None:
    requests_made = []
    real_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode() or "{}")
        requests_made.append(
            {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "json": payload,
            }
        )
        return httpx.Response(200, json={"path": request.url.path, "echo": payload})

    transport = httpx.MockTransport(handler)

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            self._client = real_async_client(*args, **kwargs)

        async def __aenter__(self):
            return await self._client.__aenter__()

        async def __aexit__(self, exc_type, exc, tb):
            return await self._client.__aexit__(exc_type, exc, tb)

    monkeypatch.setattr("scripts.main.httpx.AsyncClient", DummyAsyncClient)

    client = BackendClient(base_url="https://mock.api/", token="s3cr3t")
    payload = {"message": "hello"}
    result = await client.post("/rag", payload)

    assert result == {"path": "/rag", "echo": payload}
    assert requests_made[0]["method"] == "POST"
    assert requests_made[0]["url"] == "https://mock.api/rag"
    assert requests_made[0]["headers"].get("authorization") == "Bearer s3cr3t"
    assert requests_made[0]["json"] == payload


# Tier 3: VoiceAgent Agent tools without real LLMs
def _tools_by_name(agent: VoiceAgent):
    return {tool.__name__: tool for tool in agent.llm.registered_tools}


def test_voice_agent_registers_expected_tools(voice_agent_builder) -> None:
    ctx = voice_agent_builder
    agent = ctx.build_agent()

    tool_names = {tool.__name__ for tool in agent.llm.registered_tools}
    assert tool_names == {"query_info", "website_search", "request_pto", "create_hr_ticket"}


@pytest.mark.asyncio
async def test_voice_agent_tools_call_backend(voice_agent_builder) -> None:
    ctx = voice_agent_builder
    ctx.backend_responses["/api/rag/query"].append(
        {"answer": "Policy text", "sources": ["kb://pto"], "company": "Frontshift"}
    )
    ctx.backend_responses["/api/chat/message"].append(
        {
            "agent_used": "website_extraction",
            "response": "The HR page lists it under Benefits.",
            "metadata": {"source": "website"},
        }
    )
    ctx.backend_responses["/api/pto/chat"].append({"status": "submitted"})
    ctx.backend_responses["/api/hr-tickets/chat"].append({"ticket_id": "HR-42"})

    agent = ctx.build_agent()
    tools = _tools_by_name(agent)

    query_result = await tools["query_info"]("pto policy", top_k=2)
    assert query_result == {
        "answer": "Policy text",
        "sources": ["kb://pto"],
        "company": "Frontshift",
    }

    website_result = await tools["website_search"]("what about benefits?")
    assert website_result == {
        "answer": "The HR page lists it under Benefits.",
        "source": "website",
    }

    pto_result = await tools["request_pto"]("I need tomorrow off")
    assert pto_result == {"status": "submitted"}

    hr_result = await tools["create_hr_ticket"]("My paycheck is wrong")
    assert hr_result == {"ticket_id": "HR-42"}

    assert [call["path"] for call in ctx.backend_calls] == [
        "/api/rag/query",
        "/api/chat/message",
        "/api/pto/chat",
        "/api/hr-tickets/chat",
    ]
    assert ctx.backend_calls[0]["payload"] == {"query": "pto policy", "top_k": 2}
    assert ctx.backend_calls[1]["payload"] == {"message": "what about benefits?"}


@pytest.mark.asyncio
async def test_voice_agent_website_search_requires_specific_agent(voice_agent_builder) -> None:
    ctx = voice_agent_builder
    ctx.backend_responses["/api/chat/message"].append(
        {
            "agent_used": "fallback_agent",
            "response": "Sorry, nothing found",
            "metadata": {},
        }
    )

    agent = ctx.build_agent()
    tools = _tools_by_name(agent)

    with pytest.raises(ValueError):
        await tools["website_search"]("search the site")

    assert ctx.backend_calls[0]["path"] == "/api/chat/message"
    assert ctx.backend_calls[0]["payload"] == {"message": "search the site"}


# Tier 4: Metrics Hooks 
@pytest.mark.asyncio
async def test_voice_agent_stt_metrics_handlers_schedule_reporters(voice_agent_builder) -> None:
    ctx = voice_agent_builder
    agent = ctx.build_agent()

    handlers = agent.stt.handlers["metrics_collected"]
    assert len(handlers) == 2

    stt_metrics = SimpleNamespace(
        type="stt",
        label="greeting",
        request_id="req-1",
        timestamp=0.0,
        duration=0.25,
        speech_id="speech-1",
        error=None,
        streamed=True,
        audio_duration=0.25,
    )
    eou_metrics = SimpleNamespace(
        type="eou",
        label="greeting",
        timestamp=0.5,
        end_of_utterance_delay=0.4,
        transcription_delay=0.2,
        speech_id="speech-1",
        error=None,
    )

    handlers[0](stt_metrics)
    handlers[1](eou_metrics)

    await asyncio.sleep(0)

    reporter = ctx.stt_reporters[0]
    assert reporter.stt_metrics == [stt_metrics]
    assert reporter.eou_metrics == [eou_metrics]


@pytest.mark.asyncio
async def test_voice_agent_other_metrics_handlers_schedule_reporters(voice_agent_builder) -> None:
    ctx = voice_agent_builder
    agent = ctx.build_agent()

    llm_metrics = SimpleNamespace(
        type="llm",
        label="llm-run",
        request_id="llm-1",
        timestamp=1.0,
        duration=0.6,
        ttft=0.1,
        cancelled=False,
        completion_tokens=128,
        prompt_tokens=32,
        total_tokens=160,
        tokens_per_second=200.0,
    )
    tts_metrics = SimpleNamespace(
        type="tts",
        label="reply",
        request_id="tts-1",
        timestamp=1.2,
        ttfb=0.05,
        duration=0.4,
        audio_duration=0.4,
        cancelled=False,
        characters_count=120,
        streamed=True,
        speech_id="speech-2",
        error=None,
    )
    vad_event = SimpleNamespace(
        type="vad",
        timestamp=1.3,
        idle_time=0.8,
        inference_duration_total=0.2,
        inference_count=4,
        speech_id="speech-3",
        error=None,
    )

    agent.llm.handlers["metrics_collected"][0](llm_metrics)
    agent.tts.handlers["metrics_collected"][0](tts_metrics)
    agent.vad.handlers["metrics_collected"][0](vad_event)

    await asyncio.sleep(0)

    assert ctx.llm_reporters[0].metrics == [llm_metrics]
    assert ctx.tts_reporters[0].metrics == [tts_metrics]
    assert ctx.vad_reporters[0].events == [vad_event]


# Tier 5: Finally complete Voice Agent test behaviours


@pytest.mark.asyncio
async def test_entrypoint_starts_agent_session(entrypoint_setup) -> None:
    ctx = entrypoint_setup
    job_ctx = SimpleNamespace(room="room-alpha")

    await entrypoint(job_ctx)

    assert len(ctx.created_sessions) == 1
    session = ctx.created_sessions[0]
    agent = ctx.created_agents[0]

    assert session.started == (agent, "room-alpha")
    assert "Greet the user" in session.generated["instructions"]
    assert ctx.build_calls["stt"] == ["stt-config"]
    assert ctx.build_calls["llm"] == ["llm-config"]
    assert ctx.build_calls["tts"] == ["tts-config"]
    assert ctx.build_calls["vad"] == ["vad-config"]


@pytest.mark.asyncio
async def test_entrypoint_handles_session_start_failure(entrypoint_setup) -> None:
    ctx = entrypoint_setup
    ctx.session_config["start_error"] = RuntimeError("boom")
    job_ctx = SimpleNamespace(room="room-beta")

    await entrypoint(job_ctx)

    session = ctx.created_sessions[0]
    assert hasattr(session, "started")
    assert not hasattr(session, "generated")


@pytest.mark.asyncio
async def test_entrypoint_error_handler_restarts_stt(entrypoint_setup, monkeypatch) -> None:
    ctx = entrypoint_setup
    job_ctx = SimpleNamespace(room="room-gamma")

    real_sleep = asyncio.sleep
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)
        await real_sleep(0)

    monkeypatch.setattr("scripts.main.asyncio.sleep", fake_sleep)

    await entrypoint(job_ctx)

    session = ctx.created_sessions[0]
    err = SimpleNamespace(recoverable=False)
    stt_source = ctx.fake_classes.stt()

    error_handler = session.events["error"][0]
    error_handler(SimpleNamespace(error=err, source=stt_source))

    await asyncio.sleep(0)

    assert session.update_agent_calls == [session.current_agent]
    assert err.recoverable is True
    assert sleep_calls == [0.3]
