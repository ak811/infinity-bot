# cogs/close_circle/update.py
from datetime import datetime
from collections import defaultdict
import discord

from .state import interaction_scores, previous_message_user, reaction_history, vc_join_times

def _ensure_scores_row(uid: int) -> defaultdict:
    row = interaction_scores.get(uid)
    if isinstance(row, defaultdict):
        return row
    row = defaultdict(int, row or {})
    interaction_scores[uid] = row
    return row

def _bump_score(a: int, b: int, delta: int) -> None:
    _ensure_scores_row(a)[b] += delta

def _ensure_reaction_row(uid: int) -> defaultdict:
    row = reaction_history.get(uid)
    if isinstance(row, defaultdict):
        return row
    row = defaultdict(set, row or {})
    reaction_history[uid] = row
    return row

def update_proximity(member: discord.Member, channel_id: int) -> None:
    if member.bot:
        return
    prev = previous_message_user.get(channel_id)
    if prev and not prev.bot and prev.id != member.id:
        _bump_score(member.id, prev.id, 2)
        _bump_score(prev.id, member.id, 2)
    previous_message_user[channel_id] = member

def update_reply(message: discord.Message) -> None:
    if message.author.bot:
        return
    if message.reference and message.reference.resolved:
        replied = message.reference.resolved.author
        if not replied.bot and replied.id != message.author.id:
            _bump_score(message.author.id, replied.id, 5)

def update_mentions(message: discord.Message) -> None:
    if message.author.bot:
        return
    author = message.author.id
    for user in message.mentions:
        if not user.bot and user.id != author:
            _bump_score(author, user.id, 3)

def update_reactions_proximity(reaction: discord.Reaction, user: discord.Member) -> None:
    if user.bot or reaction.message.author.bot:
        return
    msg_author = reaction.message.author
    if msg_author.id == user.id:
        return
    _bump_score(user.id, msg_author.id, 2)
    _bump_score(msg_author.id, user.id, 1)
    emoji_str = str(reaction.emoji)
    _ensure_reaction_row(user.id)[msg_author.id].add(emoji_str)
    author_row = _ensure_reaction_row(msg_author.id)
    if user.id in author_row:
        _bump_score(user.id, msg_author.id, 4)
        _bump_score(msg_author.id, user.id, 4)

def update_voice_proximity(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if member.bot:
        return
    uid = member.id
    before_ch = before.channel
    after_ch = after.channel

    # leaving/switching away — score time spent
    if before_ch and before_ch != after_ch:
        join_time = vc_join_times.pop(uid, None)
        if join_time:
            mins = (datetime.utcnow() - join_time).total_seconds() / 60.0
            score = round(mins * 0.2, 2)
            if score > 0:
                for other in before_ch.members:
                    if not other.bot and other.id != uid:
                        _bump_score(uid, other.id, score)
                        _bump_score(other.id, uid, score)

    # joining a new channel — record start
    if after_ch and before_ch != after_ch:
        vc_join_times[uid] = datetime.utcnow()
