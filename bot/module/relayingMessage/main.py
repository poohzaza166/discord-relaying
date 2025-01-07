# Copyright (C) 7/1/2025 by pooh email pooh@poohserver.com

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from typing import Dict, List, Union

import aiohttp
import discord
import yaml
from discord.channel import TextChannel
from discord.ext import commands
from discord.ext.commands import Context
from discord.message import Message
from discord.utils import get


class ForwardMessage(commands.Cog):
    """
    A cog that handles forwarding messages between Discord channels.
    Supports forwarding messages with custom emojis.
    """

    def __init__(self, client):
        """Initialize the ForwardMessage cog."""
        self.client = client
        self.listenChannel: Dict[int, List[int]] = {}
        self.load_config()

    def load_config(self):
        try:
            with open('config.yaml', 'r') as file:
                config = yaml.safe_load(file)
                if config and 'channels' in config:
                    for mapping in config['channels']:
                        if 'source' in mapping and 'targets' in mapping:
                            self.listenChannel[int(mapping['source'])] = mapping['targets']
        except FileNotFoundError:
            print("Config file not found, creating default...")
            self.save_config()
        except yaml.YAMLError as e:
            print(f"Error parsing config: {e}")

    def save_config(self):
        config = {
            'channels': [
                {'source': source, 'targets': targets} 
                for source, targets in self.listenChannel.items()
            ]
        }
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file, default_flow_style=False)

    @commands.command(
        brief="Set up message forwarding between channels",
        description="Configure a source channel to forward messages to a target channel",
        usage="<source_channel_id> <target_channel_id>"
    )
    async def setforward(self, ctx: Context, source: int, target: int):
        """
        Set up message forwarding from source to target channel.
        
        Parameters:
        -----------
        source: int
            The ID of the source channel
        target: int
            The ID of the target channel
        """
        if source not in self.listenChannel:
            self.listenChannel[source] = []
        if target not in self.listenChannel[source]:
            self.listenChannel[source].append(target)
            await ctx.send(f"Added forward from <#{source}> to <#{target}>")
        else:
            await ctx.send(f"Already forwarding from <#{source}> to <#{target}>")

    @commands.command(
        brief="List all active forwards",
        description="Shows all currently configured channel forwarding pairs"
    )
    async def listforward(self, ctx: Context):
        """Display all active channel forwarding configurations."""
        if not self.listenChannel:
            await ctx.send('No channels to forward to')
            return
        
        count = 0
        for source, targets in self.listenChannel.items():
            targets_str = ', '.join(f'<#{target}>' for target in targets)
            await ctx.send(f"{count}). <#{source}> forwarding to: {targets_str}")
            count += 1
    
    @commands.command(
        brief="Delete forwarding configuration",
        description="Remove forwarding from source to target channel",
        usage="<source_channel_id> <target_channel_id>"
    )
    async def delforward(self, ctx: Context, source: int, target: int):
        """
        Remove forwarding configuration between channels.
        """
        if source not in self.listenChannel:
            await ctx.send(f"Channel <#{source}> is not forwarding to any channel")
            return
            
        if target not in self.listenChannel[source]:
            await ctx.send(f"Channel <#{source}> is not forwarding to <#{target}>")
            return
            
        self.listenChannel[source].remove(target)
        
        # Remove source if no targets left
        if not self.listenChannel[source]:
            del self.listenChannel[source]
            
        self.save_config()
        await ctx.send(f"Removed forwarding from <#{source}> to <#{target}>")


    @commands.command(
        brief="Save current configuration",
        description="Save the current forwarding configuration to config.yaml"
    )
    async def saveconfig(self, ctx: Context):
        """Save current forwarding configuration to disk."""
        self.save_config()
        await ctx.reply("done")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Event listener for processing messages.
        Handles forwarding messages and emoji processing.
        """
        if message.author == self.client.user:
            return
        
        if message.channel.id not in self.listenChannel:
            return
        
        if message.content is None:
            return
        
        # Forward to all target channels
        for target_id in self.listenChannel[message.channel.id]:
            outch = get(message.guild.text_channels, id=target_id)
            if outch:
                await self.echomsg(message, outch)


        
    async def echomsg(self,message: Message, outch: TextChannel):
        """
        Process and forward a message to target channel.
        
        Parameters:
        -----------
        message: Message
            The original message to forward
        outch: TextChannel
            The target channel to forward to
        """
        emoji_data = await parse_emoji(message.content)
        print(emoji_data)
        if len(emoji_data) <= 0:
            return
        
        # add emoji
        for i in emoji_data:
            print(i)
            await outch.guild.create_custom_emoji(name=i[1], image=await download_emoji_image(i[0]))
        
        await outch.send(await self.replace_emoji_mentions(message))
        # remove emoji
        for i in emoji_data:
            await outch.guild.delete_emoji(get(message.guild.emojis, name=i[1]))
        
        

    async def replace_emoji_mentions(self, message: discord.Message) -> str:
        modified_content = message.content
        emoji_pattern = r'<(a?):([a-zA-Z0-9_]+):(\d+)>'
        
        # Find all emoji matches
        matches = re.finditer(emoji_pattern, message.content)
        
        for match in matches:
            animated, emoji_name, emoji_id = match.groups()
            # Get emoji object from guild
            emoji = get(message.guild.emojis, name=emoji_name)
            if emoji:
                # Replace emoji mention with actual emoji object string
                emoji_text = match.group(0)  # Original <:name:id> format
                modified_content = modified_content.replace(emoji_text, str(emoji))
        
        return modified_content

async def parse_emoji(message: str):
    emoji_data = []
    
    for emoji in message.split():
        try:
            if emoji.startswith("<:") or emoji.startswith("<a:"):
                # Extract emoji components
                emoji_parts = emoji.split(":")
                emoji_name = emoji_parts[1]
                emoji_id = emoji_parts[2].split(">")[0]
                
                # Handle animated vs static emoji
                extension = "gif" if emoji.startswith("<a:") else "webp"
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
                
                print(f"Found emoji: {emoji_name} ({emoji_url})")  # Debug log
                emoji_data.append((emoji_url, emoji_name))
                
        except (IndexError, ValueError) as e:
            print(f"Error parsing emoji {emoji}: {e}")
            continue
            
    return emoji_data 

# Function to download the emoji image
async def download_emoji_image(emoji_url):
    async with aiohttp.ClientSession() as session:
        # Download the emoji image using the emoji's URL
        async with session.get(emoji_url) as resp:
            if resp.status == 200:
                return await resp.read()
            return None

def setup(client):
    """Add the ForwardMessage cog to the bot."""
    client.add_cog(ForwardMessage(client))