from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import re

import discord

class HypixelRank:
    # Using emojis or special characters to represent different ranks
    RANK_FORMATS = {
        'VIP': '🟢',      # Green circle for VIP
        'VIP+': '🟢⭐',    # Green circle with star for VIP+
        'MVP': '🔷',      # Blue diamond for MVP
        'MVP+': '🔷⭐',    # Blue diamond with star for MVP+
        'MVP++': '🟡⭐',   # Gold circle with star for MVP++
        'ADMIN': '🔴',    # Red circle for ADMIN
        'HELPER': '💙',   # Blue heart for HELPER
        'MODERATOR': '💚' # Green heart for MODERATOR
    }

    @staticmethod
    def format_rank(rank: str) -> str:
        rank = rank.upper() if rank else ''
        emoji = HypixelRank.RANK_FORMATS.get(rank, '')
        return f'{emoji}**[{rank}]**' if rank else ''

@dataclass
class GuildMember:
    name: str
    rank: Optional[str] = None
    experience: Optional[int] = None

@dataclass
class GuildRole:
    name: str
    members: List[GuildMember]

@dataclass
class TopEntry:
    member: GuildMember
    experience: int
    position: int

class GuildMessageParser:
    def __init__(self, message: str):
        self.raw_message = message
        self.guild_name = ""
        self.total_members = 0
        self.online_members = 0
        self.offline_members = 0
        self.roles = []
        self.top_entries = []
        self.date = None
        
    def parse(self) -> str:
        # Determine message type and parse accordingly
        if "Top Guild Experience" in self.raw_message:
            return self._parse_top_message()
        elif "Total Members:" in self.raw_message:
            if "Offline Members:" in self.raw_message:
                return self._parse_online_message()
            else:
                return self._parse_list_message()
        else:
            return "NaN"
            
    def _clean_rank(self, rank: str) -> str:
        rank = rank.strip('[]').strip()
        rank = rank.rstrip(']')
        return rank

    def _extract_member_info(self, member_text: str) -> GuildMember:
        # Remove the bullet point
        member_text = member_text.replace('●', '').strip()
        
        # Extract rank if present
        rank_match = re.match(r'\[(MVP\+?|VIP\+?)\]\s+', member_text)
        if rank_match:
            rank = self._clean_rank(rank_match.group(0))
            name = member_text[rank_match.end():].strip()
            return GuildMember(name=name, rank=rank)
        return GuildMember(name=member_text)

    def _parse_list_message(self) -> str:
        lines = self.raw_message.split('\n')
        current_role = None
        current_members = []

        for line in lines:
            line = line.strip()
            
            if line.startswith('Guild Name:'):
                self.guild_name = line.replace('Guild Name:', '').strip()
                continue
                
            if line.startswith('--') and line.endswith('--'):
                if current_role:
                    self.roles.append(GuildRole(current_role, current_members))
                    current_members = []
                current_role = line.strip('- ')
                continue
                
            if '●' in line:
                # Split by bullet points and process each member
                members = line.split('●')
                for member in members:
                    if member.strip():
                        current_members.append(self._extract_member_info(member))
                        
            if line.startswith('Total Members:'):
                self.total_members = int(re.search(r'\d+', line).group())
            elif line.startswith('Online Members:'):
                self.online_members = int(re.search(r'\d+', line).group())

        # Add the last role if exists
        if current_role:
            self.roles.append(GuildRole(current_role, current_members))

        return self._format_list_embed()

    def _parse_online_message(self) -> str:
        self._parse_list_message()  # Reuse list parsing logic
        # Extract offline members
        for line in self.raw_message.split('\n'):
            if line.startswith('Offline Members:'):
                self.offline_members = int(re.search(r'\d+', line).group())
                break
        return self._format_online_embed()

    def _parse_top_message(self) -> str:
        lines = self.raw_message.split('\n')
        
        self.date = datetime.now().date()

        # Parse top entries
        for line in lines[1:]:  # Skip header
            if not line.strip():
                continue
                
            match = re.match(r'(\d+)\.\s+(.+?)\s+(\d+,?\d*)\s+Guild Experience', line)
            if match:
                position = int(match.group(1))
                member_text = match.group(2)
                experience = int(match.group(3).replace(',', ''))
                
                member = self._extract_member_info(member_text)
                member.experience = experience
                self.top_entries.append(TopEntry(member, experience, position))

        return self._format_top_embed()

    def _format_list_embed(self) -> List[discord.Embed]:
        embeds = []
        current_embed = None
        current_field = ""
        current_field_name = ""
        page_number = 1

        for role in self.roles:
            member_texts = [f"**[{m.rank}]**{m.name}" for m in role.members]
            role_text = f"**__{role.name}__**\n{', '.join(member_texts)}\n\n"
            
            if len(current_field) + len(role_text) > 1024 or not current_embed:
                if current_embed:
                    current_embed.add_field(name=current_field_name, value=current_field, inline=False)
                    embeds.append(current_embed)
                    page_number += 1

                current_embed = discord.Embed(title=f"{self.guild_name}", colour=0x1ABC9C)
                current_field = role_text
                current_field_name = "Members"
            else:
                current_field += role_text

        if current_field:
            current_embed.add_field(name=current_field_name, value=current_field, inline=False)

        # Add statistics to the last embed
        stats_field = (
            f"**Total Members:** {self.total_members}\n"
            f"**Online Members:** {self.online_members}\n"
            f"**Offline Members:** {self.offline_members}"
        )
        current_embed.add_field(name="Guild Statistics", value=stats_field, inline=False)
        
        embeds.append(current_embed)

        # Update titles with page numbers
        total_pages = len(embeds)
        for i, embed in enumerate(embeds, 1):
            embed.title = f"{self.guild_name} - Page {i}/{total_pages}"

        return embeds

    def _format_online_embed(self) -> List[discord.Embed]:
        return self._format_list_embed()

    def _format_top_embed(self) -> List[discord.Embed]:
        embed = discord.Embed(title=f"Top Guild Experience - {self.date.strftime('%m/%d/%Y')} (today)", colour=0x1ABC9C)
        
        for entry in self.top_entries:
            member = entry.member
            rank_format = HypixelRank.format_rank(member.rank)
            member_text = f"{rank_format}{member.name}" if rank_format else member.name
            embed.add_field(
                name=f"{entry.position}. {member_text}",
                value=f"**{entry.experience:,}** Guild Experience",
                inline=False
            )
        
        return [embed]