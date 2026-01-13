# cogs/ping/messages.py
from __future__ import annotations
import discord

def embed_ok(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=discord.Color.green())
    return e

def embed_err(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=discord.Color.red())
    return e

def embed_info(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=discord.Color.blurple())
    return e
