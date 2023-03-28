import discord
from discord.ui import Select, View
from discord.ext import commands
from discord import app_commands

import os
import json

with open("cogs/jsons/settings.json") as json_file:
    data_dict = json.load(json_file)
    guild_id = data_dict["guild_id"]

class BotManager(commands.Cog):
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="reload", description="Reloads cogs.")
    @app_commands.checks.has_role("Moderator")
    async def reload(self, interaction: discord.Interaction):
        options = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                item = discord.SelectOption(label=f'cogs.{filename}')
                options.append(item)
        async def my_callback(interaction):
            for cog in select.values:
                await self.bot.reload_extension(f"{cog[:-3]}")
            selected_values = "\n".join(select.values)
            await interaction.response.send_message(f'Reloaded the following cog:\n{selected_values}')

        select = Select(min_values = 1, max_values = int(len(options)), options=options)   
        select.callback = my_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message(f'Please select the cog you would like to reload.', view=view)
    
    @reload.error
    async def reloadError(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("You do not have the permission to use this command.", ephemeral=True)
            
    @app_commands.command(name="stop", description="Stops cogs.")
    @app_commands.checks.has_role("Moderator")
    async def stop(self, interaction: discord.Interaction):
        if interaction.command_failed:
            await interaction.response.send_message(f'I had a brain fart, try again please.', ephemeral=True)
        options = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                item = discord.SelectOption(label=f'cogs.{filename}')
                options.append(item)
        async def my_callback(interaction):
            for cog in select.values:
                await self.bot.unload_extension(f"{cog[:-3]}")
            selected_values = "\n".join(select.values)
            await interaction.response.send_message(f'Unloaded the following cog:\n{selected_values}')

        select = Select(min_values = 1, max_values = int(len(options)), options=options)   
        select.callback = my_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message(f'Please select the cog you would like to reload.', view=view)

    @stop.error
    async def stopError(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("You do not have the permission to use this command.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BotManager(bot), guilds=[discord.Object(id=guild_id)])
