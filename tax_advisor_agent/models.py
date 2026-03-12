"""
データモデル
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json
from pathlib import Path


@dataclass
class BusinessProfile:
    """事業者プロフィール"""
    business_name: str = ""
    business_type: str = ""  # 業種
    annual_revenue: Optional[int] = None  # 年間売上 (円)
    employees: int = 0  # 従業員数
    established_year: Optional[int] = None  # 設立年
    prefecture: str = ""  # 都道府県
    description: str = ""  # 事業内容の説明
    blue_return: bool = True  # 青色申告かどうか

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "BusinessProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> Optional["BusinessProfile"]:
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


@dataclass
class SubsidyInfo:
    """補助金・助成金情報"""
    name: str  # 補助金名
    organization: str  # 実施機関
    description: str  # 概要
    amount: str  # 金額・補助率
    target: str  # 対象者
    deadline: str  # 申請期限
    url: str  # 詳細URL
    business_types: list[str] = field(default_factory=list)  # 対象業種
    status: str = "募集中"  # 募集中 / 準備中 / 終了
    researched_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResearchReport:
    """リサーチレポート"""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    business_type: str = ""
    subsidies: list[SubsidyInfo] = field(default_factory=list)
    tax_tips: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def save(self, path: Path) -> None:
        reports = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                reports = json.load(f)
        reports.append(self.to_dict())
        # 最新50件のみ保持
        reports = reports[-50:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_latest(cls, path: Path, n: int = 5) -> list[dict]:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            reports = json.load(f)
        return reports[-n:]


@dataclass
class AgentResponse:
    """エージェントの応答"""
    agent_name: str
    content: str
    thinking: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
