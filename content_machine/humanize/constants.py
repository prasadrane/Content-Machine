"""Constants, blacklists, and system prompts for the Humanize Transformer."""

from __future__ import annotations

import re
from content_machine.schemas import HumanizeChannel, HumanizeTone

BANNED_AI_WORDS: set[str] = {
    "delve", "delves", "delving",
    "tapestry", "tapestries",
    "pivotal",
    "testament",
    "cornerstone",
    "robust",
    "vibrant",
    "realm", "realms",
    "foster", "fosters", "fostering",
    "harness", "harnessing",
    "interplay",
    "multifaceted",
    "paramount",
    "game-changer", "gamechanger",
    "revolutionize", "revolutionizing",
    "seamlessly", "seamless",
    "plethora",
    "beacon",
    "underscores", "underscoring",
    "synergy", "synergies",
    "utilize", "utilizes", "utilizing",
    "facilitate", "facilitates", "facilitating",
    "holistic",
    "endeavor", "endeavors",
}

BANNED_AI_PHRASES: list[str] = [
    "stands as a testament",
    "serves as a testament",
    "serves as a reminder",
    "pivotal moment",
    "crucial role",
    "key role",
    "evolving landscape",
    "rapidly evolving",
    "indelible mark",
    "transformative journey",
    "focal point",
    "deeply rooted",
    "setting the stage",
    "in today's fast-paced",
    "in today's world",
    "it is important to note",
    "it's important to remember",
    "not only that, but",
    "a testament to the power",
    "unlock value",
]

EM_DASH_PATTERN = re.compile(r"\s*—\s*|(?<!-)(?:\s+--\s+|(?<=\w)--(?:(?=\w)|\s+))(?!-)")

TONE_SYSTEM_PROMPTS: dict[HumanizeTone, str] = {
    HumanizeTone.PUNCHY_DIRECT: (
        "You are an elite technical editor turning draft content into human-level craft. "
        "Tone: PUNCHY & DIRECT. Short, crisp sentences, high burstiness, zero fluff, immediate mechanical point. "
        "Use contractions (it's, don't, we've). Ban all corporate cheerleading and clichés."
    ),
    HumanizeTone.PRAGMATIC_ARCHITECT: (
        "You are a senior principal systems engineer rewriting draft content in your authentic voice. "
        "Tone: PRAGMATIC ARCHITECT. Focus on production realities, trade-offs, architecture trade-offs, "
        "and concrete mechanics. Asymmetric rhythm: mix sharp observations with detailed explanations."
    ),
    HumanizeTone.CONVERSATIONAL_PEER: (
        "You are a friendly senior engineer chatting with a colleague over coffee. "
        "Tone: CONVERSATIONAL PEER. Warm, reflective, accessible, candid, and grounded. "
        "Use conversational qualifiers ('in practice,', 'the catch is,', 'honestly,')."
    ),
}

CHANNEL_PROMPTS: dict[HumanizeChannel, str] = {
    HumanizeChannel.LINKEDIN_COMMENT: (
        "Transform this into a 2-3 sentence LinkedIn comment. "
        "Jump straight into the technical argument or counter-point. Never say 'Great post!' or 'Spot on!'. "
        "Never exceed 3 sentences. High burstiness."
    ),
    HumanizeChannel.LINKEDIN_POST: (
        "Transform this into an authentic LinkedIn post. "
        "Hook fast with a 1-line observation. Use asymmetric paragraph blocks (1 line, then 3 lines, then 1 line). "
        "Close on a blunt operational takeaway. Zero decorative bullet emojis."
    ),
    HumanizeChannel.X_THREAD: (
        "Transform this into a natural X/Twitter thread. "
        "Hook fast without thread clichés like '1/ A masterclass in...'. Keep tweets tight and punchy."
    ),
    HumanizeChannel.VIDEO_SCRIPT: (
        "Transform this into a spoken, breathable short-form video script. "
        "Preserve visual cues in square brackets (e.g., [Visual Cue], [Camera Zoom]). Natural spoken rhythm."
    ),
    HumanizeChannel.GENERAL: (
        "Rewrite this technical text to sound completely human. "
        "Vary sentence lengths dramatically. Purge all AI tells."
    ),
}
