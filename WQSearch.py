#! python3
import json
import re
import urllib.request
from datetime import datetime

import dateutil.tz

#########################################################################

# Get list view script (second script). Parse json. Read "rewards">"items">"id" from each element.
# Get data script (first script). Search for pattern _[item_id] and parse following json. Read "name_enus" attribute.
# If we have a match, read "ending" and "id" (quest id) from original json, then also lookup _[quest_id].


def _getWQhtml():
    r = urllib.request.urlopen("https://www.wowhead.com/world-quests/bfa/na")
    r_bytes = r.read()

    wq_html = r_bytes.decode("utf8")
    r.close()

    return wq_html


def _getWQjson(wq_html):

    matcher = '<div class="listview" id="list"></div>'
    wqlist_start = wq_html.index(matcher) + len(matcher)

    wqlist = wq_html[wqlist_start:]

    # Find the next two script tag's contents.
    matcher_in = "<script>"
    matcher_out = "</script>"

    script1_start = wqlist.index(matcher_in) + len(matcher_in)
    script1_end = wqlist.index(matcher_out)

    wqlist_nexttag = wqlist[script1_end + len(matcher_in) :]
    script2_start = wqlist_nexttag.index(matcher_in) + len(matcher_in)
    script2_end = wqlist_nexttag.index(matcher_out)

    wqs_data = wqlist[script1_start:script1_end]  # All quest and item data
    wqs_list = wqlist_nexttag[script2_start:script2_end]  # List holding all active WQs

    return (wqs_data, wqs_list)


zone_cache = {
    "9042": "Stormsong Valley",
    "8567": "Tiragarde Sound",
    "8721": "Drustvar",
    "8499": "Zuldazar",
    "8500": "Nazmir",
    "8501": "Vol'dun",
}


def _getZoneName(zone_id):
    global zone_cache
    zone_id = str(zone_id)
    if zone_id in zone_cache:
        return zone_cache[zone_id]

    with urllib.request.urlopen(f"https://www.wowhead.com/zone={zone_id}") as r:
        zone_html = r.read().decode("utf8")
    pat = r"<title>(.+) - Zone - World of Warcraft<\/title>"
    name = re.search(pat, zone_html).group(1)
    zone_cache[zone_id] = name

    return name


def searchWQs(items=[], quests=[], slots=[]):
    wq_html = _getWQhtml()
    (wqs_data, wqs_list) = _getWQjson(wq_html)

    ## Parse and search WQ list
    list_start = wqs_list.index("{")  # start of json
    list_end = wqs_list.rindex("}")  # end of json
    list_json = wqs_list[list_start : list_end + 1]

    list_top = json.loads(list_json)
    list_data = list_top["data"]

    # list_data is a list of dictionaries, each dict holding an active WQ
    # list_data.id: The id number for the quest
    # list_data.ending: The ending time for the quest (since epoch?)
    # list_data.rewards: If this is an empty list [], quest gives no rewards
    # list_data.rewards.items: If rewards is non-empty {}, this will hold a list of item dicts
    # list_data.rewards.items.id: If there are item rewards, this will hold their ids.
    # list_data.rewards.zones: list of zone ids for the WQ

    output = []
    for quest in list_data:
        quest_id = quest["id"]
        quest_endtime = quest["ending"]
        rewards = quest["rewards"]

        if type(rewards) is dict:  # if we have any rewards in this quest...
            reward_items_ids = [i["id"] for i in rewards["items"]]
            matched_rewards = []

            for item_name, watchlist_item, watchlist_slot in _checkForItems(
                reward_items_ids, wqs_data, items, slots
            ):
                highlight_name = item_name
                if watchlist_item:
                    pat = re.compile(f"({re.escape(watchlist_item)})", re.IGNORECASE)
                    highlight_name = re.sub(pat, "**\\1**", item_name)
                if watchlist_slot:
                    if watchlist_slot in slots:
                        slot = f" (**{watchlist_slot}**)"
                    else:
                        slot = f" ({watchlist_slot})"
                else:
                    slot = ""
                item_string = f"{highlight_name}{slot}"
                matched_rewards.append(item_string)

            if matched_rewards:
                item_output_string = ", ".join(matched_rewards)

                # We have a match. Go get the quest name and remaining time on this quest.
                quest_name, quest_side = _lookupQuest(quest_id, wqs_data)

                # Some WQs are only available to one faction
                if quest_side == 1:
                    faction_limit = " (Alliance Only)"
                elif quest_side == 2:
                    faction_limit = " (Horde Only)"
                else:
                    faction_limit = ""
                quest_endtime_formatted = _formatTime(quest_endtime)

                # Sometimes a quest contains multiple zone IDs
                _zn = [_getZoneName(x) for x in quest["zones"]]
                zone_names = (
                    " in " + " and ".join(_zn) if _zn else ""
                )  # Sometimes wowhead doesn't return a zone name

                # TODO: Format this as something other than a single line
                output.append(
                    f"{item_output_string} found in quest *{quest_name}*{zone_names}{faction_limit}. Expires: {quest_endtime_formatted} server. wowhead.com/quest={quest_id}"
                )
    return output


# Wowhead returns the slot for the reward item as an integer ID.
# This dict maps those IDs to human readable names, and allows for some fuzzy searching
slot_ids = {
    1: ["Head", "helm"],
    3: ["Shoulder"],
    5: ["Chest"],
    6: ["Waist", "belt"],
    7: ["Leg", "pants"],
    8: ["Feet", "shoe", "boot"],
    9: ["Wrist", "bracer"],
    10: ["Hand", "glove"],
    11: ["Finger", "ring"],
    12: ["Trinket"],
    13: ["One-hand", r"one.?hand", r"main.?hand", "weapon"],
    14: ["Shield", r"off.?hand"],
    15: ["Ranged", "gun", "bow", "weapon"],
    16: ["Back", "cloak"],
    17: ["Two-hand", r"two.?hand", "weapon"],
    20: ["Chest"],  # Cloth chest armor is the only thing that has slotbak:20
    23: ["Off-hand", r"off.?hand"],
}


def _checkForItems(item_id_list, wqs_data, items_to_check, slots_to_check):
    for item_id in item_id_list:
        # Takes an item id and looks up item in wqs_data.
        patt = "_[" + str(item_id) + "]="
        item_start = wqs_data.index(patt) + len(patt)
        item_end = wqs_data.index(";", item_start)
        item_json = wqs_data[item_start:item_end]

        wqlist_item = json.loads(item_json)

        # Get the slot ID of the item returned by wowhead
        s_id = wqlist_item["jsonequip"].get("slotbak")
        slot = ""
        if s_id:
            slot_names = slot_ids[s_id]
            for s in slots_to_check:
                if any(re.search(name, s, flags=re.IGNORECASE) for name in slot_names):
                    # Watchlist slot 's' matches one of the slot names for this item
                    slot = s
        item = ""
        for i in items_to_check:
            if i.lower() in wqlist_item["name_enus"].lower():
                # Watchlist item 'i' matches the name of this item
                item = i
        if item or slot:
            slot = slot_names[0]  # slot_names[0] is the "official" name
            yield (wqlist_item["name_enus"], item, slot)


def _lookupQuest(quest_id, wqs_data):
    # Takes a quest id and looks up quest in wqs_data. Returns quest name and quest side since some wqs are for only one faction.
    # TODO: Add a way to let the user ignore WQs that are specific to one faction
    patt = "_[" + str(quest_id) + "]="
    quest_start = wqs_data.index(patt) + len(patt)
    quest_end = wqs_data.index(";", quest_start)
    quest_json = wqs_data[quest_start:quest_end]

    quest = json.loads(quest_json)
    return quest["name_enus"], quest["_side"]


def _formatTime(time):
    tzinfo = dateutil.tz.gettz("US/Pacific")
    return datetime.fromtimestamp(time / 1000, tzinfo).strftime("%a, %m/%d at %I:%M %p")


def parse_slots(args):
    # A user's watchlist is a mixed list of item names and slot names.
    # This function will split it into two separate lists
    items = [x for x in args if not x.startswith("slot:")]
    slots = [x.split(":")[1] for x in args if x.startswith("slot:")]
    return items, slots


#########################################################################


if __name__ == "__main__":
    import sys

    if not sys.argv[1:]:
        items = ["Bilewing", "storm", "glove"]
        searchWQs(items=items)
    else:
        items, slots = parse_slots(sys.argv[1:])
        print(searchWQs(items=items, slots=slots))
    a = _getWQhtml()
    b = _getWQjson(a)
