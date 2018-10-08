__author__ = "Jesse Williams"
__license__ = "MIT"
__version__ = "1.1"

"""
Jeeves
A(nother) WoW discord bot.
"""


from functools import reduce
from os import path, remove, listdir, getenv
import json, asyncio
import discord
import WQSearch

script_dir = path.dirname(__file__)
watchlist_filepath = path.join(script_dir, "userdata", "wq_watchlists")


# Get Discord private token
if getenv("DISCORD_TOKEN"):
    TOKEN = getenv("DISCORD_TOKEN")
with open(path.join(script_dir, "secret", "key.txt"), "r") as f:
    TOKEN = f.read()
client = discord.Client()


botChannels = ["ask-jeeves", "bot-sandbox"]
bot_watchlist_channel = "ask-jeeves"

pronouns = ["She/Her", "He/Him", "They/Them", "Ze/Zir", "Xe/Xir"]


# Lists of valid commands with descriptions.
commands_general = {"!commands, !help": "Displays this message."}
commands_wq = {
    "!wqscan": "Scan active WQs for an item or list of items.  e.g. *!wqscan Dinobone Charm, spellstaff, Wristwraps*",
    "!wqwatch": "Add an item or list of items to your WQ watchlist. You will be notified when an item matching any of these terms appears in an active WQ.  e.g. *!wqwatch Dinobone Charm*",
    "!wqwatch slot:<slotname>": "Be notified when an item that goes in the slot appears in an active WQ. e.g. *!wqwatch slot:weapon, slot:head*",
    "!wqwatchlist": "Displays your list of currently saved watchlist items.",
    "!wqremove": "Removes an item from your watchlist. Make sure to type the item exactly as it appears in your watchlist.  e.g. *!wqremove Wristwraps*",
    "!wqclear": "Clears your entire list of watched items.",
}
commands_pronouns = {
    "!pronouns add": "Allows you to add a set of pronouns to your roles in Discord.",
    "!pronouns remove": "Allows you to remove a set of pronouns from your roles in Discord.",
}

commands_all = {
    "General": commands_general,
    "World Quests": commands_wq,
    "Pronouns": commands_pronouns,
}


f_pronouns_add = []
f_pronouns_remove = []
flags_all = [f_pronouns_add, f_pronouns_remove]


async def commandHandler(message):

    ########################
    ### General Commands ###

    ## !help / !commands
    cmds = ["!commands", "!help"]
    if message.content.strip() in cmds:
        msg = _getCommandList()
        await message.channel.send(msg)

    ###################
    ### WQ Commands ###

    ## !wqscan
    cmd = "!wqscan "
    if message.content.startswith(cmd):
        args = message.content[len(cmd) :].strip().split(", ")
        items, slots = WQSearch.parse_slots(args)

        results = WQSearch.searchWQs(items=items, slots=slots)
        results_string = _parseWQResultsList(results, message)
        await message.channel.send(results_string)

    ## !wqwatch
    cmd = "!wqwatch "
    if message.content.startswith(cmd):

        items = message.content[len(cmd) :].strip().split(", ")

        watchlist = {}
        watchlist["username"] = message.author.name
        watchlist["usermention"] = message.author.mention
        watchlist["items"] = items

        try:
            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "x"
            ) as f:
                json.dump(watchlist, f)

            await message.channel.send(
                "{}'s watchlist saved.".format(message.author.mention)
            )

        except FileExistsError:
            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "r"
            ) as f:
                old_watchlist = json.load(f)
                watchlist["items"] = old_watchlist["items"] + watchlist["items"]

            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "w"
            ) as f:
                json.dump(watchlist, f)

            await message.channel.send(
                "{}'s watchlist updated.".format(message.author.mention)
            )

    ## !wqwatchlist
    cmd = "!wqwatchlist"
    if message.content.strip() == cmd:
        try:
            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "r"
            ) as f:
                watchlist = json.load(f)
                watchlist_items = "__" + "__, __".join(watchlist["items"]) + "__"
                await message.channel.send(
                    "{}'s watchlist items: {}".format(
                        message.author.mention, watchlist_items
                    )
                )
        except OSError:
            await message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )

    ## !wqremove
    cmd = "!wqremove "
    if message.content.startswith(cmd):
        items = message.content[len(cmd) :].strip().split(", ")

        try:
            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "r"
            ) as f:
                watchlist = json.load(f)

            new_itemlist = watchlist["items"]
            for item in items:
                if item in watchlist["items"]:
                    new_itemlist.remove(item)
            watchlist["items"] = new_itemlist

            with open(
                path.join(watchlist_filepath, message.author.name + ".json"), "w"
            ) as f:
                json.dump(watchlist, f)

            await message.channel.send(
                "Item(s) removed from {}'s watchlist.".format(message.author.mention)
            )

        except OSError:  # no such file
            await message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )

    ## !wqclear
    cmd = "!wqclear"
    if message.content.strip() == cmd:
        try:
            remove(path.join(watchlist_filepath, message.author.name + ".json"))
            await message.channel.send(
                "{}'s watchlist has been cleared.".format(message.author.mention)
            )
        except OSError:
            await message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )

    #############
    ### Other ###

    cmd = "!pronouns add"
    if message.content.strip() == cmd:
        pronoun_list = ""
        for i, pn in enumerate(pronouns):
            pronoun_list += "**{}. {}**\n".format(i + 1, pn)

        await message.channel.send(
            "{} - Type a number corresponding to the pronouns you want to add from the list below.\n{}".format(
                message.author.mention, pronoun_list
            )
        )
        _waitForNonCommand(
            message.author.name, f_pronouns_add
        )  # add name to flag list for pending command
        client.loop.create_task(
            _expireFlag(f_pronouns_add, message.author.name, seconds=60)
        )  # start a task to expire flag

    cmd = "!pronouns remove"
    if message.content.strip() == cmd:
        user_pronouns = [
            role for role in message.author.roles if (role.name in pronouns)
        ]  # get list of user's current pronouns
        pronoun_list = ""
        for i, pn in enumerate(user_pronouns):
            pronoun_list += "**{}. {}**\n".format(i + 1, pn)

        await message.channel.send(
            "{} - Type a number corresponding to the pronouns you want to remove from the list below.\n{}".format(
                message.author.mention, pronoun_list
            )
        )
        _waitForNonCommand(
            message.author.name, f_pronouns_remove
        )  # add name to flag list for pending command
        client.loop.create_task(
            _expireFlag(f_pronouns_remove, message.author.name, seconds=60)
        )  # start a task to expire flag


async def nonCommandHandler(message):

    ############################
    ### Non-command Commands ###
    # These are handled based on flag lists
    if message.author.name in f_pronouns_add:
        try:
            input_num = int(message.content.strip()) - 1
            if input_num in range(len(pronouns)):

                pronoun_role = discord.utils.get(
                    message.guild.roles, name=pronouns[input_num]
                )  # find role ID

                await message.author.add_roles(pronoun_role)  # add role
                await message.channel.send(
                    "{} - Role added!".format(message.author.mention)
                )

            else:
                raise ValueError("Input out of range.")
        except ValueError:
            await message.channel.send(
                "{} - Please input a number between {} and {}.".format(
                    message.author.mention, 1, len(pronouns)
                )
            )
        except AttributeError:
            admin = discord.utils.get(message.guild.members, nick="Tenxian")
            await message.channel.send(
                "{} - Something went wrong. {} needs to fix it.".format(
                    message.author.mention, admin.mention
                )
            )

    if message.author.name in f_pronouns_remove:
        user_pronouns = [
            role.name for role in message.author.roles if (role.name in pronouns)
        ]  # get list of user's current pronouns
        try:
            input_num = int(message.content.strip()) - 1
            if input_num in range(len(user_pronouns)):

                pronoun_role = discord.utils.get(
                    message.guild.roles, name=user_pronouns[input_num]
                )  # find role ID

                await message.author.remove_roles(pronoun_role)  # remove role
                await message.channel.send(
                    "{} - Role removed!".format(message.author.mention)
                )
            else:
                raise ValueError("Input out of range.")
        except ValueError:
            await message.channel.send(
                "{} - Please input a number between {} and {}.".format(
                    message.author.mention, 1, len(user_pronouns)
                )
            )
        except AttributeError:
            admin = discord.utils.get(message.guild.members, nick="Tenxian")
            await message.channel.send(
                "{} - Something went wrong. {} needs to fix it.".format(
                    message.author.mention, admin.mention
                )
            )


# When a message is sent in the channel
@client.event
async def on_message(message):
    # We do not want the bot to reply to itself
    if message.author == client.user:
        return

    # If we see a message in one of our channels that looks like a command, send it to the handler.
    if message.content.startswith("!") and (message.channel.name in botChannels):
        await commandHandler(message)
    else:
        await nonCommandHandler(message)


# Periodically checks for new world quests
async def checkActiveWQs(interval=30):
    interval_secs = interval * 60
    await client.wait_until_ready()

    while True:
        await asyncio.sleep(interval_secs)  # task runs every 60 seconds
        bot_channel = discord.utils.get(
            client.get_all_channels(), name=bot_watchlist_channel
        )

        watchlist_files = [
            f
            for f in listdir(watchlist_filepath)
            if path.isfile(path.join(watchlist_filepath, f))
        ]

        for watchlist_filename in watchlist_files:
            with open(path.join(watchlist_filepath, watchlist_filename), "r") as f:
                watchlist = json.load(f)

            items, slots = WQSearch.parse_slots(watchlist["items"])
            results = WQSearch.searchWQs(items=items, slots=slots)

            results_msg = ""
            if results:  # non-empty
                results_msg += (
                    "Active WQ item reward in {}'s watchlist!".format(
                        watchlist["usermention"]
                    )
                    + "\n"
                )

                if len(results) > 20:
                    results = results[:20]
                    results_msg += "*Too many results. Only showing first 20:*\n"

                results_msg += "\n".join(results)

                await bot_channel.send(results_msg)


async def _expireFlag(flaglist, user, seconds=60):
    # After 'seconds' seconds, removename from flaglist.
    await asyncio.sleep(seconds)
    try:
        while True:
            flaglist.remove(user)  # make sure to get all of them
    except:
        pass


def _waitForNonCommand(user, flag_to_set):
    # Called when a user inputs a command that should be followed by a non-'!' command.
    # Clears all flag lists except for the one from the newly called command. This is so the bot will not be listening for multiple commands.
    for flag in flags_all:
        try:
            while True:
                flag.remove(user)  # make sure to get all of them
        except:
            pass

    # Add name to new flag.
    flag_to_set.append(user)


def _parseWQResultsList(results, message):
    results_msg = ""
    if results:  # non-empty

        results_msg += message.author.mention + "\n"

        if len(results) > 10:
            results = results[:10]
            results_msg += "*Too many results. Only showing first 10:*\n"

        results_msg += "\n".join(results)
        return results_msg

    else:  # empty
        return "No results found for {}'s query.".format(message.author.mention)


def _getCommandList():

    reply = ""
    reply += "__**Commands**__\n"  # header
    for category in commands_all:
        reply += "\n**{}:**\n".format(category)  # category name

        for command in commands_all[category]:
            reply += (
                "{}".format(command) + "  -  " + commands_all[category][command] + "\n"
            )  # command - description

    return reply


# When bot logs in
@client.event
async def on_ready():
    # print('Logged in as {}.'.format(client.user.name))
    print("Logged in.")
    print("--------------")


client.loop.create_task(checkActiveWQs(interval=30))  # minutes to wait between scans
client.run(TOKEN)  # run async thread
