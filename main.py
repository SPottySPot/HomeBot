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
discordToken = os.getenv("DISCORD_TOKEN")
guildID = 1385949023642587328 #id for test server
guild = discord.Object(id=guildID)
nanoleafToken = os.getenv("NANOLEAF_TOKEN")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot( # remainder of .commands that are being phased out
    command_prefix='.',
    intents=intents
)

recipes = ["dish", "ingredients", "steps"]
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

def CreateRecipeEmbed(recipe, title=None):
    if title is None:
        title = recipe['dish']

    ingredients = str(recipe['ingredients']).split(',')
    steps = str(recipe['steps']).split(',')

    ingredientText = ""
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        ingredient = ingredient.strip("[]'\"")
        ingredientText += f"- {ingredient}\n"

    stepText = ""
    for step in steps:
        step = step.strip()
        step = step.strip("[]'\"")
        stepText += f"- {step}\n"

    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Ingredients",
        value=ingredientText if ingredientText else "-",
        inline=False
    )

    embed.add_field(
        name="Steps",
        value=stepText if stepText else "-",
        inline=False
    )
    return embed

def CreateErrorEmbed(message):
    embed = discord.Embed(
        title="Error",
        description=message,
        color=discord.Color.red()
    )
    return embed

#stops the bot from reading its own messages
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def recipe(ctx):

    embed = discord.Embed(
        title="Recipe Bot Commands",
        color=discord.Color.blue()
    )

    embed.add_field(
        name=".recipe",
        value="Show the list of available commands.",
        inline=False
    )

    embed.add_field(
        name=".addRecipe",
        value="Add a new recipe.\n"
              "`.addRecipe dish|ingredient 1, ingredient 2|step 1, step 2`",
        inline=False
    )

    embed.add_field(
        name=".readRecipe",
        value="View a recipe.\n"
              "`.readRecipe dish`",
        inline=False
    )

    embed.add_field(
        name=".listRecipes",
        value="List all available recipes.",
        inline=False
    )

    embed.add_field(
        name=".randomRecipe",
        value="Get a random recipe.",
        inline=False
    )

    embed.add_field(
        name=".findIngredient",
        value="Find recipes containing an ingredient.\n"
              "`.findIngredient ingredient`",
        inline=False
    )

    embed.add_field(
        name=".editRecipe",
        value="Edit an existing recipe.\n"
              "`.editRecipe old dish|new dish|ingredients|steps`",
        inline=False
    )

    embed.add_field(
        name=".deleteRecipe",
        value="Delete a recipe.\n"
              "`.deleteRecipe dish`",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command()
async def addRecipe(ctx, *, recipe=None):
    readRecipesDF()
    global recipesDF

    if not recipe:
        await ctx.send(
            embed=CreateErrorEmbed(
                "Please provide a full recipe.\n\n"
                "Example:\n"
                ".addRecipe pasta|1 cup, 2 eggs|cook pasta, add eggs"
            )
        )
        return

    x = recipe.split('|')
    if len(x) != 3:
        await ctx.send(
            embed=CreateErrorEmbed(
                "Please provide a full recipe.\n\n"
                "Format:\n"
                ".addRecipe dish|ingredient 1, ingredient 2|step 1, step 2"
            )
        )
        return

    dish = x[0].strip()
    ingredients = x[1].strip()
    steps = x[2].strip()

    data = {
        "dish": dish,
        "ingredients": ingredients,
        "steps": steps
    }

    recipesDF.loc[len(recipesDF)] = data
    recipesDF.to_csv('./recipes.csv', index=False)
    recipe = recipesDF.iloc[-1]
    embed = CreateRecipeEmbed(recipe, f"{dish} - Recipe Added")
    await ctx.send(embed=embed)

@bot.command()
async def readRecipe(ctx, *, recipeName=None):
    readRecipesDF()

    if not recipeName:
        await ctx.send(embed=CreateErrorEmbed("Please provide a recipe name."))
        return

    recipeRow = recipesDF[recipesDF['dish'].str.lower() == recipeName.lower()]

    if recipeRow.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(recipeRow) != 1:
        await ctx.send(embed=CreateErrorEmbed("There are multiple recipes with that name."))
        return

    recipe = recipeRow.iloc[0]
    embed = CreateRecipeEmbed(recipe)
    await ctx.send(embed=embed)

@bot.command()
async def listRecipes(ctx):
    readRecipesDF()

    if recipesDF.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no recipes available."))
        return

    dishes = []
    for i, dish in recipesDF.iterrows():
        dishes.append(f"- {dish['dish']}")
    message = "\n".join(dishes)
    embed = discord.Embed(
        title="Available Recipes",
        description=message,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def randomRecipe(ctx):
    readRecipesDF()

    if recipesDF.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no recipes available."))
        return

    ran = random.randint(1, 100)
    if ran == 100:
        embed = discord.Embed(
            title="Random Recipe",
            description="You Win. Go out for dinner instead!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return

    ran = random.randint(0, len(recipesDF) - 1)
    recipe = recipesDF.iloc[ran]
    embed = CreateRecipeEmbed(recipe, "Random Recipe")
    await ctx.send(embed=embed)

@bot.command()
async def findIngredient(ctx, *, ingredient=None):
    readRecipesDF()

    if not ingredient:
        await ctx.send(embed=CreateErrorEmbed("Please provide an ingredient."))
        return

    recipeRow = recipesDF[
        recipesDF['ingredients'].str.contains(
            ingredient,
            case=False,
            na=False
        )]

    if recipeRow.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no dishes with that ingredient."))
        return

    dishes = []
    for index, recipe in recipeRow.iterrows():
        dishes.append(f"- {recipe['dish']}")
    message = "\n".join(dishes)
    embed = discord.Embed(
        title="Recipes Found",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f"Recipes containing {ingredient}",
        value=message,
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command()
async def editRecipe(ctx, *, recipe=None):
    readRecipesDF()
    global recipesDF

    if not recipe:
        await ctx.send(embed=CreateErrorEmbed("Please provide the original dish name, new dish name, ingredients and steps."))
        return

    x = recipe.split('|')
    if len(x) != 4:
        await ctx.send(
            embed=CreateErrorEmbed(
                "Please provide the original dish name, "
                "new dish name, ingredients and steps.\n\n"
                "Format:\n"
                ".editRecipe old dish|new dish|ingredients|steps"
            )
        )
        return
    oldDish = x[0].strip()
    newDish = x[1].strip()
    ingredients = x[2].strip()
    steps = x[3].strip()

    recipeRow = recipesDF[recipesDF['dish'].str.lower() == oldDish.lower()]

    if recipeRow.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(recipeRow) != 1:
        await ctx.send(embed=CreateErrorEmbed("There are multiple recipes with that name."))
        return

    index = recipeRow.index[0]
    newRecipe = {
        "dish": newDish,
        "ingredients": ingredients,
        "steps": steps
    }
    embed = CreateRecipeEmbed(
        newRecipe,
        "Edit Recipe"
    )
    embed.add_field(
        name="Confirmation",
        value="React with the appropriate option to confirm or cancel the changes.",
        inline=False
    )

    confirmMessage = await ctx.send(embed=embed)
    await confirmMessage.add_reaction("✅")
    await confirmMessage.add_reaction("❌")
    def check(checkedReaction, checkedUser):
        return (
            checkedUser == ctx.author
            and checkedReaction.message.id == confirmMessage.id
            and str(checkedReaction.emoji) in ["✅", "❌"]
        )
    try:
        selectedReaction, selectedUser = await bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=check
        )
        if str(selectedReaction.emoji) == "❌":

            await ctx.send(
                embed=discord.Embed(
                    title="Edit Cancelled",
                    description="The recipe was not changed.",
                    color=discord.Color.blue()
                )
            )
            return

        recipesDF.loc[index, 'dish'] = newDish
        recipesDF.loc[index, 'ingredients'] = ingredients
        recipesDF.loc[index, 'steps'] = steps
        recipesDF.to_csv('./recipes.csv', index=False)
        await ctx.send(
            embed=discord.Embed(
                title="Recipe Updated",
                description=f"Recipe '{newDish}' has been updated.",
                color=discord.Color.blue()
            ))

    except TimeoutError:
        await ctx.send(
            embed=discord.Embed(
                title="Edit Cancelled",
                description="The confirmation timed out.",
                color=discord.Color.blue()
            ))

@bot.command()
async def deleteRecipe(ctx, *, recipeName=None):
    readRecipesDF()
    global recipesDF

    if not recipeName:
        await ctx.send(embed=CreateErrorEmbed("Please provide a recipe name."))
        return

    recipeRow = recipesDF[recipesDF['dish'].str.lower() == recipeName.lower()]

    if recipeRow.empty:
        await ctx.send(embed=CreateErrorEmbed("There are no dishes with that name."))
        return

    if len(recipeRow) != 1:
        await ctx.send(embed=CreateErrorEmbed("There are multiple recipes with that name."))
        return

    recipe = recipeRow.iloc[0]

    embed = CreateRecipeEmbed(
        recipe,
        "Delete Recipe"
    )
    embed.add_field(
        name="Confirmation",
        value="React with the appropriate option to confirm or cancel deletion.",
        inline=False
    )
    confirmMessage = await ctx.send(embed=embed)
    await confirmMessage.add_reaction("✅")
    await confirmMessage.add_reaction("❌")
    def check(checkedReaction, checkedUser):

        return (
            checkedUser == ctx.author
            and checkedReaction.message.id == confirmMessage.id
            and str(checkedReaction.emoji) in ["✅", "❌"]
        )
    try:
        selectedReaction, selectedUser = await bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=check
        )
        if str(selectedReaction.emoji) == "❌":

            await ctx.send(
                embed=discord.Embed(
                    title="Deletion Cancelled",
                    description="The recipe was not deleted.",
                    color=discord.Color.blue()
                ))
            return

        recipesDF = recipesDF.drop(recipeRow.index)
        recipesDF.to_csv('./recipes.csv', index=False)
        await ctx.send(
            embed=discord.Embed(
                title="Recipe Deleted",
                description=f"Recipe '{recipe['dish']}' has been deleted.",
                color=discord.Color.blue()
            )
        )

    except TimeoutError:

        await ctx.send(
            embed=discord.Embed(
                title="Deletion Cancelled",
                description="The confirmation timed out.",
                color=discord.Color.blue()
            ))

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
recipeGroup = app_commands.Group(name="recipe", description="Recipe management")

@recipeGroup.command(name="help", description="lists the different help commands for the recipe Manager")
async def recipeHelpCommand(interaction: discord.Interaction):

    recipeHelpEmbed = discord.Embed(
        title="Recipe Bot Commands",
        color=discord.Color.blue()
    )
    recipeHelpEmbed.add_field(
        name="/recipe help",
        value="Show the list of available recipe commands.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe list",
        value="shows a list of all recipes",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe read",
        value="gets a recipe by name and returns the recipe",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe add",
        value="adds a new recipe to the database.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe ingredient",
        value="Find recipes containing an ingredient.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe edit",
        value="finds the recipe with the name given and changes all the details to the new ones",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe delete",
        value="deletes a recipe from the database.",
        inline=False
    )
    recipeHelpEmbed.add_field(
        name="/recipe random",
        value="selects a random recipe from the database",
        inline=False
    )
    await interaction.response.send_message(embed=recipeHelpEmbed)

@recipeGroup.command(name="list", description="shows a list of all recipes")
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

@recipeGroup.command(name="read", description="gets a recipe by name and returns the recipe")
@app_commands.describe(dish="The name of the recipe",)
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
    isEdit = False

    def __init__(self, title, dish=None, index=None,):
        super().__init__(title=title)

        if dish is not None:
            self.dish.default = str(dish["dish"])
            self.servings.default = str(dish["servings"])
            self.ingredients.default = str(dish["ingredients"])
            self.steps.default = str(dish["steps"])
            self.isEdit = True
            self.index = index

    async def on_submit(self, interaction):
        readRecipesDF()

        if self.isEdit:
            recipesDF.loc[self.index, 'dish'] = self.dish.value
            recipesDF.loc[self.index, 'servings'] = self.servings.value
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


@recipeGroup.command(name="add", description="adds a new recipe to the database.")#TODO
async def recipeAddCommand(interaction: discord.Interaction):
    await interaction.response.send_modal(RecipeModal("Add New Recipe"))

@recipeGroup.command(name="edit", description="finds the recipe with the name given and changes all the details to the new ones")#TODO
async def recipeEditCommand(interaction: discord.Interaction, dish: str):
    global recipesDF
    readRecipesDF()

    found = recipesDF[
        recipesDF["dish"].str.lower() == dish.lower()
        ]

    if found.empty:
        await interaction.response.send_message(
            embed=CreateErrorEmbed("There are no dishes with that name.")
        )
        return

    if len(found) > 1:
        await interaction.response.send_message(
            embed=CreateErrorEmbed("There is more than one dish with that name.")
        )
        return
    index = found.index[0]
    await interaction.response.send_modal(RecipeModal("Edit Old Recipe", found.iloc[0], index=index))

@recipeGroup.command(name="delete", description="deletes a recipe from the database.")
async def recipeDeleteCommand(interaction: discord.Interaction, dish: str):
    readRecipesDF()
    global recipesDF

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

    def check(reaction, user):
        return (
                user == interaction.user
                and reaction.message.id == confirmMessage.id
                and str(reaction.emoji) in ["✅", "❌"]
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

        recipesDF = recipesDF.drop(found.index)
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

@recipeGroup.command(name="ingredient", description="Find recipes containing an ingredient.")
async def recipeIngredientCommand(interaction: discord.Interaction, ingredient: str):
    readRecipesDF()

    found = recipesDF[recipesDF['ingredient'].str.contains(ingredient, case=False)]

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

@recipeGroup.command(name="random", description="selects a random recipe from the database")
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