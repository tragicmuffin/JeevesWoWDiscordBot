# Bot Commands

## General
| Command                | Description |
|---                     |---|
| !help, !commands       | Shows this list of commands. |

## World Quests
| Command                | Description |
|---                     |---|
| !wqscan                | Runs a one-time scan for a list of items and returns results in channel. |
| !wqwatch               | Saves a list of items for the bot to watch for and return hits to user. If run by a user that already has a registered list of search terms, the new terms are added to the list. |
| !wqwatchlist           | Shows user their currently saved list of item search terms. |
| !wqremove              | Removes the provided comma-separated search term(s) from a user's watch list. |
| !wqclear               | Clears all currently saved items from user's watch list. |

#### Use ``slot:[SLOTNAME]`` to search for items in a certain slot instead of by name.
#### Examples: ``!wqscan slot:trinket``, ``!wqwatch slot:cloak``.

## Pronouns
| Command                | Description |
|---                     |---|
| !pronouns add          | Adds a set of pronouns to the user as a Discord role. |
| !pronouns remove       | Removes a set of pronouns from the user. |   

## Other Roles
| Command                | Description |
|---                     |---|
| !addrole `[role]`    | Adds a Discord role to the user. |
| !removerole `[role]` | Removes a Discord role from the user. |   

#### Available roles: _Raider_, _Mythics_


# WQ Watchlist Interface
- User will send '!wqwatch item1, item2, item3'.
- These item strings will be saved in a JSON object along with the user's name (discord username, not display name)
- On a certain interval, the WQ search daemon will scan active WQs for all registered keywords for each user.
- When matches are found, the results are sent to the user in a PM and/or posted in the bot channel @ the user.
- User will send '!wqclear' to clear the user's record

# WQ Watchlist JSON Format
```js
{
    {
        username: 'tragicmuffin',
        usermention: 'Tenxian',
        items: ['item1', 'item2', 'item3']
    }
}
```
# Developer Guide
To run this project locally, you must first install the PostgreSQL binary for your environment and be able to run [`psql` from the command line](https://www.postgresql.org/download/).

This project uses [`Pipenv` (found here)](https://pipenv.readthedocs.io/en/latest/basics/) to manage all python dependencies. 

Getting started locally:
```
python3 -m pip install pipenv
pipenv install --dev .
pipenv run python TMADiscordBot.py
```

To test locally using the remote Heroku database, you must install the [`Heroku` CLI tool](https://devcenter.heroku.com/articles/heroku-cli):
```
pipenv run heroku local
```
To open Postgres command line on remote PSQL DB:
```
heroku pg psql
```
