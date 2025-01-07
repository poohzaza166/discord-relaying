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
import os

import discord
import yaml
from discord.ext import commands


class CustomHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="Discord Relay Bot Help",
            color=discord.Color.blue()
        )
        
        # Add credits
        embed.add_field(
            name="Credits",
            value="Created by Pooh (pooh@poohserver.com)",
            inline=False
        )
        
        # Add commands list
        for cog, cmds in mapping.items():
            if not cmds:
                continue
            
            commands_list = [f"`{cmd.name}`: {cmd.brief}" for cmd in cmds if not cmd.hidden]
            if commands_list:
                embed.add_field(
                    name=getattr(cog, "qualified_name", "Commands"),
                    value="\n".join(commands_list),
                    inline=False
                )
        
        await self.get_destination().send(embed=embed)

# Initialize bot with custom help
bot = commands.Bot(
    command_prefix="!",
    intents=discord.Intents.all(),
    help_command=CustomHelpCommand()
)
    



@bot.listen()
async def on_ready():
    print("starting")

@bot.command(description="Sends the bot's latency.") # this decorator makes a slash command
async def ping(ctx): # a slash command will be created with the name "ping"
    await ctx.respond(f"Pong! Latency is {bot.latency}")

bot.load_extension(name="bot.module.relayingMessage.main")

if __name__ == "__main__":
  
    TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("No token found. Set DISCORD_BOT_TOKEN environment variable")
    bot.run(TOKEN)