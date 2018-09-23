## Bot Commands
### !help / !command
- Shows this list of commands.
### !wqscan
- Runs a one-time scan for a list of items and returns results in channel.
### !wqwatch
- Saves a list of items for the bot to watch for and return hits to user.
- If run by a user that already has a registered list of search terms, the new terms are added to the list.
### !wqremove
- Removes the provided comma-separated search term(s) from a user's watch list.
### !wqwatchlist
- Shows user their currently saved list of item search terms.
### !wqclear
- Clears all currently saved items from user's watch list.

## WQ Watchlist Interface
- User will send '!wqwatch item1, item2, item3'.
- These item strings will be saved in a JSON object along with the user's name (discord username, not display name)
- On a certain interval, the WQ search daemon will scan active WQs for all registered keywords for each user.
- When matches are found, the results are sent to the user in a PM and/or posted in the bot channel @ the user.
- User will send '!wqclear' to clear the user's record

## WQ Watchlist JSON Format
```js
{
    {
        username: 'tragicmuffin',
        usermention: 'Tenxian',
        items: ['item1', 'item2', 'item3']
    }
}
```
