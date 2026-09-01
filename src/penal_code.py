"""The Directorate Penal Code — law and sentencing.

Doctrine: "Innocence Proves Nothing." A hearing under this code determines
whether the Directorate acts, not whether the accused is innocent in the
way a real-world court would weigh it.

See docs/systems/penal-code.md for the full design this implements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SentencingTier(Enum):
    """The four sentencing tiers, least to most severe."""

    REPRIMAND_AND_RESTITUTION = "reprimand_and_restitution"
    TOIL_LEGION = "toil_legion"
    PENAL_LEGION = "penal_legion"
    SERVITOR_CONVERSION = "servitor_conversion"  # capital, irreversible


CAPITAL_TIER = SentencingTier.SERVITOR_CONVERSION


@dataclass
class Article:
    """One numbered article of the Penal Code."""

    id: str
    name: str
    description: str
    typical_sentence: SentencingTier


@dataclass
class PenalCode:
    """The Directorate's standing body of law."""

    doctrine: str
    articles: dict[str, Article] = field(default_factory=dict)

    @classmethod
    def default_code(cls) -> "PenalCode":
        """Build the five founding articles established for the Directorate."""
        articles = {
            "desertion_of_post": Article(
                id="desertion_of_post",
                name="Desertion of Post",
                description="Abandoning an assigned duty station without authorization.",
                typical_sentence=SentencingTier.TOIL_LEGION,
            ),
            "sabotage_of_directorate_property": Article(
                id="sabotage_of_directorate_property",
                name="Sabotage of Directorate Property",
                description="Deliberate damage to Directorate infrastructure, ships, or cargo.",
                typical_sentence=SentencingTier.PENAL_LEGION,
            ),
            "insubordination_under_command": Article(
                id="insubordination_under_command",
                name="Insubordination Under Command",
                description="Refusal to execute a lawful order from a superior officer.",
                typical_sentence=SentencingTier.REPRIMAND_AND_RESTITUTION,
            ),
            "hoarding_of_strategic_supply": Article(
                id="hoarding_of_strategic_supply",
                name="Hoarding of Strategic Supply",
                description="Withholding rationed or strategic material from the Quartermaster Corps.",
                typical_sentence=SentencingTier.TOIL_LEGION,
            ),
            "treason_against_the_directorate": Article(
                id="treason_against_the_directorate",
                name="Treason Against the Directorate",
                description="Acting to materially aid a hostile power or undermine Directorate command.",
                typical_sentence=SentencingTier.SERVITOR_CONVERSION,
            ),
        }
        return cls(doctrine="Innocence Proves Nothing", articles=articles)


def charge(code: PenalCode, article_id: str) -> SentencingTier:
    """Return the typical sentence for a charged article.

    This is a starting recommendation, not an automatic outcome — a real
    hearing may deviate from it. Raises KeyError if the article is unknown.
    """
    return code.articles[article_id].typical_sentence


def confirm_capital_sentence(
    referred_by_vigil: bool, confirmed_by_grand_director: bool
) -> bool:
    """Gate a Servitor Conversion sentence behind its required sign-off chain.

    Both the Vigil's referral and the Grand Director's confirmation must be
    True. Anything less raises ValueError instead of silently allowing an
    irreversible capital sentence to proceed.
    """
    if not referred_by_vigil:
        raise ValueError(
            "Servitor Conversion requires a Vigil referral before it can be confirmed."
        )
    if not confirmed_by_grand_director:
        raise ValueError(
            "Servitor Conversion requires Grand Director confirmation before it can be carried out."
        )
    return True
