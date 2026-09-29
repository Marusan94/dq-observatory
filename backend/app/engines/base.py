from dataclasses import dataclass, field


@dataclass
class EngineResult:
    engine: str
    metrics: dict = field(default_factory=dict)
    issues: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
