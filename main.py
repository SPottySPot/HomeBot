import discord
from discord import app_commands
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import pandas as pd
from pandas.errors import EmptyDataError
import random
import socket
from nanoleafapi import Nanoleaf, discovery
import requests

load_dotenv()
discordToken = os.getenv("DISCORD_TOKEN", "")
guildID = int(os.getenv("guild_id", "0")) #id for test server
guild = discord.Object(id=guildID)
nanoleafToken = os.getenv("NANOLEAF_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='.', intents=intents)

recipes = ["dish", "servings", "ingredients", "steps"]
recipesDF = pd.DataFrame(columns=recipes)

nanoleafIP = None

#current implementation for getting nanoleaf ip
def discoverNanoleaf():
    global nanoleafIP

    message = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 3\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    )

    socketInstance = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
        socket.IPPROTO_UDP
    )
    socketInstance.settimeout(5)
    socketInstance.sendto(
        message.encode(),
        ("239.255.255.250", 1900)
    )

    try:
        while True:
            response, address = socketInstance.recvfrom(4096)
            response = response.decode(errors="ignore")

            if "nanoleaf" in response.lower():
                print(f"Nanoleaf found at: {address[0]}")

                for line in response.split("\r\n"):
                    if line.lower().startswith("location:"):
                        location = line.split(":", 1)[1].strip()

                        nanoleafIP = location.split("//")[1].split(":")[0]

                        print(f"Nanoleaf IP: {nanoleafIP}")
                        break

                if nanoleafIP:
                    break

    except socket.timeout:
        pass

    socketInstance.close()

    return nanoleafIP

@bot.event
async def on_ready():
    print('Online!')
    readRecipesDF()

    #DiscoverNanoleaf()

    #global nanoleafURL
    #nanoleafURL = f"http://{nanoleafIP}:16021/api/v1"
    #response = requests.get(
        #f"{nanoleafURL}/{nanoleafToken}/state"
    #)
    #print(response.status_code)
    #print(response.text)

    #clears the global commands sync
    #bot.tree.clear_commands(guild=none)
    #await bot.tree.sync()

    #syncs commands list with specifically my guild
    syncedCommands = await bot.tree.sync(guild=guild)
    print("Synced commands:")
    for command in syncedCommands:
        print(f"- /{command.name}")
    print("Initialised")

#reads the recipes.csv and writes it to the recipesDF. used for updating during use
def readRecipesDF():
    global recipesDF

    try:
        recipesDF = pd.read_csv("./recipes.csv")
    except FileNotFoundError:
        recipesDF = pd.DataFrame(columns=recipes)
        recipesDF.to_csv('./recipes.csv', index=False)
    except EmptyDataError:
        recipesDF = pd.DataFrame(columns=recipes)

def CreateRecipeEmbed(dish, title=None):
    if title is None:
        title = dish['dish']

    servings = str(dish['servings'])
    ingredients = str(dish['ingredients']).splitlines()
    steps = str(dish['steps']).splitlines()

    ingredientText = ""
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        ingredientText += f"- {ingredient}\n"

    stepText = ""
    for step in steps:
        step = step.strip()
        stepText += f"- {step}\n"

    embed = discord.Embed(title=title,color=discord.Color.blue())
    embed.add_field(name="Servings",value=servings,inline=False)
    embed.add_field(name="Ingredients",value=ingredientText if ingredientText else "-",inline=False)
    embed.add_field(name="Steps",value=stepText if stepText else "-",inline=False)
    return embed

def CreateErrorEmbed(message):
    embed = discord.Embed(title="Error",description=message,color=discord.Color.red())
    return embed

#responds with a list of the different help commands
@app_commands.command(name="help", description="lists the different help commands")
async def helpCommand(interaction: discord.Interaction):
    helpEmbed = discord.Embed(
        title="Help Commands",
        color=discord.Color.blue()
    )
    helpEmbed.add_field(
        name="/recipe help",
        value="View commands for managing and searching recipes.",
        inline=False
    )
    helpEmbed.add_field(
        name="/light help",
        value="View commands for controlling the smart lights.",
        inline=False
    )
    helpEmbed.add_field(
        name="/task help",
        value="View commands for managing tasks, schedules and timers.",
        inline=False
    )
    await interaction.response.send_message(embed=helpEmbed)

#creates the group to add recipe commands to
recipeGroup = app_commands.Group(name="recipe", description="Manage, search, and browse saved recipes.")

@recipeGroup.command(name="help",description="Display the available recipe commands and their descriptions.")
async def recipeHelpCommand(interaction: discord.Interaction):
    recipeHelpEmbed = discord.Embed(
        title="Recipe Bot Commands",
        color=discord.Color.blue()
    )
    recipeHelpEmbed.add_field(
        name="/recipe help",
        value="Display the available recipe commands and their descriptions.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe list",
        value="Display a list of all saved recipes.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe read [dish]",
        value="Search for a recipe by dish name and display its details. If multiple recipes match, display the matching names.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe add",
        value="Open a form to add a recipe, including its name, servings, ingredients, and steps. Enter each ingredient and step on a separate line.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe edit [dish]",
        value="Find a recipe by dish name and open a pre-filled form to update its name, servings, ingredients, and steps.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe delete [dish]",
        value="Find and review a recipe, then confirm whether to delete it.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe ingredient [ingredient]",
        value="Find recipes containing the specified ingredient and display the matching recipes.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe random",
        value="Display a randomly selected saved recipe, with a small chance of suggesting you eat out instead.",
        inline=False
    )
    await interaction.response.send_message(embed=recipeHelpEmbed)

@recipeGroup.command(name="list", description="Display a list of all saved recipes.")
async def recipeListCommand(interaction: discord.Interaction):
    readRecipesDF()
    if recipesDF.empty:
        await interaction.response.send_message("There are no recipes in the database.")
        return

    dishes = []
    for i, dish in recipesDF.iterrows():
        dishes.append(f"- {dish['dish']}")

    message = "\n".join(dishes)
    recipeListEmbed = discord.Embed(
        title="Available Recipes",
        description=message,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=recipeListEmbed)

@recipeGroup.command(name="read", description="Search for a recipe by dish name and display its details.")
@app_commands.describe(dish="Enter the name of the dish")
async def recipeReadCommand(interaction: discord.Interaction, dish: str):
    readRecipesDF()

    found = recipesDF[recipesDF['dish'].str.contains(dish, case=False)]

    if found.empty:
        await interaction.response.send_message(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(found) > 1:
        dishes = []

        for i, dish in found.iterrows():
            dishes.append(f"- {dish['dish']}")

        message = "\n".join(dishes)
        recipeFoundEmbed = discord.Embed(
            title="Recipes Found",
            description=message,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=recipeFoundEmbed)
        return

    embed = CreateRecipeEmbed(found.iloc[0])
    await interaction.response.send_message(embed=embed)

class RecipeModal(discord.ui.Modal):

    dish = discord.ui.TextInput(label="Dish", required=True)
    servings = discord.ui.TextInput(label="Servings", required=True)
    ingredients = discord.ui.TextInput(
        label="Ingredients",
        style=discord.TextStyle.paragraph,
        required=True
    )
    steps = discord.ui.TextInput(
        label="Steps",
        style=discord.TextStyle.paragraph,
        required=True
    )

    def __init__(self, title, dish=None, index=None,):
        super().__init__(title=title)
        self.isEdit = False
        self.index = index

        if dish is not None:
            self.dish.default = str(dish["dish"])
            self.servings.default = str(dish["servings"])
            self.ingredients.default = str(dish["ingredients"])
            self.steps.default = str(dish["steps"])
            self.isEdit = True

    async def on_submit(self, interaction):
        if self.isEdit:
            recipesDF.loc[self.index, 'dish'] = self.dish.value
            recipesDF.loc[self.index, 'servings'] = int(self.servings.value)
            recipesDF.loc[self.index, 'ingredients'] = self.ingredients.value
            recipesDF.loc[self.index, 'steps'] = self.steps.value
            recipesDF.to_csv('./recipes.csv', index=False)

            dish = recipesDF.loc[self.index]
            embed = CreateRecipeEmbed(dish, f"{self.dish.value} - Recipe Updated")
            await interaction.response.send_message(embed=embed)
            return

        data = {
            "dish": self.dish.value,
            "servings": self.servings.value,
            "ingredients": self.ingredients.value,
            "steps": self.steps.value
        }
        recipesDF.loc[len(recipesDF)] = data
        recipesDF.to_csv('./recipes.csv', index=False)
        dish = recipesDF.iloc[-1]
        embed = CreateRecipeEmbed(dish, f"{self.dish.value} - Recipe Added")
        await interaction.response.send_message(embed=embed)

@recipeGroup.command(name="add", description="Add a new recipe using a form.")
async def recipeAddCommand(interaction: discord.Interaction):
    readRecipesDF()
    await interaction.response.send_modal(RecipeModal("Add New Recipe"))

@recipeGroup.command(name="edit", description="Edit an existing recipe by its dish name.")
@app_commands.describe(dish="Enter the name of the dish")
async def recipeEditCommand(interaction: discord.Interaction, dish: str):
    global recipesDF
    readRecipesDF()

    found = recipesDF[recipesDF['dish'].str.contains(dish, case=False)]

    if found.empty:
        await interaction.response.send_message(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(found) > 1:
        await interaction.response.send_message(embed=CreateErrorEmbed("There is more than one dish with that name."))
        return

    index = found.index[0]
    await interaction.response.send_modal(RecipeModal("Edit Old Recipe", found.iloc[0], index=index))

@recipeGroup.command(name="delete", description="Review a recipe and confirm whether to delete it.")
@app_commands.describe(dish="Enter the name of the dish")
async def recipeDeleteCommand(interaction: discord.Interaction, dish: str):
    global recipesDF
    readRecipesDF()

    found = recipesDF[recipesDF["dish"].str.contains(dish, case=False)]

    if found.empty:
        await interaction.response.send_message(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(found) > 1:
        dishes = []

        for i, dish in found.iterrows():
            dishes.append(f"- {dish['dish']}")

        message = "\n".join(dishes)
        recipeFoundEmbed = discord.Embed(
            title="Recipes Found",
            description=message,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=recipeFoundEmbed)
        return

    dish = found.iloc[0]

    # Display the recipe normally
    recipeEmbed = CreateRecipeEmbed(dish)
    await interaction.response.send_message(embed=recipeEmbed)

    # Confirmation embed
    confirmEmbed = discord.Embed(
        title="Confirm Deletion",
        description=f"Would you like to delete **{dish['dish']}**?",
        color=discord.Color.red()
    )

    confirmMessage = await interaction.followup.send(
        embed=confirmEmbed,
        wait=True
    )

    await confirmMessage.add_reaction("✅")
    await confirmMessage.add_reaction("❌")

    def check(addedReaction, activeUser):
        return (
                activeUser == interaction.user
                and addedReaction.message.id == confirmMessage.id
                and str(addedReaction.emoji) in ["✅", "❌"]
        )
    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=check
        )
        if str(reaction.emoji) == "❌":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Deletion Cancelled",
                    description="The recipe was not deleted.",
                    color=discord.Color.blue()
                )
            )
            return

        recipesDF = recipesDF.drop(found.index).reset_index(drop=True)
        recipesDF.to_csv("./recipes.csv", index=False)

        await interaction.followup.send(
            embed=discord.Embed(
                title="Recipe Deleted",
                description=f"Recipe '{dish['dish']}' has been deleted.",
                color=discord.Color.blue()
            )
        )
    except TimeoutError:
        await interaction.followup.send(
            embed=discord.Embed(
                title="Deletion Cancelled",
                description="The confirmation timed out.",
                color=discord.Color.blue()
            )
        )

@recipeGroup.command(name="ingredient", description="Find recipes containing a specific ingredient.")
@app_commands.describe(ingredient="Enter the name of an ingredient")
async def recipeIngredientCommand(interaction: discord.Interaction, ingredient: str):
    readRecipesDF()

    found = recipesDF[recipesDF['ingredients'].str.contains(ingredient, case=False)]

    if found.empty:
        await interaction.response.send_message(embed=CreateErrorEmbed("There are no dishes with that ingredient."))
        return

    if len(found) > 1:
        dishes = []
        for i, dish in found.iterrows():
            dishes.append(f"- {dish['dish']}")

        message = "\n".join(dishes)
        recipeFoundEmbed = discord.Embed(
            title="Recipes Found",
            description=message,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=recipeFoundEmbed)
        return

    embed = CreateRecipeEmbed(found.iloc[0])
    await interaction.response.send_message(embed=embed)

@recipeGroup.command(name="random", description="Display a randomly selected saved recipe.")
async def recipeRandomCommand(interaction: discord.Interaction):
    readRecipesDF()

    if recipesDF.empty:
        await interaction.response.send_message(embed=CreateErrorEmbed("There are no recipes in the database."))
        return

    ran = random.randint(1, 100)
    if ran == 100:
        await interaction.response.send_message(embed = discord.Embed(
            title="Random Recipe",
            description="You Win. Go out for food instead!",
            color=discord.Color.blue()
        ))
        return

    ran = random.randint(0, len(recipesDF)-1)
    dish = recipesDF.iloc[ran]
    await  interaction.response.send_message(embed=CreateRecipeEmbed(dish))

bot.tree.add_command(helpCommand, guild=guild)
bot.tree.add_command(recipeGroup, guild=guild)
#add later
#bot.tree.add_command(lightGroup, guild=guild)
#bot.tree.add_command(taskGroup, guild=guild)


bot.run(discordToken, log_handler=handler, log_level=logging.DEBUG)