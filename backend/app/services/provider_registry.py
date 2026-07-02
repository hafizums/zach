from typing import Dict, Any, Optional, List
from app.providers.mock_provider import (
    MockLLMProvider,
    MockImageProvider,
    MockVideoProvider,
    MockAudioProvider,
    MockTranscriptionProvider,
)
from app.providers.openai_provider import OpenAILLMProvider, OpenAITTSProvider
from app.providers.wavespeed_provider import WavespeedImageProvider, WavespeedVideoProvider

# A registry connecting provider_names and modalities to actual class instances or constructors
# In a real app, this might dynamically load plugins or use a dependency injection framework.

class ProviderRegistry:
    def __init__(self):
        self._providers: Dict[str, Dict[str, Any]] = {}
        
    def register(self, provider_name: str, modality: str, provider_instance: Any):
        if provider_name not in self._providers:
            self._providers[provider_name] = {}
        self._providers[provider_name][modality] = provider_instance
        
    def get_provider(self, provider_name: str, modality: str) -> Optional[Any]:
        return self._providers.get(provider_name, {}).get(modality)
        
    def list_registered_providers(self) -> List[dict]:
        results = []
        for p_name, modalities in self._providers.items():
            for m_name, _ in modalities.items():
                results.append({"provider_name": p_name, "modality": m_name})
        return results

    def validate_provider_available(self, provider_name: str, modality: str) -> bool:
        return self.get_provider(provider_name, modality) is not None

registry = ProviderRegistry()

# Register defaults
registry.register("mock", "llm", MockLLMProvider())
registry.register("mock", "image", MockImageProvider())
registry.register("mock", "video", MockVideoProvider())
registry.register("mock", "audio", MockAudioProvider())
registry.register("mock", "transcription", MockTranscriptionProvider())

registry.register("openai", "llm", OpenAILLMProvider())
registry.register("openai", "audio", OpenAITTSProvider())
registry.register("wavespeed", "image", WavespeedImageProvider())
registry.register("wavespeed", "video", WavespeedVideoProvider())

# Note: The render provider doesn't have a dedicated mock class yet, 
# it's just deterministic logic in render_generation_service, but we can register a dummy for registry completeness
# or we can just leave it out and have the preflight allow the render modality natively.
class MockRenderProvider:
    pass

registry.register("mock", "render", MockRenderProvider())

def get_provider(provider_name: str, modality: str) -> Optional[Any]:
    return registry.get_provider(provider_name, modality)

def list_registered_providers() -> List[dict]:
    return registry.list_registered_providers()

def validate_provider_available(provider_name: str, modality: str) -> bool:
    return registry.validate_provider_available(provider_name, modality)
