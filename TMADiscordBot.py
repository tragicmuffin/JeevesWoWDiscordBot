__author__ = "tragicmuffin & MCDong"
__license__ = "MIT"
__version__ = "1.21"

"""
Jeeves
A(nother) WoW discord bot.
"""


import asyncio
from datetime import datetime
from os import getenv, path
import random

import discord
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import select

import WQSearch

script_dir = path.dirname(__file__)
DATABASE_URL = getenv("DATABASE_URL")  # Populated by Heroku
if not DATABASE_URL:
    import testing.postgresql

    # Ephemeral Postgres DB for local testing
    # Wiped every run
    _pg = testing.postgresql.Postgresql()
    params = _pg.dsn()
    url = "postgresql://%s@%s:%d/%s" % (
        params["user"],
        params["host"],
        params["port"],
        params["database"],
    )

    DATABASE_URL = _pg.url()
engine = create_engine(DATABASE_URL)
metadata = MetaData(engine)
conn = engine.connect()
# watchlist_filepath = path.join(script_dir, "userdata", "wq_watchlists")
if not engine.dialect.has_table(engine, "watchlists"):
    Watchlists = Table(
        "watchlists",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("username", String),
        Column("usermention", String),
        Column("items", ARRAY(String)),
    )
    metadata.create_all(engine)
metadata.reflect(bind=engine)
Watchlists = metadata.tables["watchlists"]

# Get Discord private token
if getenv("DISCORD_TOKEN"):
    TOKEN = getenv("DISCORD_TOKEN")
else:
    with open(path.join(script_dir, "secret", "key.txt"), "r") as f:
        TOKEN = f.read()
client = discord.Client()


botChannels = ["ask-jeeves", "dice-lobby", "bot-sandbox"]
bot_watchlist_channel = "ask-jeeves"
bot_diceroll_channel = "dice-lobby"

pronouns = ["She/Her", "He/Him", "They/Them", "Ze/Zir", "Xe/Xir"]


# Lists of valid commands with descriptions. Used in !help command.
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

commands_other_roles = {
    "!addrole Raiders": "Assigns you the @Raiders role.",
    "!addrole Mythics": "Assigns you the @Mythics role.",

    "!removerole Raiders": "Removes your @Raiders role.",
    "!removerole Mythics": "Removes your @Mythics role.",
}

commands_all = {
    "General": commands_general,
    "World Quests": commands_wq,
    "Pronouns": commands_pronouns,
    "Other Roles": command_other_roles,
}


f_pronouns_add = []
f_pronouns_remove = []
flags_all = [f_pronouns_add, f_pronouns_remove]


@asyncio.coroutine
def commandHandler(message):

    ########################
    ### General Commands ###

    ## !help / !commands
    cmds = ["!commands", "!help"]
    if message.content.strip() in cmds:
        msg = _getCommandList()
        yield from message.channel.send(msg)

    ###################
    ### WQ Commands ###

    ## !wqscan
    cmd = "!wqscan "
    if message.content.startswith(cmd):
        args = message.content[len(cmd) :].strip().split(", ")
        items, slots = WQSearch.parse_slots(args)

        results = WQSearch.searchWQs(items=items, slots=slots)
        results_string = _parseWQResultsList(results, message)
        yield from message.channel.send(results_string)

    _select_query = select([Watchlists]).where(
        Watchlists.c.username == message.author.name
    )

    ## !wqwatch
    cmd = "!wqwatch "
    if message.content.startswith(cmd):
        items = message.content[len(cmd) :].strip().split(", ")
        userdata = conn.execute(_select_query).fetchone()
        if not userdata:
            conn.execute(
                Watchlists.insert().values(
                    username=message.author.name,
                    usermention=message.author.mention,
                    items=items,
                )
            )
        else:
            items = list(set(items + userdata["items"]))
            conn.execute(
                Watchlists.update()
                .where(Watchlists.c.username == message.author.name)
                .values(
                    username=message.author.name,
                    usermention=message.author.mention,
                    items=items,
                )
            )
        userdata = conn.execute(_select_query).fetchone()
        watchlist_items = "__" + "__, __".join(userdata["items"]) + "__"
        yield from message.channel.send(
            "{}'s watchlist saved. Items: {}".format(
                message.author.mention, watchlist_items
            )
        )

    ## !wqwatchlist
    cmd = "!wqwatchlist"
    if message.content.strip() == cmd:
        userdata = conn.execute(_select_query).fetchone()
        if userdata:
            watchlist_items = "__" + "__, __".join(userdata["items"]) + "__"
            yield from message.channel.send(
                "{}'s watchlist saved. Current watchlist: {}".format(
                    message.author.mention, watchlist_items
                )
            )
        else:
            yield from message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )

    ## !wqremove
    cmd = "!wqremove "
    if message.content.startswith(cmd):
        items = message.content[len(cmd) :].strip().split(", ")
        userdata = conn.execute(_select_query).fetchone()
        if not userdata:
            yield from message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )
        else:
            items = list(set(userdata["items"]) - set(items))
            conn.execute(
                Watchlists.update()
                .where(Watchlists.c.username == message.author.name)
                .values(items=items)
            )
            userdata = conn.execute(_select_query).fetchone()
            watchlist_items = "__" + "__, __".join(userdata["items"]) + "__"
            yield from message.channel.send(
                "Item(s) removed from {}'s watchlist. Current watchlist: {}".format(
                    message.author.mention, watchlist_items
                )
            )

    ## !wqclear
    cmd = "!wqclear"
    if message.content.strip() == cmd:
        userdata = conn.execute(_select_query).fetchone()
        if not userdata:
            yield from message.channel.send(
                "{} has no saved watchlist items.".format(message.author.mention)
            )
        else:
            conn.execute(
                Watchlists.delete().where(Watchlists.c.username == message.author.name)
            )
            yield from message.channel.send(
                "Item(s) removed from {}'s watchlist. Current watchlist: {}".format(
                    message.author.mention, []
                )
            )

    ################
    ### Pronouns ###

    cmd = "!pronouns add"
    if message.content.strip() == cmd:
        pronoun_list = ""
        for i, pn in enumerate(pronouns):
            pronoun_list += "**{}. {}**\n".format(i + 1, pn)

        yield from message.channel.send(
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

        yield from message.channel.send(
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

    ###################
    ### Other Roles ###
    try:
        cmd = "!addrole raiders"
        if message.content.strip().lower() == cmd:
            raiders_role = discord.utils.get(message.guild.roles, name="Raiders")  # find role ID

            yield from message.author.add_roles(raiders_role)  # add role to message sender
            yield from message.channel.send("{} - Role added!".format(message.author.mention))
            # TODO: add 'you already have this role' handler. `message.author.roles`?

        cmd = "!addrole mythics"
        if message.content.strip().lower() == cmd:
            mythics_role = discord.utils.get(message.guild.roles, name="Mythics")  # find role ID

            yield from message.author.add_roles(mythics_role)  # add role to message sender
            yield from message.channel.send("{} - Role added!".format(message.author.mention))


        cmd = "!removerole raiders"
        if message.content.strip().lower() == cmd:
            raiders_role = discord.utils.get(message.guild.roles, name="Raiders")  # find role ID

            yield from message.author.remove_roles(raiders_role)  # remove role from message sender
            yield from message.channel.send("{} - Role removed!".format(message.author.mention))

        cmd = "!removerole mythics"
        if message.content.strip().lower() == cmd:
            mythics_role = discord.utils.get(message.guild.roles, name="Mythics")  # find role ID

            yield from message.author.remove_roles(mythics_role)  # remove role from message sender
            yield from message.channel.send("{} - Role removed!".format(message.author.mention))


        # TODO: Add catch-all for unrecognized roles


        cmd = "!roll"
        roll_success = True
        roll_default = (1, 100)
        if message.content.startswith(cmd) and (message.channel.name == bot_diceroll_channel):
            if message.content.strip() == cmd:  # no number input
                roll = random.randint(roll_default[0], roll_default[1])
            elif message.content[5:].strip().isdigit():  # single number input
                roll = random.randint(roll_default[0], message.content[5:].strip())
            elif message.content[5:].split('-')[0].strip().isdigit() and message.content[5:].split('-')[1].strip().isdigit():  # range number input
                roll = random.randint(message.content[5:].split('-')[0].strip(), message.content[5:].split('-')[1].strip())
            else:
                roll_success = False

            if (roll_success):
                yield from message.channel.send("{} rolled a **{}**".format(message.author.mention, roll))
                if roll == 69:
                    yield from message.channel.send("nice.")



    except AttributeError:
        admin = discord.utils.get(message.guild.members, nick="Tenxian")
        yield from message.channel.send(
            "{} - Something went wrong. {} needs to fix it.".format(
                message.author.mention, admin.mention
            )
        )



@asyncio.coroutine
def nonCommandHandler(message):

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

                yield from message.author.add_roles(pronoun_role)  # add role
                yield from message.channel.send(
                    "{} - Role added!".format(message.author.mention)
                )

            else:
                raise ValueError("Input out of range.")
        except ValueError:
            yield from message.channel.send(
                "{} - Please input a number between {} and {}.".format(
                    message.author.mention, 1, len(pronouns)
                )
            )
        except AttributeError:
            admin = discord.utils.get(message.guild.members, nick="Tenxian")
            yield from message.channel.send(
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

                yield from message.author.remove_roles(pronoun_role)  # remove role
                yield from message.channel.send(
                    "{} - Role removed!".format(message.author.mention)
                )
            else:
                raise ValueError("Input out of range.")
        except ValueError:
            yield from message.channel.send(
                "{} - Please input a number between {} and {}.".format(
                    message.author.mention, 1, len(user_pronouns)
                )
            )
        except AttributeError:
            admin = discord.utils.get(message.guild.members, nick="Tenxian")
            yield from message.channel.send(
                "{} - Something went wrong. {} needs to fix it.".format(
                    message.author.mention, admin.mention
                )
            )


# When a message is sent in the channel
@client.event
@asyncio.coroutine
def on_message(message):
    # We do not want the bot to reply to itself
    if message.author == client.user:
        return

    # If we see a message in one of our channels that looks like a command, send it to the handler.
    if message.content.startswith("!") and (message.channel.name in botChannels):
        yield from commandHandler(message)
    else:
        yield from nonCommandHandler(message)


# Periodically checks for new world quests
@asyncio.coroutine
def checkActiveWQs(interval=5, stale_wqs={}):
    interval_secs = interval * 60
    yield from client.wait_until_ready()

    while True:
        yield from asyncio.sleep(interval_secs)
        bot_channel = discord.utils.get(
            client.get_all_channels(), name=bot_watchlist_channel
        )
        _now = int(datetime.timestamp(datetime.utcnow()))
        if stale_wqs:
            stale_wqs = {
                q_id: q_endtime
                for q_id, q_endtime in stale_wqs.items()
                if _now < q_endtime
            }
        for watchlist in conn.execute(select([Watchlists])):
            items, slots = WQSearch.parse_slots(watchlist["items"])
            results = WQSearch.searchWQs(items=items, slots=slots)

            results_msg = ""
            for q_id, q_info in results.items():
                if q_id in stale_wqs:
                    continue
                stale_wqs[q_id] = q_info["endtime"]
                results_msg += f"\n\t• {q_info['output']}"

            if results_msg:  # non-empty
                results_msg = (
                    "Active WQ item reward in {}'s watchlist!".format(
                        watchlist["usermention"]
                    )
                    + "\n\n"
                ) + results_msg

                yield from bot_channel.send(results_msg)


@asyncio.coroutine
def _expireFlag(flaglist, user, seconds=60):
    # After 'seconds' seconds, removename from flaglist.
    yield from asyncio.sleep(seconds)
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
    output = [v["output"] for k, v in results.items()]
    results_msg = ""
    if output:  # non-empty

        results_msg += message.author.mention
        if len(output) > 10:
            output = output[:10]
            results_msg += "\n*Too many results. Only showing first 10:*"

        results_msg += "\n\t• "

        results_msg += "\n\t• ".join(output)
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
@asyncio.coroutine
def on_ready():
    # print('Logged in as {}.'.format(client.user.name))
    print("Logged in.")
    print("--------------")


client.loop.create_task(
    checkActiveWQs(interval=5, stale_wqs={})
)  # minutes to wait between scans
client.run(TOKEN)  # run async thread
