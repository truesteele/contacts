"""
Conference config loader — loads and validates a conference YAML config file,
provides typed access to all sections, and supports template variable
substitution in the scoring prompt.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ConferenceSection:
    name: str
    slug: str
    dates: str
    venue: str
    attendee_count: int
    connect_url_template: str
    field_prefix: str = ""
    roles: list[dict] = field(default_factory=list)


@dataclass
class OrganizationSection:
    name: str
    tagline: str
    mission: str
    model: str
    theory_of_change: str
    location: str
    color_primary: str
    color_accent: str
    color_dark: str
    partnership_types: dict[str, dict] = field(default_factory=dict)
    campaign: dict[str, str] = field(default_factory=dict)
    stats: dict[str, str] = field(default_factory=dict)
    key_concepts: list[str] = field(default_factory=list)


@dataclass
class UserSection:
    name: str
    full_name: str
    role: str
    linkedin: str
    bio: list[str] = field(default_factory=list)
    conference_role: str = ""
    connection_signals: list[str] = field(default_factory=list)
    columns: dict[str, str] = field(default_factory=dict)
    connection_field: str = ""


@dataclass
class UsersSection:
    primary: UserSection
    support: UserSection


@dataclass
class SupabaseSection:
    project_url: str
    anon_key: str
    table_name: str
    edge_function: str
    project_ref: str


@dataclass
class VercelSection:
    deploy_dir: str
    alias: str
    scope: str


@dataclass
class DataPathsSection:
    warm_leads: str
    triage_results: str
    shortlist: str
    linkedin_profiles: str = ""
    linkedin_posts: str = ""
    deep_writeups_module: str = ""


@dataclass
class TierConfig:
    label: str
    badge_class: str
    company_class: str = ""


class ConferenceConfig:
    """Loads and validates a conference YAML config file."""

    def __init__(self, config_path: str):
        self._config_path = Path(config_path).resolve()
        self._config_dir = self._config_path.parent

        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")

        with open(self._config_path) as f:
            self._raw = yaml.safe_load(f)

        self._validate()
        self._parse()

    def _validate(self):
        """Validate that all required top-level sections exist."""
        required = ["conference", "organization", "users", "supabase", "vercel", "data_paths", "scoring_prompt"]
        missing = [k for k in required if k not in self._raw]
        if missing:
            raise ValueError(f"Config missing required sections: {', '.join(missing)}")

        # Validate users has primary
        if "primary" not in self._raw["users"]:
            raise ValueError("Config missing users.primary section")

    def _parse(self):
        """Parse raw YAML into typed dataclass sections."""
        c = self._raw["conference"]
        self.conference = ConferenceSection(
            name=c["name"],
            slug=c["slug"],
            dates=c["dates"],
            venue=c["venue"],
            attendee_count=c["attendee_count"],
            connect_url_template=c.get("connect_url_template", ""),
            field_prefix=c.get("field_prefix", ""),
            roles=c.get("roles", []),
        )

        o = self._raw["organization"]
        self.organization = OrganizationSection(
            name=o["name"],
            tagline=o["tagline"],
            mission=o["mission"],
            model=o["model"],
            theory_of_change=o["theory_of_change"],
            location=o["location"],
            color_primary=o["color_primary"],
            color_accent=o["color_accent"],
            color_dark=o.get("color_dark", o["color_accent"]),
            partnership_types=o.get("partnership_types", {}),
            campaign=o.get("campaign", {}),
            stats=o.get("stats", {}),
            key_concepts=o.get("key_concepts", []),
        )

        up = self._raw["users"]["primary"]
        primary = UserSection(
            name=up["name"],
            full_name=up["full_name"],
            role=up["role"],
            linkedin=up["linkedin"],
            bio=up.get("bio", []),
            conference_role=up.get("conference_role", ""),
            connection_signals=up.get("connection_signals", []),
            columns=up.get("columns", {}),
        )

        us = self._raw["users"].get("support", {})
        support = UserSection(
            name=us.get("name", ""),
            full_name=us.get("full_name", ""),
            role=us.get("role", ""),
            linkedin=us.get("linkedin", ""),
            bio=us.get("bio", []),
            columns=us.get("columns", {}),
            connection_field=us.get("connection_field", ""),
        )

        self.users = UsersSection(primary=primary, support=support)

        sb = self._raw["supabase"]
        self.supabase = SupabaseSection(
            project_url=sb["project_url"],
            anon_key=sb["anon_key"],
            table_name=sb["table_name"],
            edge_function=sb["edge_function"],
            project_ref=sb["project_ref"],
        )

        v = self._raw["vercel"]
        self.vercel = VercelSection(
            deploy_dir=v["deploy_dir"],
            alias=v["alias"],
            scope=v["scope"],
        )

        dp = self._raw["data_paths"]
        self.data_paths = DataPathsSection(
            warm_leads=dp["warm_leads"],
            triage_results=dp["triage_results"],
            shortlist=dp["shortlist"],
            linkedin_profiles=dp.get("linkedin_profiles", ""),
            linkedin_posts=dp.get("linkedin_posts", ""),
            deep_writeups_module=dp.get("deep_writeups_module", ""),
        )

        # Tiers
        self.tiers: dict[int, TierConfig] = {}
        for tier_num, tier_data in self._raw.get("tiers", {}).items():
            self.tiers[int(tier_num)] = TierConfig(
                label=tier_data["label"],
                badge_class=tier_data["badge_class"],
                company_class=tier_data.get("company_class", ""),
            )

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a path relative to the config file's directory."""
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return (self._config_dir / p).resolve()

    def load_scoring_prompt(self) -> str:
        """Load the scoring prompt file and substitute template variables."""
        prompt_path = self.resolve_path(self._raw["scoring_prompt"])
        if not prompt_path.exists():
            raise FileNotFoundError(f"Scoring prompt not found: {prompt_path}")

        with open(prompt_path) as f:
            prompt = f.read()

        # Build replacement map
        replacements = {
            # Conference
            "{{conference.name}}": self.conference.name,
            "{{conference.dates}}": self.conference.dates,
            "{{conference.venue}}": self.conference.venue,
            # Organization
            "{{org.name}}": self.organization.name,
            "{{org.tagline}}": self.organization.tagline,
            "{{org.mission}}": self.organization.mission,
            "{{org.model}}": self.organization.model,
            "{{org.theory_of_change}}": self.organization.theory_of_change,
            "{{org.location}}": self.organization.location,
            # Users
            "{{users.primary.name}}": self.users.primary.name,
            "{{users.primary.full_name}}": self.users.primary.full_name,
            "{{users.primary.role}}": self.users.primary.role,
            "{{users.primary.conference_role}}": self.users.primary.conference_role,
            "{{users.support.name}}": self.users.support.name,
            "{{users.support.full_name}}": self.users.support.full_name,
            "{{users.support.role}}": self.users.support.role,
            # Campaign
            "{{org.campaign.name}}": self.organization.campaign.get("name", ""),
            "{{org.campaign.goal}}": self.organization.campaign.get("goal", ""),
            "{{org.campaign.raised}}": self.organization.campaign.get("raised", ""),
            # Stats
            "{{org.stats.bipoc_pct}}": self.organization.stats.get("bipoc_pct", ""),
            "{{org.stats.families_served}}": self.organization.stats.get("families_served", ""),
            "{{org.stats.camping_trips}}": self.organization.stats.get("camping_trips", ""),
        }

        # Composite replacements (lists rendered as bullet points)
        replacements["{{users.primary.bio}}"] = "\n".join(f"- {line}" for line in self.users.primary.bio)
        replacements["{{users.primary.connection_signals}}"] = "\n".join(
            f"- {sig}" for sig in self.users.primary.connection_signals
        )
        replacements["{{org.key_concepts}}"] = ", ".join(self.organization.key_concepts)
        replacements["{{org.partnership_types}}"] = self._render_partnership_types()

        for key, value in replacements.items():
            prompt = prompt.replace(key, value)

        return prompt

    def _render_partnership_types(self) -> str:
        """Render partnership types as numbered list for the scoring prompt."""
        lines = []
        for i, (key, pt) in enumerate(self.organization.partnership_types.items(), 1):
            if key in ("multiple", "unlikely"):
                continue
            label = pt["label"].upper()
            desc = pt.get("description", "")
            lines.append(f"{i}. {label}: {desc}")
        return "\n".join(lines)

    @property
    def raw(self) -> dict[str, Any]:
        """Access the raw parsed YAML dict for any fields not in typed sections."""
        return self._raw
