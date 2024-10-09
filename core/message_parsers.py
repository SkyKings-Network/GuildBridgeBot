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
        if "Top" in self.raw_message:
            print("Command: Top")
            return self._parse_top_message()
        elif "Total Members:" in self.raw_message:
            if "Offline Members:" in self.raw_message:
                print("Command: Online")
                return self._parse_online_message()
            else:
                print("Command: List")
                return self._parse_list_message()
        elif "MOTD" in self.raw_message:
            print("Command: Info")
            return self._create_guild_stats_embed()
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

    def _format_rank(self, rank: str) -> str:
        return f"**[{rank}]**" if rank else ""

    def _format_list_embed(self) -> List[discord.Embed]:
        embeds = []
        current_description = ""
        page_number = 1

        current_description += f"# {self.guild_name}\n\n"

        for role in self.roles:
            role_description = f"## {role.name}\n"
            member_texts = []
            for m in role.members:
                rank_format = self._format_rank(m.rank)
                member_text = f"{rank_format}{m.name}" if rank_format else m.name
                member_texts.append(member_text)
            
            role_description += ", ".join(member_texts) + "\n\n"
            
            # Check if adding this role would exceed the limit
            if len(current_description) + len(role_description) > 3000:
                embeds.append(discord.Embed(description=current_description.strip(), colour=0x1ABC9C))
                current_description = f"# {self.guild_name} (Continued)\n\n" + role_description
                page_number += 1
            else:
                current_description += role_description

        # Add statistics to the last embed
        stats_description = (
            f"## Guild Statistics\n"
            f"**Total Members:** {self.total_members}\n"
            f"**Online Members:** {self.online_members}\n"
            f"**Offline Members:** {self.offline_members}\n"
        )

        embeds.append(discord.Embed(description=current_description.strip(), colour=0x1ABC9C))
        current_description = f"# {self.guild_name} (Statistics)\n\n" + stats_description
        page_number += 1

        embeds.append(discord.Embed(description=current_description.strip(), colour=0x1ABC9C))

        # Update titles with page numbers
        total_pages = len(embeds)
        for i, embed in enumerate(embeds, 1):
            embed.title = f"{self.guild_name} - Page {i}/{total_pages}"

        return embeds


    def _format_online_embed(self) -> List[discord.Embed]:
        return self._format_list_embed()

    def _format_top_embed(self) -> List[discord.Embed]:
        embed = discord.Embed(title=f"Top Guild Experience - {self.date.strftime('%m/%d/%Y')} (today)", colour=0x1ABC9C)
        
        description = []
        for entry in self.top_entries:
            member = entry.member
            rank_format = HypixelRank.format_rank(member.rank)
            member_text = f"{rank_format}{member.name}" if rank_format else member.name
            description.append(
                f"### {entry.position}. {member_text}\n"
                f"**{entry.experience:,}** Guild Experience\n"
            )
        
        embed.description = "\n".join(description)
        return [embed]

    def _parse_guild_data(data_string):
        # Initialize dictionary to store parsed data
        guild_data = {}
        
        # Split into lines and process each line
        lines = data_string.strip().split('\n')
        
        # Parse the rest of the data
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'Created':
                    guild_data['created'] = value
                elif key == 'Members':
                    guild_data['members'] = value
                elif key == 'Guild Exp':
                    # Extract experience and rank
                    exp_rank = value.split()
                    guild_data['total_exp'] = exp_rank[0]
                    guild_data['rank'] = exp_rank[1].strip('()')
                elif key == 'Guild Level':
                    guild_data['level'] = value
                else:
                    # Parse daily experience entries
                    if re.match(r'(Today|[A-Za-z]+ \d{2} \d{4}):', line):
                        date, exp = line.split(':', 1)
                        if 'daily_exp' not in guild_data:
                            guild_data['daily_exp'] = []
                        guild_data['daily_exp'].append((date.strip(), exp.strip()))
        
        return guild_data

    def _create_guild_stats_embed(self):
        input_data = self.raw_message
        guild_data = self._parse_guild_data(input_data)
        
        embed = discord.Embed(
            title="Guild Statistics and Experience Report",
            description="",
            color=0x2F3136
        )
        
        # Add basic guild info
        guild_info = (
            f"**Created:** {guild_data.get('created', 'Unknown')}\n"
            f"**Members:** {guild_data.get('members', 'Unknown')}\n"
            f"**Guild Level:** {guild_data.get('level', 'Unknown')}\n"
            f"**Total Experience:** {guild_data.get('total_exp', 'Unknown')} {guild_data.get('rank', '')}"
        )
        embed.add_field(name="Guild Info", value=guild_info, inline=False)
        
        # Add daily experience data
        if 'daily_exp' in guild_data:
            exp_data = '\n'.join(f"{date}: {exp}" for date, exp in guild_data['daily_exp'])
            embed.add_field(
                name="Daily Guild Experience",
                value=f"```{exp_data}```",
                inline=False
            )
        
        # Set footer with timestamp
        embed.set_footer(text="Last Updated")
        embed.timestamp = datetime.utcnow()
        
        return [embed]
